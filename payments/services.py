from django.conf import settings
from djstripe.models import Customer

from payments.mock import mock_customer, mock_payment_intent, mock_subscription


def get_customer(user):
    """Return the dj-stripe Customer for user, creating one if needed."""
    try:
        return Customer.objects.get(subscriber=user)
    except Customer.DoesNotExist:
        if settings.STRIPE_MOCK_MODE:
            return mock_customer(user)
        # Live mode: sync from Stripe
        customer, _created = Customer.get_or_create(subscriber=user)
        return customer


def charge_user(request, price_id):
    """Initiate a one-time payment. Returns a redirect URL."""
    from djstripe.models import Price

    price = Price.objects.get(id=price_id)
    customer = get_customer(request.user)

    if settings.STRIPE_MOCK_MODE:
        mock_payment_intent(customer, amount=price.unit_amount, currency=price.currency)
        return 'mock_success'

    # Live mode: create Stripe Checkout Session
    import stripe
    from django.urls import reverse

    session = stripe.checkout.Session.create(
        customer=customer.id,
        line_items=[{'price': price_id, 'quantity': 1}],
        mode='payment',
        success_url=request.build_absolute_uri(reverse('payments:success')),
        cancel_url=request.build_absolute_uri(reverse('payments:cancel')),
    )
    return session.url


def create_subscription(request, price_id):
    """Initiate a subscription. Returns a redirect URL."""
    from djstripe.models import Price

    price = Price.objects.get(id=price_id)
    customer = get_customer(request.user)

    if settings.STRIPE_MOCK_MODE:
        mock_subscription(customer, price)
        return 'mock_success'

    # Live mode: create Stripe Checkout Session in subscription mode
    import stripe
    from django.urls import reverse

    session = stripe.checkout.Session.create(
        customer=customer.id,
        line_items=[{'price': price_id, 'quantity': 1}],
        mode='subscription',
        success_url=request.build_absolute_uri(reverse('payments:success')),
        cancel_url=request.build_absolute_uri(reverse('payments:cancel')),
    )
    return session.url
