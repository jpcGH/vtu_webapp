from django.urls import path
from .views import referral_dashboard

app_name = 'referrals'

urlpatterns = [
    path('', referral_dashboard, name='dashboard'),
]
