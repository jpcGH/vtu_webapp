from django.contrib import admin
from .models import PurchaseOrder, ServiceProvider

admin.site.register(ServiceProvider)
admin.site.register(PurchaseOrder)
