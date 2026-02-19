from __future__ import annotations

from decimal import Decimal
from uuid import uuid4

from django.conf import settings
from django.db import transaction

from apps.ledger.models import LedgerEntry
from apps.ledger.services import debit_wallet, reverse_transaction
from apps.referrals.services import evaluate_referral_bonus
from apps.vtu.models import PurchaseOrder, ServiceProvider
from apps.vtu.providers import BaseProvider, MockProvider


def get_provider_client() -> BaseProvider:
    provider_name = getattr(settings, 'VTU_PROVIDER', 'mock').lower()
    if provider_name == 'vtpass':
        from apps.vtu.providers.vtpass import VTpassProvider

        return VTpassProvider(config=settings.VTPASS_CONFIG)
    return MockProvider()


def generate_purchase_reference() -> str:
    return f'VTU-{uuid4().hex[:12].upper()}'


def _ledger_type_for_product(product_type: str) -> str:
    mapping = {
        PurchaseOrder.ProductType.AIRTIME: LedgerEntry.TransactionType.AIRTIME,
        PurchaseOrder.ProductType.DATA: LedgerEntry.TransactionType.DATA,
        PurchaseOrder.ProductType.BILL: LedgerEntry.TransactionType.BILL,
    }
    return mapping[product_type]


@transaction.atomic
def create_purchase_order(*, user, provider: ServiceProvider, product_type: str, amount: Decimal, destination: str, service_code: str = '') -> PurchaseOrder:
    reference = generate_purchase_reference()
    ledger_reference = f'{reference}-DEBIT'
    debit_entry = debit_wallet(
        user=user,
        amount=amount,
        reference=ledger_reference,
        tx_type=_ledger_type_for_product(product_type),
        meta={'purchase_reference': reference, 'product_type': product_type, 'destination': destination},
    )

    status = PurchaseOrder.Status.PENDING
    if debit_entry.status == LedgerEntry.Status.FAILED:
        status = PurchaseOrder.Status.FAILED

    order = PurchaseOrder.objects.create(
        user=user,
        provider=provider,
        reference=reference,
        product_type=product_type,
        amount=amount,
        destination=destination,
        service_code=service_code,
        status=status,
        message='Awaiting provider processing.' if status == PurchaseOrder.Status.PENDING else 'Insufficient wallet balance.',
        ledger_reference=ledger_reference,
    )
    return order


def process_purchase(order_id: int) -> PurchaseOrder:
    order = PurchaseOrder.objects.select_related('provider').get(pk=order_id)
    if order.status != PurchaseOrder.Status.PENDING:
        return order

    client = get_provider_client()

    if order.product_type == PurchaseOrder.ProductType.AIRTIME:
        result = client.purchase_airtime(
            network=order.service_code,
            phone=order.destination,
            amount=order.amount,
            reference=order.reference,
        )
    elif order.product_type == PurchaseOrder.ProductType.DATA:
        result = client.purchase_data(
            network=order.service_code.split(':')[0] if ':' in order.service_code else order.service_code,
            plan_code=order.service_code,
            phone=order.destination,
            reference=order.reference,
        )
    else:
        result = client.purchase_bill(
            biller_code=order.service_code,
            customer_id=order.destination,
            amount=order.amount,
            reference=order.reference,
        )

    order.provider_reference = result.provider_ref
    order.message = result.message
    order.provider_response = result.raw or {}

    if result.status == 'SUCCESS':
        order.status = PurchaseOrder.Status.SUCCESS
        order.save(update_fields=['status', 'provider_reference', 'message', 'provider_response'])
        evaluate_referral_bonus(order.user)
        return order

    if result.status == 'PENDING':
        order.status = PurchaseOrder.Status.PENDING
        order.save(update_fields=['status', 'provider_reference', 'message', 'provider_response'])
        from apps.vtu.tasks import verify_pending_purchase

        verify_pending_purchase.delay(order.id)
        return order

    reverse_transaction(order.ledger_reference, reason=result.message or 'provider_failure')
    order.status = PurchaseOrder.Status.FAILED
    order.save(update_fields=['status', 'provider_reference', 'message', 'provider_response'])
    return order


def verify_purchase(order_id: int) -> PurchaseOrder:
    order = PurchaseOrder.objects.get(pk=order_id)
    if order.status != PurchaseOrder.Status.PENDING:
        return order

    result = get_provider_client().verify(reference=order.reference, provider_ref=order.provider_reference)
    order.provider_reference = result.provider_ref or order.provider_reference
    order.message = result.message
    order.provider_response = result.raw or {}

    if result.status == 'SUCCESS':
        order.status = PurchaseOrder.Status.SUCCESS
        order.save(update_fields=['status', 'provider_reference', 'message', 'provider_response'])
        evaluate_referral_bonus(order.user)
        return order

    if result.status == 'PENDING':
        order.save(update_fields=['provider_reference', 'message', 'provider_response'])
        return order

    reverse_transaction(order.ledger_reference, reason=result.message or 'verification_failure')
    order.status = PurchaseOrder.Status.FAILED
    order.save(update_fields=['status', 'provider_reference', 'message', 'provider_response'])
    return order
