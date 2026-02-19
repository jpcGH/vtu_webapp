import logging

from django.contrib.auth import get_user_model
from django.db.models.signals import post_save
from django.dispatch import receiver

from apps.payments.services import ensure_user_reserved_accounts

logger = logging.getLogger(__name__)


@receiver(post_save, sender=get_user_model())
def provision_monnify_reserved_account(sender, instance, created, **kwargs):
    if not created:
        return
    try:
        ensure_user_reserved_accounts(instance)
    except Exception:  # noqa: BLE001
        logger.exception('Failed to provision Monnify reserved account for user %s', instance.pk)
