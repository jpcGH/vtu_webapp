from decimal import Decimal
from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models, transaction


class Wallet(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='wallet')
    balance = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal('0.00'))
    currency = models.CharField(max_length=3, default='NGN')
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self) -> str:
        return f'Wallet<{self.user.username}:{self.balance}>'


class LedgerEntry(models.Model):
    class EntryType(models.TextChoices):
        CREDIT = 'CREDIT', 'Credit'
        DEBIT = 'DEBIT', 'Debit'

    wallet = models.ForeignKey(Wallet, on_delete=models.PROTECT, related_name='entries')
    amount = models.DecimalField(max_digits=14, decimal_places=2)
    entry_type = models.CharField(max_length=6, choices=EntryType.choices)
    reference = models.CharField(max_length=64, unique=True)
    narration = models.CharField(max_length=255)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ('-created_at',)

    def clean(self) -> None:
        if self.pk:
            raise ValidationError('Ledger entries are immutable and cannot be edited once created.')

    def save(self, *args, **kwargs):
        if self.pk:
            raise ValidationError('Ledger entries are immutable and cannot be edited once created.')
        super().save(*args, **kwargs)

    @classmethod
    @transaction.atomic
    def post_entry(cls, *, wallet: Wallet, amount: Decimal, entry_type: str, reference: str, narration: str, metadata=None):
        if amount <= 0:
            raise ValidationError('Amount must be greater than zero.')

        signed_amount = amount if entry_type == cls.EntryType.CREDIT else amount * Decimal('-1')
        wallet = Wallet.objects.select_for_update().get(pk=wallet.pk)
        next_balance = wallet.balance + signed_amount

        if next_balance < 0:
            raise ValidationError('Insufficient wallet balance for debit entry.')

        entry = cls.objects.create(
            wallet=wallet,
            amount=amount,
            entry_type=entry_type,
            reference=reference,
            narration=narration,
            metadata=metadata or {},
        )
        wallet.balance = next_balance
        wallet.save(update_fields=['balance', 'updated_at'])
        return entry
