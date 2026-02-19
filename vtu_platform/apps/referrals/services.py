from decimal import Decimal

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from apps.ledger.models import LedgerEntry
from apps.ledger.services import credit_wallet
from apps.referrals.models import Referral
from apps.vtu.models import PurchaseOrder


def _bonus_amount(minimum_funding: Decimal) -> Decimal:
    return (minimum_funding * Decimal(settings.REFERRAL_BONUS_PERCENT / 100)).quantize(Decimal('0.01'))


@transaction.atomic
def evaluate_referral_bonus(referee_user):
    profile = getattr(referee_user, 'profile', None)
    if not profile or not profile.referred_by:
        return None

    referral, _ = Referral.objects.select_for_update().get_or_create(
        referee=referee_user,
        defaults={
            'referrer': profile.referred_by,
            'referral_code_used': getattr(profile.referred_by, 'profile', None).referral_code if hasattr(profile.referred_by, 'profile') else '',
        },
    )

    if referral.status == Referral.Status.PAID:
        return referral

    min_fund = Decimal(str(settings.REFERRAL_MIN_FUND)).quantize(Decimal('0.01'))
    qualifying_funding_exists = LedgerEntry.objects.filter(
        user=referee_user,
        tx_type=LedgerEntry.TransactionType.FUNDING,
        direction=LedgerEntry.Direction.CREDIT,
        status=LedgerEntry.Status.SUCCESS,
        amount__gte=min_fund,
    ).exists()

    qualifying_purchase_exists = PurchaseOrder.objects.filter(
        user=referee_user,
        status=PurchaseOrder.Status.SUCCESS,
        product_type__in=[
            PurchaseOrder.ProductType.AIRTIME,
            PurchaseOrder.ProductType.DATA,
            PurchaseOrder.ProductType.BILL,
        ],
    ).exists()

    if not (profile.email_verified and qualifying_funding_exists and qualifying_purchase_exists):
        return referral

    bonus = _bonus_amount(min_fund)
    if bonus <= 0:
        return referral

    bonus_reference = referral.bonus_reference or f'REF-BONUS-{referee_user.pk}'
    entry = credit_wallet(
        user=referral.referrer,
        amount=bonus,
        reference=bonus_reference,
        tx_type=LedgerEntry.TransactionType.REFERRAL_BONUS,
        meta={
            'referee_id': referee_user.pk,
            'referee_username': referee_user.username,
        },
    )

    referral.status = Referral.Status.PAID
    referral.bonus_amount = entry.amount
    referral.bonus_reference = bonus_reference
    referral.rewarded_at = timezone.now()
    referral.save(update_fields=['status', 'bonus_amount', 'bonus_reference', 'rewarded_at'])
    return referral
