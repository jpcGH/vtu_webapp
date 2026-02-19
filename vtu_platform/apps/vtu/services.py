from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from decimal import Decimal
from uuid import uuid4

from django.conf import settings
from django.db import transaction

from apps.ledger.models import LedgerEntry
from apps.ledger.services import debit_wallet, reverse_transaction
from apps.referrals.services import evaluate_referral_bonus
from apps.vtu.models import PurchaseOrder, ServiceProvider


@dataclass
class VTUResult:
    success: bool
    message: str
    provider_reference: str = ''
    error_code: str = ''
    raw_response: dict | None = None


class BaseProvider(ABC):
    @abstractmethod
    def purchase_airtime(self, network: str, phone: str, amount: Decimal, reference: str) -> VTUResult:
        raise NotImplementedError

    @abstractmethod
    def purchase_data(self, network: str, plan_code: str, phone: str, reference: str) -> VTUResult:
        raise NotImplementedError

    @abstractmethod
    def purchase_bill(self, biller_code: str, customer_id: str, amount: Decimal, reference: str) -> VTUResult:
        raise NotImplementedError


class MockProvider(BaseProvider):
    def _is_failure(self, value: str) -> bool:
        return value.strip().upper().startswith('FAIL')

    def purchase_airtime(self, network: str, phone: str, amount: Decimal, reference: str) -> VTUResult:
        if self._is_failure(phone):
            return VTUResult(success=False, message='Mock airtime purchase failed', error_code='MOCK_FAILED')
        return VTUResult(
            success=True,
            message='Mock airtime purchase successful',
            provider_reference=f'MOCK-AIR-{reference[-8:]}',
            raw_response={'network': network, 'phone': phone, 'amount': str(amount)},
        )

    def purchase_data(self, network: str, plan_code: str, phone: str, reference: str) -> VTUResult:
        if self._is_failure(phone) or self._is_failure(plan_code):
            return VTUResult(success=False, message='Mock data purchase failed', error_code='MOCK_FAILED')
        return VTUResult(
            success=True,
            message='Mock data purchase successful',
            provider_reference=f'MOCK-DATA-{reference[-8:]}',
            raw_response={'network': network, 'phone': phone, 'plan_code': plan_code},
        )

    def purchase_bill(self, biller_code: str, customer_id: str, amount: Decimal, reference: str) -> VTUResult:
        if self._is_failure(customer_id) or self._is_failure(biller_code):
            return VTUResult(success=False, message='Mock bill payment failed', error_code='MOCK_FAILED')
        return VTUResult(
            success=True,
            message='Mock bill payment successful',
            provider_reference=f'MOCK-BILL-{reference[-8:]}',
            raw_response={'biller_code': biller_code, 'customer_id': customer_id, 'amount': str(amount)},
        )


def get_provider_client() -> BaseProvider:
    provider_name = getattr(settings, 'VTU_PROVIDER', 'mock').lower()
    if provider_name in {'mock', 'stub'}:
        return MockProvider()
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

    if result.success:
        order.status = PurchaseOrder.Status.SUCCESS
        order.provider_reference = result.provider_reference
        order.message = result.message
        order.provider_response = result.raw_response or {}
        order.save(update_fields=['status', 'provider_reference', 'message', 'provider_response'])
        evaluate_referral_bonus(order.user)
        return order

    reverse_transaction(order.ledger_reference, reason=result.message or result.error_code or 'provider_failure')
    order.status = PurchaseOrder.Status.FAILED
    order.message = result.message
    order.provider_response = result.raw_response or {}
    order.save(update_fields=['status', 'message', 'provider_response'])
    return order
