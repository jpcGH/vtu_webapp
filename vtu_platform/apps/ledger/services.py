from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import transaction

from apps.ledger.models import LedgerEntry, Wallet


def _validate_amount(amount: Decimal) -> Decimal:
    if amount is None or amount <= 0:
        raise ValidationError('Amount must be greater than zero.')
    return amount.quantize(Decimal('0.01'))


@transaction.atomic
def credit_wallet(user, amount: Decimal, reference: str, meta=None, tx_type: str = LedgerEntry.TransactionType.FUNDING):
    amount = _validate_amount(amount)
    wallet, _ = Wallet.objects.select_for_update().get_or_create(user=user)

    existing_entry = LedgerEntry.objects.filter(reference=reference).first()
    if existing_entry and existing_entry.status == LedgerEntry.Status.SUCCESS:
        return existing_entry
    if existing_entry:
        raise ValidationError('Reference already exists with non-success status and cannot be reused.')

    entry = LedgerEntry.objects.create(
        user=user,
        reference=reference,
        tx_type=tx_type,
        direction=LedgerEntry.Direction.CREDIT,
        amount=amount,
        status=LedgerEntry.Status.SUCCESS,
        meta=meta or {},
    )

    wallet.balance += amount
    wallet._allow_balance_update = True
    wallet.save(update_fields=['balance', 'updated_at'])
    return entry


@transaction.atomic
def debit_wallet(user, amount: Decimal, reference: str, meta=None, tx_type: str = LedgerEntry.TransactionType.BILL):
    amount = _validate_amount(amount)
    wallet, _ = Wallet.objects.select_for_update().get_or_create(user=user)

    existing_entry = LedgerEntry.objects.filter(reference=reference).first()
    if existing_entry and existing_entry.status == LedgerEntry.Status.SUCCESS:
        return existing_entry
    if existing_entry:
        raise ValidationError('Reference already exists with non-success status and cannot be reused.')

    if wallet.balance < amount:
        return LedgerEntry.objects.create(
            user=user,
            reference=reference,
            tx_type=tx_type,
            direction=LedgerEntry.Direction.DEBIT,
            amount=amount,
            status=LedgerEntry.Status.FAILED,
            meta={**(meta or {}), 'reason': 'insufficient_funds'},
        )

    entry = LedgerEntry.objects.create(
        user=user,
        reference=reference,
        tx_type=tx_type,
        direction=LedgerEntry.Direction.DEBIT,
        amount=amount,
        status=LedgerEntry.Status.SUCCESS,
        meta=meta or {},
    )

    wallet.balance -= amount
    wallet._allow_balance_update = True
    wallet.save(update_fields=['balance', 'updated_at'])
    return entry


@transaction.atomic
def reverse_transaction(reference: str, reason: str):
    original_entry = LedgerEntry.objects.select_for_update().get(reference=reference)

    reversal_reference = f'REV-{reference}'
    existing_reversal = LedgerEntry.objects.filter(reference=reversal_reference).first()
    if existing_reversal and existing_reversal.status == LedgerEntry.Status.SUCCESS:
        return existing_reversal
    if existing_reversal:
        raise ValidationError('Reversal reference already exists with non-success status and cannot be reused.')

    if original_entry.direction != LedgerEntry.Direction.DEBIT or original_entry.status != LedgerEntry.Status.SUCCESS:
        raise ValidationError('Only successful debit transactions can be reversed.')

    wallet = Wallet.objects.select_for_update().get(user=original_entry.user)
    reversal_entry = LedgerEntry.objects.create(
        user=original_entry.user,
        reference=reversal_reference,
        tx_type=LedgerEntry.TransactionType.REVERSAL,
        direction=LedgerEntry.Direction.CREDIT,
        amount=original_entry.amount,
        status=LedgerEntry.Status.SUCCESS,
        meta={
            'reversed_reference': reference,
            'reason': reason,
        },
    )

    wallet.balance += original_entry.amount
    wallet._allow_balance_update = True
    wallet.save(update_fields=['balance', 'updated_at'])
    return reversal_entry
