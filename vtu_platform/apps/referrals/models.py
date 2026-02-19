from decimal import Decimal

from django.conf import settings
from django.db import models


class Referral(models.Model):
    class Status(models.TextChoices):
        PENDING = 'PENDING', 'Pending'
        PAID = 'PAID', 'Paid'

    referrer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='referrals_made')
    referee = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='referral_record')
    referral_code_used = models.CharField(max_length=20, blank=True)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.PENDING)
    bonus_amount = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    bonus_reference = models.CharField(max_length=64, unique=True, blank=True)
    rewarded_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ('-created_at',)

    def __str__(self):
        return f'Referral<{self.referrer_id}->{self.referee_id}:{self.status}>'
