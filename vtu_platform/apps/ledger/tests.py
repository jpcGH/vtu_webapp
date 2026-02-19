from decimal import Decimal
from threading import Barrier, Thread

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import close_old_connections
from django.test import TestCase, TransactionTestCase, skipUnlessDBFeature

from apps.ledger.models import LedgerEntry, Wallet
from apps.ledger.services import credit_wallet, debit_wallet, reverse_transaction


class WalletServiceTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username='ledger-user', password='secret123')

    def test_credit_wallet_is_idempotent_for_success_reference(self):
        first = credit_wallet(self.user, Decimal('100.00'), 'ref-credit-1', {'channel': 'bank'})
        second = credit_wallet(self.user, Decimal('100.00'), 'ref-credit-1', {'channel': 'bank'})

        wallet = Wallet.objects.get(user=self.user)
        self.assertEqual(first.pk, second.pk)
        self.assertEqual(wallet.balance, Decimal('100.00'))
        self.assertEqual(LedgerEntry.objects.count(), 1)

    def test_debit_wallet_prevents_negative_balance(self):
        Wallet.objects.create(user=self.user, balance=Decimal('20.00'))

        debit_entry = debit_wallet(self.user, Decimal('50.00'), 'ref-debit-1', {'product': 'airtime'})

        wallet = Wallet.objects.get(user=self.user)
        self.assertEqual(debit_entry.status, LedgerEntry.Status.FAILED)
        self.assertEqual(wallet.balance, Decimal('20.00'))

    def test_reverse_transaction_credits_wallet_once(self):
        credit_wallet(self.user, Decimal('120.00'), 'fund-1', {})
        debit_wallet(self.user, Decimal('40.00'), 'bill-1', {}, tx_type=LedgerEntry.TransactionType.BILL)

        first_reversal = reverse_transaction('bill-1', 'provider timeout')
        second_reversal = reverse_transaction('bill-1', 'provider timeout')

        wallet = Wallet.objects.get(user=self.user)
        self.assertEqual(first_reversal.pk, second_reversal.pk)
        self.assertEqual(wallet.balance, Decimal('120.00'))

    def test_wallet_balance_cannot_be_changed_directly(self):
        wallet = Wallet.objects.create(user=self.user, balance=Decimal('10.00'))
        wallet.balance = Decimal('99.00')

        with self.assertRaises(ValidationError):
            wallet.save(update_fields=['balance'])


@skipUnlessDBFeature('has_select_for_update')
class WalletConcurrencyTests(TransactionTestCase):
    reset_sequences = True

    def setUp(self):
        self.user = get_user_model().objects.create_user(username='concurrency-user', password='secret123')
        credit_wallet(self.user, Decimal('100.00'), 'seed-fund', {})

    def test_concurrent_debits_only_one_succeeds(self):
        barrier = Barrier(2)
        results = []

        def make_debit(reference):
            close_old_connections()
            barrier.wait()
            entry = debit_wallet(self.user, Decimal('80.00'), reference, {'source': 'thread'})
            results.append((reference, entry.status))
            close_old_connections()

        thread_a = Thread(target=make_debit, args=('con-debit-a',))
        thread_b = Thread(target=make_debit, args=('con-debit-b',))

        thread_a.start()
        thread_b.start()
        thread_a.join()
        thread_b.join()

        wallet = Wallet.objects.get(user=self.user)
        success_count = sum(1 for _, status in results if status == LedgerEntry.Status.SUCCESS)
        failed_count = sum(1 for _, status in results if status == LedgerEntry.Status.FAILED)

        self.assertEqual(success_count, 1)
        self.assertEqual(failed_count, 1)
        self.assertEqual(wallet.balance, Decimal('20.00'))
