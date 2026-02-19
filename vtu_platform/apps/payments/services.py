import base64
import hashlib
import hmac
import json
import logging
from dataclasses import dataclass
from decimal import Decimal
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from django.conf import settings
from django.core.cache import cache
from django.db import transaction
from django.utils.crypto import constant_time_compare

from apps.ledger.models import LedgerEntry
from apps.ledger.services import credit_wallet
from apps.payments.models import IncomingPayment, PaymentWebhookEvent, VirtualAccount
from apps.referrals.services import evaluate_referral_bonus

logger = logging.getLogger(__name__)


class MonnifyAPIError(Exception):
    pass


@dataclass
class ReservedAccountResult:
    account_reference: str
    accounts: list[dict]


class MonnifyClient:
    TOKEN_CACHE_KEY = 'monnify_access_token'

    def _request(self, method: str, path: str, data: dict | None = None, headers: dict | None = None) -> dict:
        body = None
        req_headers = {'Content-Type': 'application/json'}
        if headers:
            req_headers.update(headers)
        if data is not None:
            body = json.dumps(data).encode()

        request = Request(f"{settings.MONNIFY_BASE_URL.rstrip('/')}{path}", data=body, method=method)
        for key, value in req_headers.items():
            request.add_header(key, value)

        try:
            with urlopen(request, timeout=15) as response:
                payload = json.loads(response.read().decode() or '{}')
        except (HTTPError, URLError, TimeoutError) as exc:
            raise MonnifyAPIError(f'Monnify request failed: {exc}') from exc

        if not payload.get('requestSuccessful', False):
            raise MonnifyAPIError(payload.get('responseMessage', 'Monnify request unsuccessful'))
        return payload.get('responseBody', {})

    def get_access_token(self) -> str:
        cached_token = cache.get(self.TOKEN_CACHE_KEY)
        if cached_token:
            return cached_token

        credentials = f'{settings.MONNIFY_API_KEY}:{settings.MONNIFY_SECRET_KEY}'.encode()
        auth_header = base64.b64encode(credentials).decode()
        response_body = self._request('POST', '/api/v1/auth/login', headers={'Authorization': f'Basic {auth_header}'})
        token = response_body.get('accessToken')
        expires_in = int(response_body.get('expiresIn', 300))
        if not token:
            raise MonnifyAPIError('Monnify auth token missing in response.')
        cache.set(self.TOKEN_CACHE_KEY, token, timeout=max(expires_in - 60, 60))
        return token

    def reserve_account(self, *, account_reference: str, account_name: str, customer_email: str, customer_name: str) -> ReservedAccountResult:
        token = self.get_access_token()
        payload = {
            'accountReference': account_reference,
            'accountName': account_name,
            'currencyCode': 'NGN',
            'contractCode': settings.MONNIFY_CONTRACT_CODE,
            'customerEmail': customer_email,
            'customerName': customer_name,
            'getAllAvailableBanks': True,
        }
        response_body = self._request(
            'POST',
            '/api/v2/bank-transfer/reserved-accounts',
            data=payload,
            headers={'Authorization': f'Bearer {token}'},
        )
        return ReservedAccountResult(
            account_reference=response_body.get('accountReference') or account_reference,
            accounts=response_body.get('accounts', []),
        )


def monnify_webhook_signature(raw_body: bytes) -> str:
    secret = settings.MONNIFY_SECRET_KEY.encode()
    return hmac.new(secret, raw_body, hashlib.sha512).hexdigest()


def validate_monnify_signature(raw_body: bytes, signature_header: str) -> bool:
    if not signature_header:
        return False
    expected = monnify_webhook_signature(raw_body)
    return constant_time_compare(expected, signature_header)


def _user_from_webhook_event(event_data: dict):
    account_number = (event_data.get('destinationAccountInformation') or {}).get('accountNumber')
    payment_description = event_data.get('paymentDescription') or ''
    references = {
        event_data.get('accountReference'),
        event_data.get('reservedAccountReference'),
    }
    references = {ref for ref in references if ref}

    query = VirtualAccount.objects.filter(provider=VirtualAccount.Provider.MONNIFY)
    if account_number:
        va = query.filter(account_number=account_number).select_related('user').first()
        if va:
            return va.user
    if references:
        va = query.filter(account_reference__in=references).select_related('user').first()
        if va:
            return va.user
    if payment_description:
        va = query.filter(account_reference__icontains=payment_description).select_related('user').first()
        if va:
            return va.user
    return None


