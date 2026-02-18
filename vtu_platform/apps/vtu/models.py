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
    product_type = models.CharField(max_length=20, choices=ProductType.choices)
    amount = models.DecimalField(max_digits=14, decimal_places=2)
    destination = models.CharField(max_length=50)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    provider_reference = models.CharField(max_length=80, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
