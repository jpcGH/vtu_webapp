from django.contrib import admin
from .models import PaymentWebhookEvent, VirtualAccount

admin.site.register(VirtualAccount)
admin.site.register(PaymentWebhookEvent)
