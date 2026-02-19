from decimal import Decimal, InvalidOperation

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render

from apps.vtu.models import PurchaseOrder, ServiceProvider
from apps.vtu.services import create_purchase_order, process_purchase


@login_required
def buy_services(request):
    providers = ServiceProvider.objects.filter(is_active=True).order_by('name')

    if request.method == 'POST':
        product_type = request.POST.get('product_type', PurchaseOrder.ProductType.AIRTIME)
        destination = request.POST.get('destination', '').strip()
        service_code = request.POST.get('service_code', '').strip()
        provider_id = request.POST.get('provider')

        amount_raw = request.POST.get('amount', '0').strip()
        try:
            amount = Decimal(amount_raw)
        except (InvalidOperation, ValueError):
            messages.error(request, 'Enter a valid amount.')
            return redirect('vtu:buy_services')

        provider = get_object_or_404(ServiceProvider, pk=provider_id, is_active=True)

        order = create_purchase_order(
            user=request.user,
            provider=provider,
            product_type=product_type,
            amount=amount,
            destination=destination,
            service_code=service_code,
        )

        if order.status == PurchaseOrder.Status.PENDING:
            process_purchase(order.id)
        return redirect('vtu:transaction_status', reference=order.reference)

    return render(
        request,
        'vtu/buy_services.html',
        {
            'providers': providers,
            'product_types': PurchaseOrder.ProductType.choices,
        },
    )


@login_required
def transaction_status(request, reference):
    order = get_object_or_404(PurchaseOrder, reference=reference, user=request.user)
    return render(request, 'vtu/transaction_status.html', {'order': order})


@login_required
def receipt(request, reference):
    order = get_object_or_404(PurchaseOrder, reference=reference, user=request.user)
    return render(request, 'vtu/receipt.html', {'order': order})
