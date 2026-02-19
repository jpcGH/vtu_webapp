from __future__ import annotations

try:
    from celery import shared_task
except ImportError:  # pragma: no cover
    class _DummyRequest:
        retries = 0

    class _DummyTask:
        request = _DummyRequest()

        @staticmethod
        def retry(*args, **kwargs):
            return None

    def shared_task(*_args, **options):
        bind = options.get('bind', False)

        def decorator(fn):
            def delay(*args, **kwargs):
                if bind:
                    return fn(_DummyTask(), *args, **kwargs)
                return fn(*args, **kwargs)

            fn.delay = delay
            return fn

        return decorator

from apps.vtu.models import PurchaseOrder
from apps.vtu.services import verify_purchase


@shared_task(bind=True, max_retries=5, default_retry_delay=60)
def verify_pending_purchase(self, order_id: int):
    order = verify_purchase(order_id)
    if order.status == PurchaseOrder.Status.PENDING:
        raise self.retry(countdown=min(60 * (2 ** self.request.retries), 60 * 60))
    return order.status


@shared_task
def sweep_pending_purchases():
    for order_id in PurchaseOrder.objects.filter(status=PurchaseOrder.Status.PENDING).values_list('id', flat=True):
        verify_pending_purchase.delay(order_id)
