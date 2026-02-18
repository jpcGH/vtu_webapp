from django.contrib.auth.decorators import login_required
from django.shortcuts import render


@login_required
def buy_services(request):
    return render(request, 'vtu/buy_services.html')
