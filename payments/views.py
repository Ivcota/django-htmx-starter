from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from django.urls import reverse
from django.views.decorators.http import require_POST

from payments.services import charge_user, create_subscription


def pricing(request):
    from djstripe.models import Product

    products = Product.objects.filter(active=True).prefetch_related('prices')

    # Build display-ready product data for the template
    product_list = []
    for product in products:
        prices = []
        for price in product.prices.filter(active=True).order_by('unit_amount'):
            amount = price.unit_amount or 0
            dollars = amount // 100
            cents = amount % 100
            display = f'${dollars}' if cents == 0 else f'${dollars}.{cents:02d}'
            prices.append({
                'id': price.id,
                'display': display,
                'recurring': price.recurring,
                'checkout_url': reverse('payments:checkout', kwargs={'price_id': price.id}),
            })
        product_list.append({
            'name': product.name,
            'description': product.description,
            'prices': prices,
        })

    return render(request, 'payments/pricing.html', {
        'products': product_list,
    })


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
