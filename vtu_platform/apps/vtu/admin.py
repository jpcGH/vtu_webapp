from django.contrib import admin

from apps.vtu.models import DataBundlePlan, PurchaseOrder, ServiceProvider

admin.site.register(ServiceProvider)
admin.site.register(PurchaseOrder)
admin.site.register(DataBundlePlan)
