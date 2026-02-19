from django.contrib.admin.views.decorators import staff_member_required
from django.core.paginator import Paginator
from django.shortcuts import render

from apps.payments.models import PaymentWebhookEvent
from apps.payments.services import ensure_user_reserved_accounts


@staff_member_required
def operations_console(request):
    ensure_user_reserved_accounts(request.user)
    return render(request, 'dashboard/console.html')


@staff_member_required
def monnify_webhook_events(request):
    events = PaymentWebhookEvent.objects.order_by('-created_at')
    paginator = Paginator(events, 25)
    page_obj = paginator.get_page(request.GET.get('page', 1))
    return render(request, 'dashboard/monnify_webhook_events.html', {'page_obj': page_obj})
