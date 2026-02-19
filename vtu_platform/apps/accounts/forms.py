from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import UserCreationForm

from apps.accounts.models import Profile


class SignUpForm(UserCreationForm):
    email = forms.EmailField(required=True)
    referral_code = forms.CharField(max_length=20, required=False)

    class Meta(UserCreationForm.Meta):
        model = get_user_model()
        fields = ('username', 'email', 'password1', 'password2', 'referral_code')

    def clean_referral_code(self):
        code = (self.cleaned_data.get('referral_code') or '').strip()
        if not code:
            return None

        referrer_profile = Profile.objects.select_related('user').filter(referral_code__iexact=code).first()
        if not referrer_profile:
            raise forms.ValidationError('Referral code is invalid.')
        return referrer_profile.user
