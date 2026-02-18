from django.contrib.auth.decorators import login_required
from django.shortcuts import render


@login_required
def wallet_overview(request):
    return render(request, 'ledger/wallet_overview.html')
