from django.urls import path
from .views import monnify_webhook

app_name = 'payments'

urlpatterns = [
    path('webhooks/monnify/', monnify_webhook, name='monnify_webhook'),
]
