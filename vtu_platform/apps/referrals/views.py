from decimal import Decimal
from urllib.parse import quote_plus

from django.contrib.auth.decorators import login_required
from django.db.models import Count, Q, Sum
from django.shortcuts import render

from apps.referrals.models import Referral


@login_required
def referral_dashboard(request):
    profile = getattr(request.user, 'profile', None)
    code = profile.referral_code if profile else ''
    signup_link = f"{request.build_absolute_uri('/accounts/signup/')}?ref={code}" if code else ''

    referrals = Referral.objects.filter(referrer=request.user)
    stats = referrals.aggregate(
        total=Count('id'),
        paid=Count('id', filter=Q(status=Referral.Status.PAID)),
        pending=Count('id', filter=Q(status=Referral.Status.PENDING)),
        total_bonus=Sum('bonus_amount'),
    )

    whatsapp_text = quote_plus(f'Join VTU Platform with my referral code {code}: {signup_link}') if code else ''

    context = {
        'referral_code': code,
        'referral_link': signup_link,
        'whatsapp_share_link': f'https://wa.me/?text={whatsapp_text}' if whatsapp_text else '',
        'stats': {
            'total': stats['total'] or 0,
            'paid': stats['paid'] or 0,
            'pending': stats['pending'] or 0,
            'total_bonus': stats['total_bonus'] or Decimal('0.00'),
        },
    }
    return render(request, 'referrals/dashboard.html', context)
