from decimal import Decimal

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models


class Wallet(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='wallet')
    balance = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self) -> str:
        return f'Wallet<{self.user_id}:{self.balance}>'

    def save(self, *args, **kwargs):
        if self.pk and not getattr(self, '_allow_balance_update', False):
            original_balance = type(self).objects.filter(pk=self.pk).values_list('balance', flat=True).first()
            if original_balance is not None and original_balance != self.balance:
                raise ValidationError('Wallet balance can only be changed through ledger services.')
        super().save(*args, **kwargs)


class LedgerEntry(models.Model):
    class TransactionType(models.TextChoices):
        FUNDING = 'FUNDING', 'Funding'
        AIRTIME = 'AIRTIME', 'Airtime'
        DATA = 'DATA', 'Data'
        BILL = 'BILL', 'Bill'
        REFERRAL_BONUS = 'REFERRAL_BONUS', 'Referral Bonus'
        REVERSAL = 'REVERSAL', 'Reversal'

    class Direction(models.TextChoices):
        CREDIT = 'CREDIT', 'Credit'
        DEBIT = 'DEBIT', 'Debit'

    class Status(models.TextChoices):
        PENDING = 'PENDING', 'Pending'
        SUCCESS = 'SUCCESS', 'Success'
        FAILED = 'FAILED', 'Failed'
        REVERSED = 'REVERSED', 'Reversed'

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='ledger_entries')
    reference = models.CharField(max_length=64, unique=True)
    tx_type = models.CharField(max_length=20, choices=TransactionType.choices)
    direction = models.CharField(max_length=6, choices=Direction.choices)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    status = models.CharField(max_length=8, choices=Status.choices, default=Status.PENDING)
    meta = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ('-created_at',)

    def save(self, *args, **kwargs):
        if self.pk:
            raise ValidationError('Ledger entries are immutable and cannot be edited once created.')
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ValidationError('Ledger entries are immutable and cannot be deleted.')
