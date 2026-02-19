from django.conf import settings
from django.db import models


class VirtualAccount(models.Model):
    class Provider(models.TextChoices):
        MONNIFY = 'MONNIFY', 'Monnify'

    class Status(models.TextChoices):
        ACTIVE = 'ACTIVE', 'Active'
        INACTIVE = 'INACTIVE', 'Inactive'

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='virtual_accounts')
    provider = models.CharField(max_length=20, choices=Provider.choices, default=Provider.MONNIFY)
    account_reference = models.CharField(max_length=120, default='')
    bank_name = models.CharField(max_length=120)
    account_number = models.CharField(max_length=20, unique=True)
    account_name = models.CharField(max_length=180)
    monnify_account_reference = models.CharField(max_length=120, blank=True)
    reserved_account_reference = models.CharField(max_length=120, blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.ACTIVE)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['provider', 'account_reference', 'account_number'],
                name='uniq_provider_account_ref_number',
            )
        ]


class PaymentWebhookEvent(models.Model):
    event_type = models.CharField(max_length=80)
    event_id = models.CharField(max_length=120, unique=True)
    payload = models.JSONField(default=dict)
    processed = models.BooleanField(default=False)
    processing_error = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)


class IncomingPayment(models.Model):
    class Status(models.TextChoices):
        RECEIVED = 'RECEIVED', 'Received'
        PROCESSED = 'PROCESSED', 'Processed'
        FAILED = 'FAILED', 'Failed'

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='incoming_payments')
    provider = models.CharField(max_length=20, default=VirtualAccount.Provider.MONNIFY)
    idempotency_key = models.CharField(max_length=120, unique=True)
    transaction_reference = models.CharField(max_length=120, blank=True)
    payment_reference = models.CharField(max_length=120, blank=True)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    currency = models.CharField(max_length=3, default='NGN')
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.RECEIVED)
    payload = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)
