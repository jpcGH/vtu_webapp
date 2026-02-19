from decimal import Decimal

from django.conf import settings

from apps.ledger.models import LedgerEntry
from apps.ledger.services import credit_wallet


def apply_referral_bonus(*, referrer_wallet, transaction_reference: str, transaction_amount: Decimal) -> LedgerEntry | None:
    if transaction_amount <= 0:
        return None

    bonus = (transaction_amount * Decimal(settings.REFERRAL_BONUS_PERCENT / 100)).quantize(Decimal('0.01'))
    if bonus <= 0:
        return None

    return credit_wallet(
        user=referrer_wallet.user,
        amount=bonus,
        reference=f'REF-{transaction_reference}',
        meta={'source_reference': transaction_reference},
        tx_type=LedgerEntry.TransactionType.REFERRAL_BONUS,
    )