def process_monnify_transaction_event(payload: dict) -> None:
    event_data = payload.get('eventData') or {}
    tx_ref = event_data.get('transactionReference')
    payment_ref = event_data.get('paymentReference')
    idempotency_key = tx_ref or payment_ref
    if not idempotency_key:
        raise ValueError('Missing transactionReference/paymentReference for idempotency.')

    user = _user_from_webhook_event(event_data)
    if not user:
        raise ValueError('Unable to match webhook event to a user account.')

    amount = Decimal(str(event_data.get('amountPaid', '0'))).quantize(Decimal('0.01'))
    if amount <= 0:
        raise ValueError('Invalid amount in webhook payload.')

    with transaction.atomic():
        incoming, created = IncomingPayment.objects.get_or_create(
            idempotency_key=idempotency_key,
            defaults={
                'user': user,
                'provider': VirtualAccount.Provider.MONNIFY,
                'transaction_reference': tx_ref or '',
                'payment_reference': payment_ref or '',
                'amount': amount,
                'currency': event_data.get('currency', 'NGN'),
                'status': IncomingPayment.Status.RECEIVED,
                'payload': payload,
            },
        )
        if not created and incoming.status == IncomingPayment.Status.PROCESSED:
            return

        ledger_reference = f"MONNIFY_{tx_ref or payment_ref}"
        credit_wallet(
            user=user,
            amount=amount,
            reference=ledger_reference,
            tx_type=LedgerEntry.TransactionType.FUNDING,
            meta={
                'provider': 'MONNIFY',
                'transactionReference': tx_ref,
                'paymentReference': payment_ref,
                'payerName': event_data.get('payerName'),
                'payerEmail': event_data.get('payerEmail'),
                'bankName': (event_data.get('destinationAccountInformation') or {}).get('bankName'),
                'accountNumber': (event_data.get('destinationAccountInformation') or {}).get('accountNumber'),
            },
        )

        incoming.status = IncomingPayment.Status.PROCESSED
        incoming.save(update_fields=['status'])

        evaluate_referral_bonus(user)


def ensure_user_reserved_accounts(user) -> int:
    if VirtualAccount.objects.filter(user=user, provider=VirtualAccount.Provider.MONNIFY).exists():
        return 0

    if not all([settings.MONNIFY_API_KEY, settings.MONNIFY_SECRET_KEY, settings.MONNIFY_CONTRACT_CODE]):
        logger.warning('Monnify credentials are not fully configured; skipping reserved account provisioning for user %s', user.pk)
        return 0

    account_reference = f"USR-{user.pk}"
    account_name = f"{user.get_full_name().strip() or user.username} Wallet"
    customer_name = user.get_full_name().strip() or user.username
    customer_email = user.email or f'user-{user.pk}@example.com'

    client = MonnifyClient()
    result = client.reserve_account(
        account_reference=account_reference,
        account_name=account_name,
        customer_email=customer_email,
        customer_name=customer_name,
    )

    created_count = 0
    for account in result.accounts:
        _, created = VirtualAccount.objects.get_or_create(
            user=user,
            provider=VirtualAccount.Provider.MONNIFY,
            account_reference=result.account_reference,
            account_number=account.get('accountNumber', ''),
            defaults={
                'bank_name': account.get('bankName', ''),
                'account_name': account.get('accountName', account_name),
                'monnify_account_reference': account.get('accountReference', ''),
                'reserved_account_reference': account.get('reservedAccountReference', ''),
                'status': VirtualAccount.Status.ACTIVE,
            },
        )
        created_count += int(created)
    return created_count


def handle_monnify_webhook(payload: dict) -> None:
    event_data = payload.get('eventData') or {}
    event_id = event_data.get('transactionReference') or event_data.get('paymentReference') or 'unknown-ref'
    event, _ = PaymentWebhookEvent.objects.get_or_create(
        event_id=event_id,
        defaults={'event_type': payload.get('eventType', 'UNKNOWN'), 'payload': payload},
    )
    try:
        if payload.get('eventType') == 'SUCCESSFUL_TRANSACTION':
            process_monnify_transaction_event(payload)
        event.processed = True
        event.processing_error = ''
    except Exception as exc:  # noqa: BLE001
        logger.exception('Failed processing Monnify webhook event %s', event_id)
        event.processed = False
        event.processing_error = str(exc)
    event.save(update_fields=['processed', 'processing_error'])
