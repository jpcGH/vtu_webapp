from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings

from apps.ledger.models import LedgerEntry, Wallet
from apps.ledger.services import credit_wallet
from apps.vtu.models import PurchaseOrder, ServiceProvider
from apps.vtu.services import create_purchase_order, process_purchase, verify_purchase


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

    @patch('apps.vtu.tasks.verify_pending_purchase.delay')
    def test_pending_purchase_remains_pending_and_schedules_verification(self, delay_mock):
        order = create_purchase_order(
            user=self.user,
            provider=self.provider,
            product_type=PurchaseOrder.ProductType.AIRTIME,
            amount=Decimal('120.00'),
            destination='PEND-08030000000',
            service_code='mtn',
        )

        processed_order = process_purchase(order.id)
        self.assertEqual(processed_order.status, PurchaseOrder.Status.PENDING)
        delay_mock.assert_called_once_with(order.id)

    @patch('apps.vtu.tasks.verify_pending_purchase.delay')
    def test_verification_failure_reverses_wallet(self, _delay_mock):
        order = create_purchase_order(
            user=self.user,
            provider=self.provider,
            product_type=PurchaseOrder.ProductType.AIRTIME,
            amount=Decimal('120.00'),
            destination='PEND-08030000000',
            service_code='mtn',
        )
        process_purchase(order.id)

        order.reference = 'FAIL-VERIFY'
        order.save(update_fields=['reference'])
        verify_purchase(order.id)

        order.refresh_from_db()
        wallet = Wallet.objects.get(user=self.user)
        self.assertEqual(order.status, PurchaseOrder.Status.FAILED)
        self.assertEqual(wallet.balance, Decimal('1000.00'))


class VTpassProviderTests(TestCase):
    @override_settings(
        VTU_PROVIDER='vtpass',
        VTPASS_CONFIG={
            'base_url': 'https://vtpass.test',
            'api_key': 'api-key',
            'username': 'user',
            'password': 'secret',
        },
    )
    @patch('apps.vtu.providers.vtpass.requests.Session.request')
    def test_vtpass_response_is_normalized(self, request_mock):
        response_payload = {
            'code': '000',
            'response_description': 'TRANSACTION SUCCESSFUL',
            'requestId': 'REF-001',
            'content': {'transactions': {'status': 'delivered', 'transactionId': 'TX-123'}},
        }

        class _Response:
            status_code = 200

            @staticmethod
            def json():
                return response_payload

        request_mock.return_value = _Response()

        from apps.vtu.services import get_provider_client

        result = get_provider_client().purchase_airtime('mtn', '0803', Decimal('100'), 'REF-001')
        self.assertTrue(result.success)
        self.assertEqual(result.status, 'SUCCESS')
        self.assertEqual(result.provider_ref, 'REF-001')
