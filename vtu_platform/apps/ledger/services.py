from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction

from .models import LedgerEntry, Wallet


class LedgerConflictError(ValidationError):
    pass


def _validate_amount(amount: Decimal) -> Decimal:
    if amount is None:
        raise ValidationError('Amount is required.')
    normalized = Decimal(amount).quantize(Decimal('0.01'))
    if normalized <= 0:
        raise ValidationError('Amount must be greater than zero.')
    return normalized


def _get_locked_wallet(user):
    wallet, _ = Wallet.objects.get_or_create(user=user, defaults={'balance': Decimal('0.00')})
    return Wallet.objects.select_for_update().get(pk=wallet.pk)


def _persist_wallet_balance(wallet: Wallet, next_balance: Decimal):
    wallet.balance = next_balance.quantize(Decimal('0.01'))
    wallet._allow_balance_update = True
    try:
        wallet.save(update_fields=['balance', 'updated_at'])
    finally:
        wallet._allow_balance_update = False


@transaction.atomic
def credit_wallet(user, amount, reference, meta=None, tx_type=LedgerEntry.TransactionType.FUNDING):
    amount = _validate_amount(amount)
    existing = LedgerEntry.objects.filter(reference=reference).first()
    if existing:
        if existing.status == LedgerEntry.Status.SUCCESS:
            return existing
        raise LedgerConflictError('Reference already exists with non-success status.')

    wallet = _get_locked_wallet(user)
    next_balance = wallet.balance + amount
    try:
        entry = LedgerEntry.objects.create(
            user=user,
            reference=reference,
            tx_type=tx_type,
            direction=LedgerEntry.Direction.CREDIT,
            amount=amount,
            status=LedgerEntry.Status.SUCCESS,
            meta=meta or {},
        )
    except IntegrityError:
        existing = LedgerEntry.objects.filter(reference=reference, status=LedgerEntry.Status.SUCCESS).first()
        if existing:
            return existing
        raise
    _persist_wallet_balance(wallet, next_balance)
    return entry


@transaction.atomic
def debit_wallet(user, amount, reference, meta=None, tx_type=LedgerEntry.TransactionType.BILL):
    amount = _validate_amount(amount)
    existing = LedgerEntry.objects.filter(reference=reference).first()
    if existing:
        if existing.status == LedgerEntry.Status.SUCCESS:
            return existing
        raise LedgerConflictError('Reference already exists with non-success status.')

    wallet = _get_locked_wallet(user)
    next_balance = wallet.balance - amount
    if next_balance < 0:
        raise ValidationError('Insufficient wallet balance.')

    try:
        entry = LedgerEntry.objects.create(
            user=user,
            reference=reference,
            tx_type=tx_type,
            direction=LedgerEntry.Direction.DEBIT,
            amount=amount,
            status=LedgerEntry.Status.SUCCESS,
            meta=meta or {},
        )
    except IntegrityError:
        existing = LedgerEntry.objects.filter(reference=reference, status=LedgerEntry.Status.SUCCESS).first()
        if existing:
            return existing
        raise
    _persist_wallet_balance(wallet, next_balance)
    return entry


@transaction.atomic
def reverse_transaction(reference, reason):
    original = LedgerEntry.objects.select_for_update().filter(reference=reference).first()
    if not original:
        raise ValidationError('Transaction reference not found.')

    if original.direction != LedgerEntry.Direction.DEBIT:
        raise ValidationError('Only successful debit transactions can be reversed.')

    if original.status != LedgerEntry.Status.SUCCESS:
        raise ValidationError('Only successful debit transactions can be reversed.')

    reversal_reference = f'REV-{reference}'
    existing_reversal = LedgerEntry.objects.filter(reference=reversal_reference).first()
    if existing_reversal and existing_reversal.status == LedgerEntry.Status.SUCCESS:
        return existing_reversal
    if existing_reversal:
        raise LedgerConflictError('Reversal reference already exists with non-success status.')

    wallet = _get_locked_wallet(original.user)
    next_balance = wallet.balance + original.amount

    try:
        reversal = LedgerEntry.objects.create(
            user=original.user,
            reference=reversal_reference,
            tx_type=LedgerEntry.TransactionType.REVERSAL,
            direction=LedgerEntry.Direction.CREDIT,
            amount=original.amount,
            status=LedgerEntry.Status.SUCCESS,
            meta={
                'reversed_reference': reference,
                'reason': reason,
            },
        )
    except IntegrityError:
        existing_reversal = LedgerEntry.objects.filter(reference=reversal_reference, status=LedgerEntry.Status.SUCCESS).first()
        if existing_reversal:
            return existing_reversal
        raise
    _persist_wallet_balance(wallet, next_balance)
    return reversal
