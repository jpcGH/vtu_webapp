from django.urls import path

from .views import buy_services, receipt, transaction_status

app_name = 'vtu'

urlpatterns = [
    path('buy/', buy_services, name='buy_services'),
    path('transactions/<str:reference>/', transaction_status, name='transaction_status'),
    path('transactions/<str:reference>/receipt/', receipt, name='receipt'),
]
