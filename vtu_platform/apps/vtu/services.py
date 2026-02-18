from dataclasses import dataclass
from decimal import Decimal


@dataclass
class VTUResult:
    success: bool
    message: str
    provider_reference: str = ''


class BaseProvider:
    def purchase(self, product_type: str, amount: Decimal, destination: str) -> VTUResult:
        raise NotImplementedError


class StubProvider(BaseProvider):
    def purchase(self, product_type: str, amount: Decimal, destination: str) -> VTUResult:
        reference = f'STUB-{product_type.upper()}-{destination[-4:]}'
        return VTUResult(success=True, message='Simulated successful transaction', provider_reference=reference)
