from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings

from apps.ledger.models import LedgerEntry, Wallet
from apps.ledger.services import credit_wallet
from apps.referrals.models import Referral
from apps.referrals.services import evaluate_referral_bonus
from apps.vtu.models import PurchaseOrder, ServiceProvider


@override_settings(REFERRAL_MIN_FUND=1000.0, REFERRAL_BONUS_PERCENT=2.5)
class ReferralBonusEligibilityTests(TestCase):
    def setUp(self):
        self.referrer = get_user_model().objects.create_user(username='referrer', password='secret123')
        self.referee = get_user_model().objects.create_user(username='referee', password='secret123')
        self.referee.profile.referred_by = self.referrer
        self.referee.profile.save(update_fields=['referred_by'])
        self.provider = ServiceProvider.objects.create(name='Referral Provider', slug='ref-provider')

    def test_bonus_requires_all_conditions(self):
        evaluate_referral_bonus(self.referee)
        self.assertFalse(LedgerEntry.objects.filter(tx_type=LedgerEntry.TransactionType.REFERRAL_BONUS).exists())

        self.referee.profile.email_verified = True
        self.referee.profile.save(update_fields=['email_verified'])
        evaluate_referral_bonus(self.referee)
        self.assertFalse(LedgerEntry.objects.filter(tx_type=LedgerEntry.TransactionType.REFERRAL_BONUS).exists())

        credit_wallet(self.referee, Decimal('900.00'), 'fund-low', tx_type=LedgerEntry.TransactionType.FUNDING)
        evaluate_referral_bonus(self.referee)
        self.assertFalse(LedgerEntry.objects.filter(tx_type=LedgerEntry.TransactionType.REFERRAL_BONUS).exists())

        credit_wallet(self.referee, Decimal('1200.00'), 'fund-high', tx_type=LedgerEntry.TransactionType.FUNDING)
        PurchaseOrder.objects.create(
            user=self.referee,
            provider=self.provider,
            product_type=PurchaseOrder.ProductType.AIRTIME,
            amount=Decimal('200.00'),
            destination='08000000000',
            status=PurchaseOrder.Status.SUCCESS,
        )

        evaluate_referral_bonus(self.referee)

        referral = Referral.objects.get(referee=self.referee)
        bonus_entry = LedgerEntry.objects.get(reference=f'REF-BONUS-{self.referee.pk}')
        referrer_wallet = Wallet.objects.get(user=self.referrer)

        self.assertEqual(referral.status, Referral.Status.PAID)
        self.assertEqual(bonus_entry.tx_type, LedgerEntry.TransactionType.REFERRAL_BONUS)
        self.assertEqual(bonus_entry.amount, Decimal('25.00'))
        self.assertEqual(referrer_wallet.balance, Decimal('25.00'))

    def test_bonus_credit_is_idempotent(self):
        self.referee.profile.email_verified = True
        self.referee.profile.save(update_fields=['email_verified'])
        credit_wallet(self.referee, Decimal('1000.00'), 'fund-ok', tx_type=LedgerEntry.TransactionType.FUNDING)
        PurchaseOrder.objects.create(
            user=self.referee,
            provider=self.provider,
            product_type=PurchaseOrder.ProductType.DATA,
            amount=Decimal('300.00'),
            destination='08030000000',
            status=PurchaseOrder.Status.SUCCESS,
            service_code='mtn:500mb',
        )

        evaluate_referral_bonus(self.referee)
        evaluate_referral_bonus(self.referee)

        self.assertEqual(
            LedgerEntry.objects.filter(reference=f'REF-BONUS-{self.referee.pk}', tx_type=LedgerEntry.TransactionType.REFERRAL_BONUS).count(),
            1,
        )
        self.assertEqual(Referral.objects.filter(referee=self.referee, status=Referral.Status.PAID).count(), 1)
