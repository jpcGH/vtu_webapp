import json
import logging

from django.http import HttpRequest, HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt

from apps.payments.services import handle_monnify_webhook, validate_monnify_signature

logger = logging.getLogger(__name__)


@csrf_exempt
def monnify_webhook(request: HttpRequest) -> HttpResponse:
    if request.method != 'POST':
        return JsonResponse({'detail': 'Method not allowed'}, status=405)

    signature = request.headers.get('monnify-signature', '')
    if not validate_monnify_signature(request.body, signature):
        logger.warning('Rejected Monnify webhook due to invalid signature.')
        return JsonResponse({'detail': 'Invalid signature'}, status=401)

    try:
        payload = json.loads(request.body.decode() or '{}')
    except json.JSONDecodeError:
        logger.warning('Rejected Monnify webhook due to invalid JSON payload.')
        return JsonResponse({'detail': 'Invalid payload'}, status=400)

    handle_monnify_webhook(payload)
    return JsonResponse({'status': 'accepted'}, status=200)
