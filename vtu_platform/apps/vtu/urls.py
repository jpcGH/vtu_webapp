from django.urls import path
from .views import buy_services

app_name = 'vtu'

urlpatterns = [
    path('buy/', buy_services, name='buy_services'),
]
