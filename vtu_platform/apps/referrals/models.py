from django.conf import settings
from django.db import models


class ReferralBonus(models.Model):
    referrer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='earned_referral_bonuses')
    referee = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='generated_referral_bonuses')
    source_reference = models.CharField(max_length=64, unique=True)
    amount = models.DecimalField(max_digits=14, decimal_places=2)
    credited = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
