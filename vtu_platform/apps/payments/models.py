from django.conf import settings
from django.db import models


class VirtualAccount(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='virtual_accounts')
    account_number = models.CharField(max_length=20, unique=True)
    bank_name = models.CharField(max_length=80)
    account_name = models.CharField(max_length=120)
    provider_ref = models.CharField(max_length=120, unique=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)


class PaymentWebhookEvent(models.Model):
    event_type = models.CharField(max_length=80)
    event_id = models.CharField(max_length=120, unique=True)
    payload = models.JSONField(default=dict)
    processed = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
