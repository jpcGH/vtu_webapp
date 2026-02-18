import json
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from .models import PaymentWebhookEvent


@csrf_exempt
def monnify_webhook(request: HttpRequest) -> HttpResponse:
    if request.method != 'POST':
        return JsonResponse({'detail': 'Method not allowed'}, status=405)

    payload = json.loads(request.body.decode() or '{}')
    event = payload.get('eventData', {})
    PaymentWebhookEvent.objects.get_or_create(
        event_id=event.get('transactionReference', 'unknown-ref'),
        defaults={'event_type': payload.get('eventType', 'UNKNOWN'), 'payload': payload},
    )
    return JsonResponse({'status': 'accepted'})
