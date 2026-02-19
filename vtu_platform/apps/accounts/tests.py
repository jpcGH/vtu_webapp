from django.contrib.auth import get_user_model
from django.test import TestCase

from apps.accounts.models import Profile


class SignUpReferralTests(TestCase):
    def test_signup_with_referral_code_sets_referred_by(self):
        referrer = get_user_model().objects.create_user(username='referrer', password='secret123')

        response = self.client.post(
            '/accounts/signup/',
            {
                'username': 'new-user',
                'email': 'new-user@example.com',
                'password1': 'Strongpass123!',
                'password2': 'Strongpass123!',
                'referral_code': referrer.profile.referral_code,
            },
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        user = get_user_model().objects.get(username='new-user')
        self.assertEqual(user.profile.referred_by, referrer)
        self.assertTrue(Profile.objects.filter(user=user, referral_code__isnull=False).exists())
