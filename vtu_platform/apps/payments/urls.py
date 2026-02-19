from django.urls import path

from .views import monnify_webhook

app_name = 'payments'

urlpatterns = [
    path('monnify/webhook/', monnify_webhook, name='monnify_webhook'),
]
