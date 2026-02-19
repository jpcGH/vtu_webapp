from __future__ import annotations

import logging
from decimal import Decimal
from typing import Any

try:
    import requests
    from requests.adapters import HTTPAdapter
    from urllib3.util.retry import Retry
except ImportError:  # pragma: no cover
    class _FallbackRequestException(Exception):
        pass

    class _FallbackSession:
        def __init__(self):
            self.headers = {}

        def mount(self, *_args, **_kwargs):
            return None

        def request(self, *_args, **_kwargs):
            raise RuntimeError('The requests package is required for VTpassProvider.')

    class _FallbackRequests:
        Session = _FallbackSession
        RequestException = _FallbackRequestException

    class HTTPAdapter:  # type: ignore[override]
        def __init__(self, *args, **kwargs):
            pass

    class Retry:  # type: ignore[override]
        def __init__(self, *args, **kwargs):
            pass

    requests = _FallbackRequests()

from apps.vtu.providers.base import BaseProvider, VTUResult

logger = logging.getLogger(__name__)


class VTpassProvider(BaseProvider):
    SUCCESS_STATES = {'delivered', 'successful', 'success', 'completed'}
    PENDING_STATES = {'pending', 'processing', 'initiated'}

    def __init__(self, *, config: dict[str, str], timeout: tuple[int, int] = (5, 30)):
        self.base_url = config['base_url'].rstrip('/')
        self.api_key = config.get('api_key', '')
        self.username = config.get('username', '')
        self.password = config.get('password', '')
        self.timeout = timeout
        self.session = self._build_session()

    def _build_session(self) -> requests.Session:
        session = requests.Session()
        retries = Retry(
            total=3,
            backoff_factor=0.5,
            status_forcelist=(429, 500, 502, 503, 504),
            allowed_methods=frozenset({'GET', 'POST'}),
            raise_on_status=False,
        )
        session.mount('https://', HTTPAdapter(max_retries=retries))
        session.mount('http://', HTTPAdapter(max_retries=retries))
        session.headers.update({'Content-Type': 'application/json'})
        if self.api_key:
            session.headers.update({'api-key': self.api_key})
        return session

    def purchase_airtime(self, network: str, phone: str, amount: Decimal, reference: str) -> VTUResult:
        payload = {
            'request_id': reference,
            'serviceID': network,
            'amount': str(amount),
            'phone': phone,
        }
        return self._request('POST', '/api/pay', payload)

    def purchase_data(self, network: str, plan_code: str, phone: str, reference: str) -> VTUResult:
        payload = {
            'request_id': reference,
            'serviceID': network,
            'billersCode': phone,
            'variation_code': plan_code,
            'phone': phone,
        }
        return self._request('POST', '/api/pay', payload)

    def purchase_bill(self, biller_code: str, customer_id: str, amount: Decimal, reference: str) -> VTUResult:
        payload = {
            'request_id': reference,
            'serviceID': biller_code,
            'billersCode': customer_id,
            'amount': str(amount),
        }
        return self._request('POST', '/api/pay', payload)

    def verify(self, *, reference: str = '', provider_ref: str = '') -> VTUResult:
        payload = {'request_id': reference, 'transaction_id': provider_ref}
        return self._request('POST', '/api/requery', payload)

    def fetch_data_plans(self, service_id: str) -> list[dict[str, Any]]:
        result = self._request('POST', '/api/service-variations', {'serviceID': service_id})
        raw = result.raw or {}
        content = raw.get('content') or {}
        return content.get('variations') or []

    def _request(self, method: str, path: str, payload: dict[str, Any]) -> VTUResult:
        url = f'{self.base_url}{path}'
        safe_payload = {k: ('***' if k in {'api_key', 'password'} else v) for k, v in payload.items()}
        logger.info('VTpass request %s %s payload=%s', method, path, safe_payload)

        auth = (self.username, self.password) if self.username and self.password else None
        try:
            response = self.session.request(method, url, json=payload, timeout=self.timeout, auth=auth)
            response_data = response.json()
        except requests.RequestException as exc:
            logger.exception('VTpass request transport error path=%s', path)
            return VTUResult(success=False, status='FAILED', message=str(exc), raw={'error': str(exc)})
        except ValueError:
            logger.error('VTpass invalid JSON response path=%s status=%s', path, response.status_code)
            return VTUResult(success=False, status='FAILED', message='Invalid provider response', raw={})

        logger.info(
            'VTpass response %s status=%s code=%s',
            path,
            response.status_code,
            response_data.get('code') if isinstance(response_data, dict) else None,
        )
        return self._normalize(response_data)

    def _normalize(self, payload: dict[str, Any]) -> VTUResult:
        code = str(payload.get('code', '')).lower()
        response_desc = str(payload.get('response_description') or payload.get('message') or '').strip()
        content = payload.get('content') or {}
        transactions = content.get('transactions') or {}

        provider_ref = str(
            payload.get('requestId')
            or transactions.get('transactionId')
            or content.get('transactionId')
            or ''
        )

        state_hint = str(transactions.get('status') or content.get('status') or response_desc).lower()
        if code == '000' or any(token in state_hint for token in self.SUCCESS_STATES):
            status = 'SUCCESS'
            success = True
        elif any(token in state_hint for token in self.PENDING_STATES):
            status = 'PENDING'
            success = False
        else:
            status = 'FAILED'
            success = False

        return VTUResult(
            success=success,
            status=status,
            provider_ref=provider_ref,
            message=response_desc or 'Provider request processed',
            raw=payload,
        )
