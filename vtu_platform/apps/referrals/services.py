from decimal import Decimal
from django.conf import settings
from apps.ledger.models import LedgerEntry


def apply_referral_bonus(*, referrer_wallet, transaction_reference: str, transaction_amount: Decimal) -> LedgerEntry | None:
    if transaction_amount <= 0:
        return None

    bonus = (transaction_amount * Decimal(settings.REFERRAL_BONUS_PERCENT / 100)).quantize(Decimal('0.01'))
    if bonus <= 0:
        return None

    return LedgerEntry.post_entry(
        wallet=referrer_wallet,
        amount=bonus,
        entry_type=LedgerEntry.EntryType.CREDIT,
        reference=f'REF-{transaction_reference}',
        narration='Referral bonus credit',
        metadata={'source_reference': transaction_reference},
    )
