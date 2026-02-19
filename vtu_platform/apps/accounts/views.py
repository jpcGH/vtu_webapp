from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render

from apps.accounts.forms import SignUpForm


@login_required
def profile(request):
    return render(request, 'accounts/profile.html')


def signup(request):
    if request.user.is_authenticated:
        return redirect('core:home')

    initial = {}
    if request.method == 'GET' and request.GET.get('ref'):
        initial['referral_code'] = request.GET.get('ref')
    form = SignUpForm(request.POST or None, initial=initial)
    if request.method == 'POST' and form.is_valid():
        user = form.save(commit=False)
        user.email = form.cleaned_data['email']
        user.save()

        referrer = form.cleaned_data.get('referral_code')
        if referrer:
            user.profile.referred_by = referrer
            user.profile.save(update_fields=['referred_by'])

        login(request, user)
        return redirect('core:home')

    return render(request, 'registration/signup.html', {'form': form})
