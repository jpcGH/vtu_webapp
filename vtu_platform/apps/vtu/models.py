from uuid import uuid4

from django.conf import settings
from django.db import models


class ServiceProvider(models.Model):
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=100, unique=True)
    base_url = models.URLField(blank=True)
    api_key = models.CharField(max_length=150, blank=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.name


def generate_order_reference():
    return f'VTU-{uuid4().hex[:12].upper()}'


class PurchaseOrder(models.Model):
    class ProductType(models.TextChoices):
        AIRTIME = 'airtime', 'Airtime'
        DATA = 'data', 'Data'
        BILL = 'bill', 'Bill Payment'

    class Status(models.TextChoices):
        PENDING = 'pending', 'Pending'
        SUCCESS = 'success', 'Success'
        FAILED = 'failed', 'Failed'

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='vtu_orders')
    provider = models.ForeignKey(ServiceProvider, on_delete=models.PROTECT, related_name='orders')
    reference = models.CharField(max_length=32, unique=True, default=generate_order_reference)
    product_type = models.CharField(max_length=20, choices=ProductType.choices)
    amount = models.DecimalField(max_digits=14, decimal_places=2)
    destination = models.CharField(max_length=50)
    service_code = models.CharField(max_length=50, blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    provider_reference = models.CharField(max_length=80, blank=True)
    ledger_reference = models.CharField(max_length=80, blank=True)
    message = models.CharField(max_length=255, blank=True)
    provider_response = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f'{self.reference} ({self.get_status_display()})'
