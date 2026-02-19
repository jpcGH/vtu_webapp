from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import close_old_connections
from django.test import TestCase, TransactionTestCase

from .models import LedgerEntry, Wallet
from .services import credit_wallet, debit_wallet, reverse_transaction


class LedgerServiceTestCase(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username='alice', email='alice@example.com', password='testpass123')

    def test_credit_wallet_is_idempotent_with_successful_reference(self):
        first = credit_wallet(self.user, Decimal('100.00'), 'REF-100', {'source': 'test'})
        second = credit_wallet(self.user, Decimal('100.00'), 'REF-100', {'source': 'test'})

        wallet = Wallet.objects.get(user=self.user)
        self.assertEqual(first.pk, second.pk)
        self.assertEqual(wallet.balance, Decimal('100.00'))
        self.assertEqual(LedgerEntry.objects.filter(reference='REF-100').count(), 1)

    def test_debit_prevents_negative_balances(self):
        credit_wallet(self.user, Decimal('50.00'), 'REF-200')

        with self.assertRaises(ValidationError):
            debit_wallet(self.user, Decimal('60.00'), 'REF-201')

        wallet = Wallet.objects.get(user=self.user)
        self.assertEqual(wallet.balance, Decimal('50.00'))
        self.assertFalse(LedgerEntry.objects.filter(reference='REF-201').exists())

    def test_reverse_transaction_is_idempotent(self):
        credit_wallet(self.user, Decimal('100.00'), 'REF-300')
        debit_wallet(self.user, Decimal('40.00'), 'REF-301')

        first_reversal = reverse_transaction('REF-301', 'provider timeout')
        second_reversal = reverse_transaction('REF-301', 'provider timeout')

        wallet = Wallet.objects.get(user=self.user)
        self.assertEqual(first_reversal.pk, second_reversal.pk)
        self.assertEqual(wallet.balance, Decimal('100.00'))
        self.assertEqual(first_reversal.meta['reversed_reference'], 'REF-301')

    def test_wallet_balance_change_outside_services_is_blocked(self):
        credit_wallet(self.user, Decimal('25.00'), 'REF-400')
        wallet = Wallet.objects.get(user=self.user)
        wallet.balance = Decimal('26.00')

        with self.assertRaises(ValidationError):
            wallet.save(update_fields=['balance'])


class LedgerConcurrencyTestCase(TransactionTestCase):
    reset_sequences = True

    def setUp(self):
        self.user = get_user_model().objects.create_user(username='bob', email='bob@example.com', password='testpass123')
        credit_wallet(self.user, Decimal('100.00'), 'SEED-REF')

    def _try_debit(self, reference):
        close_old_connections()
        try:
            debit_wallet(self.user, Decimal('80.00'), reference)
            return 'success'
        except ValidationError:
            return 'insufficient'


    def _try_credit_same_reference(self):
        close_old_connections()
        credit_wallet(self.user, Decimal('30.00'), 'DUP-REF')
        return 'ok'

    def test_concurrent_same_reference_is_idempotent(self):
        with ThreadPoolExecutor(max_workers=2) as executor:
            list(executor.map(lambda _: self._try_credit_same_reference(), [1, 2]))

        wallet = Wallet.objects.get(user=self.user)
        self.assertEqual(wallet.balance, Decimal('130.00'))
        self.assertEqual(LedgerEntry.objects.filter(reference='DUP-REF').count(), 1)

    def test_concurrent_debits_only_allow_one_success(self):
        with ThreadPoolExecutor(max_workers=2) as executor:
            results = list(executor.map(self._try_debit, ['CONC-1', 'CONC-2']))

        wallet = Wallet.objects.get(user=self.user)
        self.assertEqual(results.count('success'), 1)
        self.assertEqual(results.count('insufficient'), 1)
        self.assertEqual(wallet.balance, Decimal('20.00'))
        self.assertEqual(
            LedgerEntry.objects.filter(user=self.user, direction=LedgerEntry.Direction.DEBIT, status=LedgerEntry.Status.SUCCESS).count(),
            1,
        )
