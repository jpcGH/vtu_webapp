import json
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import Client, TestCase, override_settings

from apps.ledger.models import LedgerEntry, Wallet
from apps.payments.models import IncomingPayment, VirtualAccount
from apps.payments.services import monnify_webhook_signature


@override_settings(MONNIFY_SECRET_KEY='test-secret-key')
class MonnifyWebhookTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = get_user_model().objects.create_user(
            username='monnify-user',
            email='monnify@example.com',
            password='secret123',
        )
        VirtualAccount.objects.create(
            user=self.user,
            provider=VirtualAccount.Provider.MONNIFY,
            account_reference=f'USR-{self.user.pk}',
            bank_name='Test Bank',
            account_number='0123456789',
            account_name='Monnify User',
            monnify_account_reference='mon-ref-123',
            reserved_account_reference='res-ref-123',
            status=VirtualAccount.Status.ACTIVE,
        )

    def _payload(self):
        return {
            'eventType': 'SUCCESSFUL_TRANSACTION',
            'eventData': {
                'transactionReference': 'MNF_TX_001',
                'paymentReference': 'MNF_PAY_001',
                'amountPaid': 1500,
                'currency': 'NGN',
                'payerName': 'John Doe',
                'payerEmail': 'john@example.com',
                'destinationAccountInformation': {
                    'accountNumber': '0123456789',
                    'bankName': 'Test Bank',
                },
            },
        }

    def test_webhook_rejects_invalid_signature(self):
        payload = self._payload()
        response = self.client.post(
            '/payments/monnify/webhook/',
            data=json.dumps(payload),
            content_type='application/json',
            HTTP_MONNIFY_SIGNATURE='bad-signature',
        )

        self.assertEqual(response.status_code, 401)
        self.assertEqual(IncomingPayment.objects.count(), 0)

    def test_webhook_idempotency_credits_wallet_once(self):
        payload = self._payload()
        raw = json.dumps(payload).encode()
        signature = monnify_webhook_signature(raw)

        first = self.client.post(
            '/payments/monnify/webhook/',
            data=raw,
            content_type='application/json',
            HTTP_MONNIFY_SIGNATURE=signature,
        )
        second = self.client.post(
            '/payments/monnify/webhook/',
            data=raw,
            content_type='application/json',
            HTTP_MONNIFY_SIGNATURE=signature,
        )

        self.assertEqual(first.status_code, 200)
        self.assertEqual(second.status_code, 200)

        wallet = Wallet.objects.get(user=self.user)
        self.assertEqual(wallet.balance, Decimal('1500.00'))
        self.assertEqual(IncomingPayment.objects.count(), 1)
        self.assertEqual(
            LedgerEntry.objects.filter(reference='MONNIFY_MNF_TX_001', status=LedgerEntry.Status.SUCCESS).count(),
            1,
        )
