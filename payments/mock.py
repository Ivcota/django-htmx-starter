import uuid
from datetime import timedelta

from django.utils import timezone
from djstripe.models import Customer, PaymentIntent, Plan, Price, Product, Subscription, SubscriptionItem


def mock_customer(user):
    """Create a fake dj-stripe Customer linked to the given user."""
    customer_id = f'cus_mock_{uuid.uuid4().hex[:14]}'
    return Customer.objects.create(
        id=customer_id,
        livemode=False,
        email=user.email or '',
        name=getattr(user, 'get_full_name', lambda: '')() or '',
        currency='usd',
        subscriber=user,
        stripe_data={},
    )


def mock_product(name='Mock Product', type='service'):
    """Create a fake dj-stripe Product."""
    product_id = f'prod_mock_{uuid.uuid4().hex[:14]}'
    return Product.objects.create(
        id=product_id,
        livemode=False,
        name=name,
        type=type,
        active=True,
        stripe_data={},
    )


def mock_price(product, unit_amount=1000, currency='usd', recurring=None):
    """Create a fake dj-stripe Price linked to a product."""
    price_id = f'price_mock_{uuid.uuid4().hex[:14]}'
    price_type = 'recurring' if recurring else 'one_time'
    return Price.objects.create(
        id=price_id,
        livemode=False,
        product=product,
        unit_amount=unit_amount,
        currency=currency,
        type=price_type,
        recurring=recurring,
        active=True,
        billing_scheme='per_unit',
        stripe_data={},
    )


def mock_subscription(customer, price):
    """Create a fake dj-stripe Subscription linked to customer and price."""
    sub_id = f'sub_mock_{uuid.uuid4().hex[:14]}'
    plan_id = f'plan_mock_{uuid.uuid4().hex[:14]}'
    si_id = f'si_mock_{uuid.uuid4().hex[:14]}'
    now = timezone.now()

    plan = Plan.objects.create(
        id=plan_id,
        livemode=False,
        active=True,
        currency=price.currency,
        interval=price.recurring.get('interval', 'month') if price.recurring else 'month',
        product=price.product,
        amount=price.unit_amount,
        stripe_data={},
    )

    subscription = Subscription.objects.create(
        id=sub_id,
        livemode=False,
        customer=customer,
        status='active',
        collection_method='charge_automatically',
        current_period_start=now,
        current_period_end=now + timedelta(days=30),
        plan=plan,
        stripe_data={},
    )

    SubscriptionItem.objects.create(
        id=si_id,
        livemode=False,
        subscription=subscription,
        plan=plan,
        price=price,
        quantity=1,
        stripe_data={},
    )

    return subscription


def mock_payment_intent(customer, amount, currency='usd'):
    """Create a fake dj-stripe PaymentIntent for the given customer."""
    pi_id = f'pi_mock_{uuid.uuid4().hex[:14]}'
    return PaymentIntent.objects.create(
        id=pi_id,
        livemode=False,
        customer=customer,
        amount=amount,
        amount_capturable=0,
        amount_received=amount,
        currency=currency,
        status='succeeded',
        capture_method='automatic',
        confirmation_method='automatic',
        client_secret=f'{pi_id}_secret_mock',
        payment_method_types=['card'],
        stripe_data={},
    )
