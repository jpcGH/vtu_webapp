from django.contrib import admin

from .models import IncomingPayment, PaymentWebhookEvent, VirtualAccount

admin.site.register(VirtualAccount)
admin.site.register(PaymentWebhookEvent)
admin.site.register(IncomingPayment)
