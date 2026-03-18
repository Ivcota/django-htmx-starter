from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from django.urls import reverse
from django.views.decorators.http import require_POST

from payments.services import charge_user, create_subscription


@login_required
@require_POST
def checkout(request, price_id):
    from djstripe.models import Price

    price = Price.objects.get(id=price_id)
    if price.type == 'recurring':
        result = create_subscription(request, price_id)
    else:
        result = charge_user(request, price_id)

    if result == 'mock_success':
        return redirect(reverse('payments:success'))
    # Live mode: result is a Stripe Checkout URL
    return redirect(result)


@login_required
def success(request):
    return render(request, 'payments/success.html')


@login_required
def cancel(request):
    return render(request, 'payments/cancel.html')
