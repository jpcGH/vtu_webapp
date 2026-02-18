from django.contrib.auth.decorators import login_required
from django.shortcuts import render


@login_required
def referral_dashboard(request):
    return render(request, 'referrals/dashboard.html')
