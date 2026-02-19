from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase

from apps.ledger.models import LedgerEntry, Wallet
from apps.ledger.services import credit_wallet
from apps.vtu.models import PurchaseOrder, ServiceProvider
from apps.vtu.services import create_purchase_order, process_purchase


class VTUPurchaseFlowTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username='vtu-user', password='secret123')
        self.provider = ServiceProvider.objects.create(name='Mock', slug='mock')
        credit_wallet(self.user, Decimal('1000.00'), 'seed-vtu-fund', {})

    def test_failed_provider_purchase_reverses_debit_once(self):
        order = create_purchase_order(
            user=self.user,
            provider=self.provider,
            product_type=PurchaseOrder.ProductType.AIRTIME,
            amount=Decimal('200.00'),
            destination='FAIL-08000000000',
            service_code='mtn',
        )

        processed_order = process_purchase(order.id)
        process_purchase(order.id)

        wallet = Wallet.objects.get(user=self.user)
        reversal_entries = LedgerEntry.objects.filter(
            tx_type=LedgerEntry.TransactionType.REVERSAL,
            meta__reversed_reference=order.ledger_reference,
        )

        self.assertEqual(processed_order.status, PurchaseOrder.Status.FAILED)
        self.assertEqual(wallet.balance, Decimal('1000.00'))
        self.assertEqual(reversal_entries.count(), 1)

    def test_successful_purchase_keeps_debit_and_marks_success(self):
        order = create_purchase_order(
            user=self.user,
            provider=self.provider,
            product_type=PurchaseOrder.ProductType.DATA,
            amount=Decimal('150.00'),
            destination='08030000000',
            service_code='mtn:500mb',
        )

        processed_order = process_purchase(order.id)
        wallet = Wallet.objects.get(user=self.user)

        self.assertEqual(processed_order.status, PurchaseOrder.Status.SUCCESS)
        self.assertTrue(processed_order.provider_reference.startswith('MOCK-DATA-'))
        self.assertEqual(wallet.balance, Decimal('850.00'))
        self.assertFalse(
            LedgerEntry.objects.filter(
                tx_type=LedgerEntry.TransactionType.REVERSAL,
                meta__reversed_reference=order.ledger_reference,
            ).exists()
        )
