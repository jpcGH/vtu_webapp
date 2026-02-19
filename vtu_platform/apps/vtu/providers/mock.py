from __future__ import annotations

from decimal import Decimal

from apps.vtu.providers.base import BaseProvider, VTUResult


class MockProvider(BaseProvider):
    def _is_failure(self, value: str) -> bool:
        return value.strip().upper().startswith('FAIL')

    def _is_pending(self, value: str) -> bool:
        return value.strip().upper().startswith('PEND')

    def purchase_airtime(self, network: str, phone: str, amount: Decimal, reference: str) -> VTUResult:
        if self._is_failure(phone):
            return VTUResult(success=False, status='FAILED', message='Mock airtime purchase failed')
        if self._is_pending(phone):
            return VTUResult(success=False, status='PENDING', message='Mock airtime pending')
        return VTUResult(
            success=True,
            status='SUCCESS',
            message='Mock airtime purchase successful',
            provider_ref=f'MOCK-AIR-{reference[-8:]}',
            raw={'network': network, 'phone': phone, 'amount': str(amount)},
        )

    def purchase_data(self, network: str, plan_code: str, phone: str, reference: str) -> VTUResult:
        if self._is_failure(phone) or self._is_failure(plan_code):
            return VTUResult(success=False, status='FAILED', message='Mock data purchase failed')
        if self._is_pending(phone) or self._is_pending(plan_code):
            return VTUResult(success=False, status='PENDING', message='Mock data purchase pending')
        return VTUResult(
            success=True,
            status='SUCCESS',
            message='Mock data purchase successful',
            provider_ref=f'MOCK-DATA-{reference[-8:]}',
            raw={'network': network, 'phone': phone, 'plan_code': plan_code},
        )

    def purchase_bill(self, biller_code: str, customer_id: str, amount: Decimal, reference: str) -> VTUResult:
        if self._is_failure(customer_id) or self._is_failure(biller_code):
            return VTUResult(success=False, status='FAILED', message='Mock bill payment failed')
        if self._is_pending(customer_id) or self._is_pending(biller_code):
            return VTUResult(success=False, status='PENDING', message='Mock bill payment pending')
        return VTUResult(
            success=True,
            status='SUCCESS',
            message='Mock bill payment successful',
            provider_ref=f'MOCK-BILL-{reference[-8:]}',
            raw={'biller_code': biller_code, 'customer_id': customer_id, 'amount': str(amount)},
        )

    def verify(self, *, reference: str = '', provider_ref: str = '') -> VTUResult:
        if self._is_failure(reference) or self._is_failure(provider_ref):
            return VTUResult(success=False, status='FAILED', message='Mock verification failed')
        return VTUResult(
            success=True,
            status='SUCCESS',
            message='Mock verification successful',
            provider_ref=provider_ref or f'MOCK-VERIFY-{reference[-8:]}',
            raw={'reference': reference, 'provider_ref': provider_ref},
        )
