from django.urls import path

from .views import monnify_webhook_events, operations_console

app_name = 'dashboard'

urlpatterns = [
    path('', operations_console, name='console'),
    path('monnify-webhooks/', monnify_webhook_events, name='monnify_webhook_events'),
]
