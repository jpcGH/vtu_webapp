from django.urls import path
from .views import wallet_overview

app_name = 'ledger'

urlpatterns = [
    path('wallet/', wallet_overview, name='wallet_overview'),
]
