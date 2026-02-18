import hashlib
import hmac
import json
from django.conf import settings


def monnify_webhook_signature(payload: dict) -> str:
    body = json.dumps(payload, separators=(',', ':'), sort_keys=True).encode()
    secret = settings.MONNIFY_SECRET_KEY.encode()
    return hmac.new(secret, body, hashlib.sha512).hexdigest()
