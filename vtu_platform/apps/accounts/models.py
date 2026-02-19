from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import IntegrityError
from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils.crypto import get_random_string


class Profile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='profile')
    phone = models.CharField(max_length=15, blank=True)
    referral_code = models.CharField(max_length=20, unique=True)
    referred_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name='referrals'
    )
    email_verified = models.BooleanField(default=False)
    is_kyc_verified = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self) -> str:
        return f'Profile<{self.user.username}>'


def generate_referral_code() -> str:
    return get_random_string(10).upper()


@receiver(post_save, sender=get_user_model())
def ensure_user_profile(sender, instance, created, **kwargs):
    if not created:
        return

    for _ in range(5):
        code = generate_referral_code()
        try:
            Profile.objects.create(user=instance, referral_code=code)
            return
        except IntegrityError:
            continue

    Profile.objects.create(user=instance, referral_code=f'USR{instance.pk:08d}')


@receiver(post_save, sender=Profile)
def sync_referral_record_and_bonus(sender, instance, **kwargs):
    if instance.referred_by:
        from apps.referrals.models import Referral

        Referral.objects.get_or_create(
            referee=instance.user,
            defaults={
                'referrer': instance.referred_by,
                'referral_code_used': instance.referred_by.profile.referral_code if hasattr(instance.referred_by, 'profile') else '',
            },
        )

    if not instance.email_verified:
        return

    from apps.referrals.services import evaluate_referral_bonus

    evaluate_referral_bonus(instance.user)
