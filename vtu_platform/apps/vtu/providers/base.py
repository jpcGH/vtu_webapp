from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from decimal import Decimal
from typing import Any


@dataclass
class VTUResult:
    success: bool
    status: str
    message: str
    provider_ref: str = ''
    raw: dict[str, Any] | None = None


class BaseProvider(ABC):
    @abstractmethod
    def purchase_airtime(self, network: str, phone: str, amount: Decimal, reference: str) -> VTUResult:
        raise NotImplementedError

    @abstractmethod
    def purchase_data(self, network: str, plan_code: str, phone: str, reference: str) -> VTUResult:
        raise NotImplementedError

    @abstractmethod
    def purchase_bill(self, biller_code: str, customer_id: str, amount: Decimal, reference: str) -> VTUResult:
        raise NotImplementedError

    @abstractmethod
    def verify(self, *, reference: str = '', provider_ref: str = '') -> VTUResult:
        raise NotImplementedError
