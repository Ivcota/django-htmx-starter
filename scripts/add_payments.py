"""Scaffold script that adds a complete Stripe payments system to the django-htmx-starter."""

import os


def inject_installed_apps(settings_path):
    """Insert 'djstripe' and 'payments' into INSTALLED_APPS before 'core'."""
    with open(settings_path) as f:
        content = f.read()

    for app in ('djstripe', 'payments'):
        if f"'{app}'" in content:
            continue
        content = content.replace(
            "    'core',",
            f"    '{app}',\n    'core',",
        )

    with open(settings_path, 'w') as f:
        f.write(content)


STRIPE_SETTINGS_BLOCK = """
# --- Stripe / Payments ---
STRIPE_LIVE_SECRET_KEY = os.environ.get('STRIPE_LIVE_SECRET_KEY', '')
STRIPE_TEST_SECRET_KEY = os.environ.get('STRIPE_TEST_SECRET_KEY', '')
DJSTRIPE_WEBHOOK_SECRET = os.environ.get('DJSTRIPE_WEBHOOK_SECRET', '')
STRIPE_MOCK_MODE = os.environ.get('STRIPE_MOCK_MODE', 'true').lower() in ('true', '1', 'yes')
DJSTRIPE_SUBSCRIBER_MODEL = 'core.User'
DJSTRIPE_FOREIGN_KEY_TO_FIELD = 'id'
"""


def append_stripe_settings(settings_path):
    """Append the Stripe config block to settings.py."""
    with open(settings_path) as f:
        content = f.read()

    if '# --- Stripe / Payments ---' in content:
        return

    with open(settings_path, 'a') as f:
        f.write(STRIPE_SETTINGS_BLOCK)


PAYMENTS_URL_LINES = """\
    path('payments/', include('payments.urls')),
    path('stripe/', include('djstripe.urls', namespace='djstripe')),
"""


def wire_urls(urls_path):
    """Add payments and djstripe URL includes to urls.py."""
    with open(urls_path) as f:
        content = f.read()

    if "payments.urls" in content:
        return

    content = content.replace(
        "    path('admin/', admin.site.urls),",
        PAYMENTS_URL_LINES + "    path('admin/', admin.site.urls),",
    )

    with open(urls_path, 'w') as f:
        f.write(content)


ENV_STRIPE_BLOCK = """
# --- Stripe / Payments ---
# Set to 'false' to use real Stripe API (requires keys below)
STRIPE_MOCK_MODE=true
# Get keys from https://dashboard.stripe.com/apikeys
STRIPE_LIVE_SECRET_KEY=
STRIPE_TEST_SECRET_KEY=
# Get from https://dashboard.stripe.com/webhooks
DJSTRIPE_WEBHOOK_SECRET=
"""


def update_env_example(env_path):
    """Append Stripe env vars to .env.example."""
    with open(env_path) as f:
        content = f.read()

    if 'STRIPE_MOCK_MODE' in content:
        return

    with open(env_path, 'a') as f:
        f.write(ENV_STRIPE_BLOCK)


SEED_PAYMENTS_RECIPE = """
# Seed example Products and Prices for development
[group: 'database']
seed-payments:
    {{manage}} seed_payments
"""


def add_justfile_recipe(justfile_path):
    """Add seed-payments recipe to justfile."""
    with open(justfile_path) as f:
        content = f.read()

    if 'seed-payments' in content:
        return

    with open(justfile_path, 'a') as f:
        f.write(SEED_PAYMENTS_RECIPE)


# ---------------------------------------------------------------------------
# File contents for the payments app
# ---------------------------------------------------------------------------

PAYMENTS_FILES = {
    'payments/__init__.py': '',

    'payments/apps.py': '''\
from django.apps import AppConfig


class PaymentsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'payments'

    def ready(self):
        import payments.signals  # noqa: F401
''',

    'payments/urls.py': '''\
from django.urls import path

from payments import views

app_name = 'payments'

urlpatterns = [
    path('pricing/', views.pricing, name='pricing'),
    path('checkout/<str:price_id>/', views.checkout, name='checkout'),
    path('success/', views.success, name='success'),
    path('cancel/', views.cancel, name='cancel'),
    path('portal/', views.billing_portal, name='portal'),
]
''',

    'payments/mock.py': '''\
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
''',

    'payments/services.py': '''\
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
''',

    'payments/views.py': '''\
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from django.urls import reverse
from django.views.decorators.http import require_POST

from payments.services import charge_user, create_subscription, get_customer


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


@login_required
def billing_portal(request):
    """Redirect to Stripe Billing Portal, or dashboard in mock mode."""
    if settings.STRIPE_MOCK_MODE:
        messages.info(request, 'Billing portal is not available in mock mode.')
        return redirect(reverse('dashboard'))

    # Live mode: create a Stripe Billing Portal session
    import stripe

    customer = get_customer(request.user)
    session = stripe.billing_portal.Session.create(
        customer=customer.id,
        return_url=request.build_absolute_uri(reverse('dashboard')),
    )
    return redirect(session.url)
''',

    'payments/decorators.py': '''\
import functools

from django.shortcuts import redirect
from djstripe.models import Subscription


def requires_subscription(view=None, price_id=None):
    """Require an active subscription to access the view.

    Usage:
        @requires_subscription
        def my_view(request): ...

        @requires_subscription(price_id='price_xxx')
        def my_view(request): ...
    """
    def decorator(view_func):
        @functools.wraps(view_func)
        def wrapper(request, *args, **kwargs):
            filters = {
                'customer__subscriber': request.user,
                'status': 'active',
            }
            if price_id:
                filters['items__price__id'] = price_id

            if Subscription.objects.filter(**filters).exists():
                return view_func(request, *args, **kwargs)

            return redirect('/payments/pricing/')

        return wrapper

    if view is not None:
        # Called as @requires_subscription without parens
        return decorator(view)

    # Called as @requires_subscription(...) with args
    return decorator
''',

    'payments/signals.py': '''\
import logging

from djstripe.event_handlers import djstripe_receiver

logger = logging.getLogger(__name__)


@djstripe_receiver("payment_intent.succeeded")
def handle_payment_succeeded(sender, event, **kwargs):
    """Handle successful payment events.

    This fires when a PaymentIntent completes successfully. Add your custom
    logic here, for example:
    - Send a confirmation email
    - Provision access to a purchased product
    - Update internal order records
    """
    obj = event.data.get("object", {})
    logger.info("Payment succeeded: %s (amount: %s)", obj.get("id"), obj.get("amount"))


@djstripe_receiver([
    "customer.subscription.created",
    "customer.subscription.updated",
    "customer.subscription.deleted",
])
def handle_subscription_changed(sender, event, **kwargs):
    """Handle subscription lifecycle events.

    This fires when a subscription is created, updated, or canceled. Add your
    custom logic here, for example:
    - Upgrade/downgrade user permissions based on new plan
    - Send notification emails for subscription changes
    - Log subscription status transitions for analytics
    """
    obj = event.data.get("object", {})
    logger.info("Subscription changed: %s (status: %s)", obj.get("id"), obj.get("status"))
''',

    'payments/admin.py': '''\
from django.contrib import admin
from djstripe.models import Customer, PaymentIntent, Price, Product, Subscription


# Unregister dj-stripe's default admin registrations so we can customize them
for model in [Customer, Product, Price, Subscription, PaymentIntent]:
    if admin.site.is_registered(model):
        admin.site.unregister(model)


@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display = ('id', 'subscriber', 'email', 'created')
    search_fields = ('id', 'email', 'subscriber__email', 'subscriber__username')
    list_filter = ('created',)


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'active', 'type')
    search_fields = ('id', 'name')
    list_filter = ('active', 'type')


@admin.register(Price)
class PriceAdmin(admin.ModelAdmin):
    list_display = ('id', 'product', 'unit_amount', 'currency', 'recurring', 'active')
    search_fields = ('id', 'product__name')
    list_filter = ('active', 'currency', 'type')


@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
    list_display = ('id', 'customer', 'status', 'current_period_start', 'current_period_end')
    search_fields = ('id', 'customer__email', 'customer__subscriber__email')
    list_filter = ('status',)


@admin.register(PaymentIntent)
class PaymentIntentAdmin(admin.ModelAdmin):
    list_display = ('id', 'customer', 'amount', 'currency', 'status')
    search_fields = ('id', 'customer__email')
    list_filter = ('status', 'currency')
''',

    'payments/management/__init__.py': '',
    'payments/management/commands/__init__.py': '',

    'payments/management/commands/seed_payments.py': '''\
from django.core.management.base import BaseCommand

from payments.mock import mock_price, mock_product


SEED_DATA = [
    {
        'name': 'Pro Plan',
        'type': 'service',
        'prices': [
            {'unit_amount': 1000, 'recurring': {'interval': 'month'}},
            {'unit_amount': 10000, 'recurring': {'interval': 'year'}},
        ],
    },
    {
        'name': 'Lifetime Access',
        'type': 'service',
        'prices': [
            {'unit_amount': 19900},
        ],
    },
]


class Command(BaseCommand):
    help = 'Seed example Products and Prices for development'

    def handle(self, *args, **options):
        from djstripe.models import Product

        for item in SEED_DATA:
            if Product.objects.filter(name=item['name']).exists():
                self.stdout.write(f"  Skipping '{item['name']}' (already exists)")
                continue

            product = mock_product(name=item['name'], type=item['type'])
            self.stdout.write(f"  Created product: {item['name']}")

            for price_data in item['prices']:
                mock_price(product, **price_data)
                amount = price_data['unit_amount'] / 100
                interval = price_data.get('recurring', {}).get('interval', 'one-time')
                self.stdout.write(f"    Created price: ${amount:.0f}/{interval}")

        self.stdout.write(self.style.SUCCESS('Seed complete.'))
''',

    'payments/tests.py': '''\
from unittest.mock import MagicMock, patch

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import resolve, reverse

User = get_user_model()


class MockModeSettingTests(TestCase):
    def test_mock_mode_defaults_to_true(self):
        """STRIPE_MOCK_MODE should default to True when env var is unset."""
        self.assertTrue(settings.STRIPE_MOCK_MODE)

    def test_mock_mode_setting_is_boolean(self):
        """STRIPE_MOCK_MODE should be a boolean, not a string."""
        self.assertIsInstance(settings.STRIPE_MOCK_MODE, bool)


class URLRoutingTests(TestCase):
    def test_webhook_url_resolves(self):
        """The dj-stripe webhook URL should be registered at /stripe/webhook/<uuid>/."""
        import uuid
        # Any valid UUID should resolve — the view handles 404 for unknown endpoints
        test_uuid = uuid.uuid4()
        url = f'/stripe/webhook/{test_uuid}/'
        match = resolve(url)
        self.assertEqual(match.url_name, 'djstripe_webhook_by_uuid')


class MockCustomerTests(TestCase):
    def test_mock_customer_creates_djstripe_customer(self):
        """mock_customer should create a dj-stripe Customer linked to the user."""
        from djstripe.models import Customer
        from payments.mock import mock_customer

        user = User.objects.create_user(username='test', email='test@example.com', password='testpass')
        customer = mock_customer(user)

        self.assertIsInstance(customer, Customer)
        self.assertEqual(customer.subscriber, user)
        self.assertTrue(customer.id.startswith('cus_mock_'))

    def test_mock_customer_is_retrievable(self):
        """mock_customer should persist a real DB record."""
        from djstripe.models import Customer
        from payments.mock import mock_customer

        user = User.objects.create_user(username='test2', email='test2@example.com', password='testpass')
        customer = mock_customer(user)

        retrieved = Customer.objects.get(id=customer.id)
        self.assertEqual(retrieved.subscriber, user)


class MockProductTests(TestCase):
    def test_mock_product_creates_djstripe_product(self):
        """mock_product should create a dj-stripe Product record."""
        from djstripe.models import Product
        from payments.mock import mock_product

        product = mock_product(name='Test Product')

        self.assertIsInstance(product, Product)
        self.assertEqual(product.name, 'Test Product')
        self.assertTrue(product.id.startswith('prod_mock_'))
        self.assertTrue(product.active)

    def test_mock_product_uses_defaults(self):
        """mock_product should use sensible defaults when no args given."""
        from payments.mock import mock_product

        product = mock_product()
        self.assertEqual(product.name, 'Mock Product')
        self.assertEqual(product.type, 'service')


class MockPriceTests(TestCase):
    def test_mock_price_creates_djstripe_price(self):
        """mock_price should create a dj-stripe Price linked to a product."""
        from djstripe.models import Price
        from payments.mock import mock_price, mock_product

        product = mock_product()
        price = mock_price(product, unit_amount=1000)

        self.assertIsInstance(price, Price)
        self.assertEqual(price.product, product)
        self.assertEqual(price.unit_amount, 1000)
        self.assertEqual(price.currency, 'usd')
        self.assertTrue(price.id.startswith('price_mock_'))

    def test_mock_price_recurring(self):
        """mock_price with recurring interval creates a recurring price."""
        from payments.mock import mock_price, mock_product

        product = mock_product()
        price = mock_price(product, unit_amount=1000, recurring={'interval': 'month'})

        self.assertEqual(price.recurring['interval'], 'month')
        self.assertEqual(price.type, 'recurring')

    def test_mock_price_one_time(self):
        """mock_price without recurring creates a one-time price."""
        from payments.mock import mock_price, mock_product

        product = mock_product()
        price = mock_price(product, unit_amount=19900)

        self.assertIsNone(price.recurring)
        self.assertEqual(price.type, 'one_time')


class MockPaymentIntentTests(TestCase):
    def test_mock_payment_intent_creates_djstripe_record(self):
        """mock_payment_intent should create a dj-stripe PaymentIntent."""
        from djstripe.models import PaymentIntent
        from payments.mock import mock_customer, mock_payment_intent

        user = User.objects.create_user(username='pi_test', email='pi@example.com', password='testpass')
        customer = mock_customer(user)
        pi = mock_payment_intent(customer, amount=2500)

        self.assertIsInstance(pi, PaymentIntent)
        self.assertEqual(pi.customer, customer)
        self.assertEqual(pi.amount, 2500)
        self.assertEqual(pi.currency, 'usd')
        self.assertEqual(pi.status, 'succeeded')
        self.assertTrue(pi.id.startswith('pi_mock_'))


class MockCheckoutFlowTests(TestCase):
    """End-to-end tracer bullet: authenticated user completes mock checkout."""

    def setUp(self):
        from payments.mock import mock_product, mock_price

        self.user = User.objects.create_user(
            username='buyer', email='buyer@example.com', password='testpass'
        )
        self.product = mock_product(name='Test Widget')
        self.price = mock_price(self.product, unit_amount=2500)

    def test_mock_checkout_creates_payment_and_redirects_to_success(self):
        """Full mock checkout: POST to checkout → PaymentIntent created → redirect to success."""
        from djstripe.models import PaymentIntent

        self.client.login(username='buyer', password='testpass')
        response = self.client.post(
            reverse('payments:checkout', kwargs={'price_id': self.price.id})
        )

        self.assertRedirects(response, reverse('payments:success'), fetch_redirect_response=False)
        self.assertTrue(PaymentIntent.objects.filter(customer__subscriber=self.user).exists())


class GetCustomerTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='custtest', email='cust@example.com', password='testpass'
        )

    def test_creates_customer_when_none_exists(self):
        """get_customer should create a new dj-stripe Customer for a user with no Customer."""
        from djstripe.models import Customer

        from payments.services import get_customer

        customer = get_customer(self.user)

        self.assertIsInstance(customer, Customer)
        self.assertEqual(customer.subscriber, self.user)

    def test_returns_existing_customer(self):
        """get_customer should return the same Customer on second call."""
        from payments.services import get_customer

        first = get_customer(self.user)
        second = get_customer(self.user)

        self.assertEqual(first.id, second.id)


class ChargeUserTests(TestCase):
    def setUp(self):
        from payments.mock import mock_price, mock_product

        self.user = User.objects.create_user(
            username='chargetest', email='charge@example.com', password='testpass'
        )
        product = mock_product(name='Charge Product')
        self.price = mock_price(product, unit_amount=5000)

    def test_mock_mode_creates_payment_intent_and_returns_mock_success(self):
        """charge_user in mock mode should create a PaymentIntent and return 'mock_success'."""
        from django.test import RequestFactory
        from djstripe.models import PaymentIntent

        from payments.services import charge_user

        request = RequestFactory().post('/payments/checkout/fake/')
        request.user = self.user

        result = charge_user(request, self.price.id)

        self.assertEqual(result, 'mock_success')
        pi = PaymentIntent.objects.get(customer__subscriber=self.user)
        self.assertEqual(pi.amount, 5000)
        self.assertEqual(pi.status, 'succeeded')


class CheckoutViewTests(TestCase):
    def setUp(self):
        from payments.mock import mock_price, mock_product

        self.user = User.objects.create_user(
            username='viewtest', email='view@example.com', password='testpass'
        )
        product = mock_product(name='View Product')
        self.price = mock_price(product, unit_amount=1500)

    def test_unauthenticated_user_redirected_to_login(self):
        """Checkout should redirect unauthenticated users to the login page."""
        url = reverse('payments:checkout', kwargs={'price_id': self.price.id})
        response = self.client.post(url)

        self.assertEqual(response.status_code, 302)
        self.assertIn('/accounts/login/', response.url)

    def test_success_page_renders(self):
        """Success page should render 200 with confirmation message."""
        self.client.login(username='viewtest', password='testpass')
        response = self.client.get(reverse('payments:success'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Thank you for your purchase')

    def test_cancel_page_renders(self):
        """Cancel page should render 200 with retry messaging."""
        self.client.login(username='viewtest', password='testpass')
        response = self.client.get(reverse('payments:cancel'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'try again')


class LiveModeChargeTests(TestCase):
    def setUp(self):
        from payments.mock import mock_customer, mock_price, mock_product

        self.user = User.objects.create_user(
            username='livetest', email='live@example.com', password='testpass'
        )
        # Pre-create customer so get_customer finds it without hitting Stripe
        self.customer = mock_customer(self.user)
        product = mock_product(name='Live Product')
        self.price = mock_price(product, unit_amount=3000)

    @override_settings(STRIPE_MOCK_MODE=False)
    @patch('stripe.checkout.Session.create')
    def test_live_mode_returns_stripe_checkout_url(self, mock_session_create):
        """charge_user in live mode should create a Stripe Checkout Session and return its URL."""
        from django.test import RequestFactory

        from payments.services import charge_user

        mock_session_create.return_value = MagicMock(url='https://checkout.stripe.com/test_session')

        request = RequestFactory().post('/payments/checkout/fake/')
        request.user = self.user

        result = charge_user(request, self.price.id)

        self.assertEqual(result, 'https://checkout.stripe.com/test_session')
        mock_session_create.assert_called_once()


class MockSubscriptionTests(TestCase):
    def test_mock_subscription_creates_active_subscription(self):
        """mock_subscription should create a dj-stripe Subscription with status='active'."""
        from djstripe.models import Subscription

        from payments.mock import mock_customer, mock_price, mock_product, mock_subscription

        user = User.objects.create_user(username='subtest', email='sub@example.com', password='testpass')
        customer = mock_customer(user)
        product = mock_product(name='Sub Product')
        price = mock_price(product, unit_amount=1000, recurring={'interval': 'month'})

        subscription = mock_subscription(customer, price)

        self.assertIsInstance(subscription, Subscription)
        self.assertEqual(subscription.customer, customer)
        self.assertEqual(subscription.status, 'active')
        self.assertTrue(subscription.id.startswith('sub_mock_'))
        self.assertIsNotNone(subscription.current_period_start)
        self.assertIsNotNone(subscription.current_period_end)

    def test_mock_subscription_has_item_linked_to_price(self):
        """mock_subscription should create a SubscriptionItem linking to the price."""
        from payments.mock import mock_customer, mock_price, mock_product, mock_subscription

        user = User.objects.create_user(username='subitem', email='subitem@example.com', password='testpass')
        customer = mock_customer(user)
        product = mock_product()
        price = mock_price(product, unit_amount=1000, recurring={'interval': 'month'})

        subscription = mock_subscription(customer, price)

        self.assertTrue(subscription.items.filter(price=price).exists())


class CreateSubscriptionTests(TestCase):
    def setUp(self):
        from payments.mock import mock_price, mock_product

        self.user = User.objects.create_user(
            username='createsubtest', email='createsub@example.com', password='testpass'
        )
        product = mock_product(name='Sub Product')
        self.price = mock_price(product, unit_amount=1000, recurring={'interval': 'month'})

    def test_mock_mode_creates_subscription_and_returns_mock_success(self):
        """create_subscription in mock mode should create a Subscription and return 'mock_success'."""
        from django.test import RequestFactory
        from djstripe.models import Subscription

        from payments.services import create_subscription

        request = RequestFactory().post('/payments/checkout/fake/')
        request.user = self.user

        result = create_subscription(request, self.price.id)

        self.assertEqual(result, 'mock_success')
        sub = Subscription.objects.get(customer__subscriber=self.user)
        self.assertEqual(sub.status, 'active')


class LiveModeSubscriptionTests(TestCase):
    def setUp(self):
        from payments.mock import mock_customer, mock_price, mock_product

        self.user = User.objects.create_user(
            username='livesub', email='livesub@example.com', password='testpass'
        )
        self.customer = mock_customer(self.user)
        product = mock_product(name='Live Sub Product')
        self.price = mock_price(product, unit_amount=1000, recurring={'interval': 'month'})

    @override_settings(STRIPE_MOCK_MODE=False)
    @patch('stripe.checkout.Session.create')
    def test_live_mode_creates_subscription_checkout_session(self, mock_session_create):
        """create_subscription in live mode should create a Stripe Checkout Session with mode='subscription'."""
        from django.test import RequestFactory

        from payments.services import create_subscription

        mock_session_create.return_value = MagicMock(url='https://checkout.stripe.com/sub_session')

        request = RequestFactory().post('/payments/checkout/fake/')
        request.user = self.user

        result = create_subscription(request, self.price.id)

        self.assertEqual(result, 'https://checkout.stripe.com/sub_session')
        mock_session_create.assert_called_once()
        call_kwargs = mock_session_create.call_args[1]
        self.assertEqual(call_kwargs['mode'], 'subscription')


class CheckoutAutoDetectTests(TestCase):
    def setUp(self):
        from payments.mock import mock_price, mock_product

        self.user = User.objects.create_user(
            username='autodetect', email='autodetect@example.com', password='testpass'
        )
        product = mock_product(name='Auto Product')
        self.recurring_price = mock_price(product, unit_amount=1000, recurring={'interval': 'month'})
        self.onetime_price = mock_price(product, unit_amount=19900)

    def test_recurring_price_creates_subscription(self):
        """Checkout with a recurring price should create a Subscription, not a PaymentIntent."""
        from djstripe.models import PaymentIntent, Subscription

        self.client.login(username='autodetect', password='testpass')
        response = self.client.post(
            reverse('payments:checkout', kwargs={'price_id': self.recurring_price.id})
        )

        self.assertRedirects(response, reverse('payments:success'), fetch_redirect_response=False)
        self.assertTrue(Subscription.objects.filter(customer__subscriber=self.user).exists())
        self.assertFalse(PaymentIntent.objects.filter(customer__subscriber=self.user).exists())

    def test_onetime_price_creates_payment_intent(self):
        """Checkout with a one-time price should create a PaymentIntent, not a Subscription."""
        from djstripe.models import PaymentIntent, Subscription

        self.client.login(username='autodetect', password='testpass')
        response = self.client.post(
            reverse('payments:checkout', kwargs={'price_id': self.onetime_price.id})
        )

        self.assertRedirects(response, reverse('payments:success'), fetch_redirect_response=False)
        self.assertTrue(PaymentIntent.objects.filter(customer__subscriber=self.user).exists())
        self.assertFalse(Subscription.objects.filter(customer__subscriber=self.user).exists())


class RequiresSubscriptionTests(TestCase):
    def setUp(self):
        from payments.mock import mock_customer, mock_price, mock_product

        self.user = User.objects.create_user(
            username='decotest', email='deco@example.com', password='testpass'
        )
        self.customer = mock_customer(self.user)
        self.product = mock_product(name='Deco Product')
        self.price = mock_price(self.product, unit_amount=1000, recurring={'interval': 'month'})

    def test_allows_access_with_active_subscription(self):
        """@requires_subscription should allow access for users with active subscriptions."""
        from django.test import RequestFactory

        from payments.decorators import requires_subscription
        from payments.mock import mock_subscription

        mock_subscription(self.customer, self.price)

        @requires_subscription
        def protected_view(request):
            from django.http import HttpResponse
            return HttpResponse('OK')

        request = RequestFactory().get('/protected/')
        request.user = self.user

        response = protected_view(request)
        self.assertEqual(response.status_code, 200)

    def test_redirects_without_subscription(self):
        """@requires_subscription should redirect users without subscriptions."""
        from django.test import RequestFactory

        from payments.decorators import requires_subscription

        @requires_subscription
        def protected_view(request):
            from django.http import HttpResponse
            return HttpResponse('OK')

        request = RequestFactory().get('/protected/')
        request.user = self.user

        response = protected_view(request)
        self.assertEqual(response.status_code, 302)
        self.assertIn('/payments/pricing/', response.url)


class RequiresSubscriptionPriceIdTests(TestCase):
    def setUp(self):
        from payments.mock import mock_customer, mock_price, mock_product, mock_subscription

        self.user = User.objects.create_user(
            username='pricegate', email='pricegate@example.com', password='testpass'
        )
        self.customer = mock_customer(self.user)
        product = mock_product(name='Gate Product')
        self.price_a = mock_price(product, unit_amount=1000, recurring={'interval': 'month'})
        self.price_b = mock_price(product, unit_amount=2000, recurring={'interval': 'month'})
        # User is subscribed to price_a only
        mock_subscription(self.customer, self.price_a)

    def test_allows_with_matching_price_id(self):
        """@requires_subscription(price_id=X) should allow when subscribed to X."""
        from django.test import RequestFactory

        from payments.decorators import requires_subscription

        @requires_subscription(price_id=self.price_a.id)
        def protected_view(request):
            from django.http import HttpResponse
            return HttpResponse('OK')

        request = RequestFactory().get('/protected/')
        request.user = self.user

        response = protected_view(request)
        self.assertEqual(response.status_code, 200)

    def test_denies_with_non_matching_price_id(self):
        """@requires_subscription(price_id=X) should deny when subscribed to different price."""
        from django.test import RequestFactory

        from payments.decorators import requires_subscription

        @requires_subscription(price_id=self.price_b.id)
        def protected_view(request):
            from django.http import HttpResponse
            return HttpResponse('OK')

        request = RequestFactory().get('/protected/')
        request.user = self.user

        response = protected_view(request)
        self.assertEqual(response.status_code, 302)


class PricingPageTests(TestCase):
    def test_pricing_page_renders(self):
        """GET /payments/pricing/ should return 200."""
        response = self.client.get(reverse('payments:pricing'))
        self.assertEqual(response.status_code, 200)

    def test_empty_state_when_no_products(self):
        """Pricing page should show seed message when no products exist."""
        response = self.client.get(reverse('payments:pricing'))
        self.assertContains(response, 'seed_payments')

    def test_displays_seeded_products(self):
        """Pricing page should display product names from seeded data."""
        from django.core.management import call_command

        call_command('seed_payments')
        response = self.client.get(reverse('payments:pricing'))

        self.assertContains(response, 'Pro Plan')
        self.assertContains(response, 'Lifetime Access')

    def test_displays_formatted_prices(self):
        """Pricing page should show formatted prices like $10/month, $100/year, $199."""
        from django.core.management import call_command

        call_command('seed_payments')
        response = self.client.get(reverse('payments:pricing'))

        self.assertContains(response, '$10')
        self.assertContains(response, '/month')
        self.assertContains(response, '$100')
        self.assertContains(response, '/year')
        self.assertContains(response, '$199')

    def test_checkout_links(self):
        """Pricing page buttons should link to checkout URLs for each price."""
        from django.core.management import call_command
        from djstripe.models import Price

        call_command('seed_payments')
        response = self.client.get(reverse('payments:pricing'))

        for price in Price.objects.all():
            checkout_url = reverse('payments:checkout', kwargs={'price_id': price.id})
            self.assertContains(response, checkout_url)


class SeedPaymentsTests(TestCase):
    def test_creates_products_and_prices(self):
        """seed_payments should create Products and Prices in the database."""
        from django.core.management import call_command
        from djstripe.models import Price, Product

        call_command('seed_payments')

        self.assertEqual(Product.objects.count(), 2)
        self.assertEqual(Price.objects.count(), 3)

    def test_expected_seed_data(self):
        """Seed data should match spec: Pro Plan ($10/mo, $100/yr) + Lifetime Access ($199)."""
        from django.core.management import call_command
        from djstripe.models import Price, Product

        call_command('seed_payments')

        pro = Product.objects.get(name='Pro Plan')
        pro_prices = Price.objects.filter(product=pro).order_by('unit_amount')
        self.assertEqual(pro_prices.count(), 2)
        self.assertEqual(pro_prices[0].unit_amount, 1000)
        self.assertEqual(pro_prices[0].recurring['interval'], 'month')
        self.assertEqual(pro_prices[1].unit_amount, 10000)
        self.assertEqual(pro_prices[1].recurring['interval'], 'year')

        lifetime = Product.objects.get(name='Lifetime Access')
        lifetime_price = Price.objects.get(product=lifetime)
        self.assertEqual(lifetime_price.unit_amount, 19900)
        self.assertIsNone(lifetime_price.recurring)

    def test_idempotent_no_duplicates(self):
        """Running seed_payments twice should not create duplicate records."""
        from django.core.management import call_command
        from djstripe.models import Price, Product

        call_command('seed_payments')
        call_command('seed_payments')

        self.assertEqual(Product.objects.count(), 2)
        self.assertEqual(Price.objects.count(), 3)


class BillingPortalMockModeTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='portal', email='portal@test.com', password='testpass')
        self.client.login(username='portal', password='testpass')

    @override_settings(STRIPE_MOCK_MODE=True)
    def test_portal_mock_mode_redirects_to_dashboard(self):
        """In mock mode, billing portal should redirect to dashboard."""
        response = self.client.get(reverse('payments:portal'))
        self.assertRedirects(response, '/dashboard/', fetch_redirect_response=False)

    @override_settings(STRIPE_MOCK_MODE=True)
    def test_portal_mock_mode_sets_toast_message(self):
        """In mock mode, billing portal should add an info message."""
        response = self.client.get(reverse('payments:portal'))
        msgs = list(messages.get_messages(response.wsgi_request))
        self.assertEqual(len(msgs), 1)
        self.assertIn('mock mode', str(msgs[0]).lower())


class BillingPortalLiveModeTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='portal_live', email='portal_live@test.com', password='testpass')
        self.client.login(username='portal_live', password='testpass')

    @override_settings(STRIPE_MOCK_MODE=False)
    @patch('payments.views.get_customer')
    @patch('stripe.billing_portal.Session.create')
    def test_portal_live_mode_redirects_to_stripe(self, mock_session_create, mock_get_customer):
        """In live mode, billing portal should redirect to the Stripe billing portal URL."""
        mock_customer = MagicMock()
        mock_customer.id = 'cus_live_123'
        mock_get_customer.return_value = mock_customer
        mock_session_create.return_value = MagicMock(url='https://billing.stripe.com/session/test')

        response = self.client.get(reverse('payments:portal'))

        mock_session_create.assert_called_once_with(
            customer='cus_live_123',
            return_url=response.wsgi_request.build_absolute_uri(reverse('dashboard')),
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, 'https://billing.stripe.com/session/test')


class BillingPortalAuthTests(TestCase):
    def test_portal_requires_login(self):
        """Unauthenticated users should be redirected to login."""
        response = self.client.get(reverse('payments:portal'))
        self.assertEqual(response.status_code, 302)
        self.assertIn('/accounts/login/', response.url)


class SignalHandlerTests(TestCase):
    def test_payment_succeeded_handler_connected(self):
        """payment_succeeded handler should be connected to payment_intent.succeeded signal."""
        from djstripe.signals import WEBHOOK_SIGNALS

        from payments.signals import handle_payment_succeeded

        signal = WEBHOOK_SIGNALS['payment_intent.succeeded']
        receivers = [r[1]() for r in signal.receivers]
        self.assertIn(handle_payment_succeeded, receivers)

    def test_subscription_changed_handler_connected(self):
        """subscription_changed handler should be connected to customer.subscription.* signals."""
        from djstripe.signals import WEBHOOK_SIGNALS

        from payments.signals import handle_subscription_changed

        for event_name in [
            'customer.subscription.created',
            'customer.subscription.updated',
            'customer.subscription.deleted',
        ]:
            signal = WEBHOOK_SIGNALS[event_name]
            receivers = [r[1]() for r in signal.receivers]
            self.assertIn(handle_subscription_changed, receivers, f'Not connected to {event_name}')

    def test_payment_succeeded_handler_callable(self):
        """payment_succeeded handler should execute without error."""
        from payments.signals import handle_payment_succeeded

        event = MagicMock()
        event.data = {'object': {'id': 'pi_test_123', 'amount': 1000}}
        handle_payment_succeeded(sender=None, event=event)

    def test_subscription_changed_handler_callable(self):
        """subscription_changed handler should execute without error."""
        from payments.signals import handle_subscription_changed

        event = MagicMock()
        event.data = {'object': {'id': 'sub_test_123', 'status': 'active'}}
        handle_subscription_changed(sender=None, event=event)


class PaymentsAdminTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_superuser(username='admin', email='admin@test.com', password='testpass')
        self.client.login(username='admin', password='testpass')

    @override_settings(STORAGES={"staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"}})
    def test_customer_admin_loads(self):
        """Customer admin changelist should load."""
        response = self.client.get('/admin/djstripe/customer/')
        self.assertEqual(response.status_code, 200)

    @override_settings(STORAGES={"staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"}})
    def test_product_admin_loads(self):
        """Product admin changelist should load."""
        response = self.client.get('/admin/djstripe/product/')
        self.assertEqual(response.status_code, 200)

    @override_settings(STORAGES={"staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"}})
    def test_price_admin_loads(self):
        """Price admin changelist should load."""
        response = self.client.get('/admin/djstripe/price/')
        self.assertEqual(response.status_code, 200)

    @override_settings(STORAGES={"staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"}})
    def test_subscription_admin_loads(self):
        """Subscription admin changelist should load."""
        response = self.client.get('/admin/djstripe/subscription/')
        self.assertEqual(response.status_code, 200)

    @override_settings(STORAGES={"staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"}})
    def test_paymentintent_admin_loads(self):
        """PaymentIntent admin changelist should load."""
        response = self.client.get('/admin/djstripe/paymentintent/')
        self.assertEqual(response.status_code, 200)

    def test_customer_admin_list_display(self):
        """Customer admin should display specific columns."""
        from django.contrib.admin.sites import site
        from djstripe.models import Customer

        admin_cls = site._registry[Customer]
        self.assertIn('subscriber', admin_cls.list_display)
        self.assertIn('created', admin_cls.list_display)

    def test_product_admin_list_display(self):
        """Product admin should display specific columns."""
        from django.contrib.admin.sites import site
        from djstripe.models import Product

        admin_cls = site._registry[Product]
        self.assertIn('name', admin_cls.list_display)
        self.assertIn('active', admin_cls.list_display)
        self.assertIn('type', admin_cls.list_display)

    def test_price_admin_list_display(self):
        """Price admin should display specific columns."""
        from django.contrib.admin.sites import site
        from djstripe.models import Price

        admin_cls = site._registry[Price]
        self.assertIn('product', admin_cls.list_display)
        self.assertIn('unit_amount', admin_cls.list_display)
        self.assertIn('currency', admin_cls.list_display)
        self.assertIn('recurring', admin_cls.list_display)

    def test_subscription_admin_list_display(self):
        """Subscription admin should display specific columns."""
        from django.contrib.admin.sites import site
        from djstripe.models import Subscription

        admin_cls = site._registry[Subscription]
        self.assertIn('customer', admin_cls.list_display)
        self.assertIn('status', admin_cls.list_display)
        self.assertIn('current_period_start', admin_cls.list_display)
        self.assertIn('current_period_end', admin_cls.list_display)

    def test_paymentintent_admin_list_display(self):
        """PaymentIntent admin should display specific columns."""
        from django.contrib.admin.sites import site
        from djstripe.models import PaymentIntent

        admin_cls = site._registry[PaymentIntent]
        self.assertIn('customer', admin_cls.list_display)
        self.assertIn('amount', admin_cls.list_display)
        self.assertIn('currency', admin_cls.list_display)
        self.assertIn('status', admin_cls.list_display)

    def test_customer_admin_search_fields(self):
        """Customer admin should have search fields configured."""
        from django.contrib.admin.sites import site
        from djstripe.models import Customer

        admin_cls = site._registry[Customer]
        self.assertTrue(len(admin_cls.search_fields) > 0)

    def test_subscription_admin_list_filter(self):
        """Subscription admin should have list filters configured."""
        from django.contrib.admin.sites import site
        from djstripe.models import Subscription

        admin_cls = site._registry[Subscription]
        self.assertIn('status', admin_cls.list_filter)
''',
}

# Template files stored separately for clarity
TEMPLATE_FILES = {
    'templates/payments/pricing.html': '''\
<c-layout title="Pricing">
    <section class="flex-1 py-16 lg:py-24" style="background-color: var(--navy-950);">
        <div class="max-w-5xl mx-auto px-6 sm:px-10 lg:px-16">
            <div class="text-center mb-12">
                <p class="text-xs font-semibold tracking-[0.3em] uppercase mb-4"
                   style="color: var(--amber-400);">Pricing</p>
                <h1 class="font-display text-3xl sm:text-4xl font-bold mb-4"
                    style="color: #e8ecf4;">Choose your plan</h1>
            </div>

            {% if not products %}
                <div class="text-center">
                    <p class="text-base mb-4" style="color: var(--slate-400);">
                        No products found. Run the seed command to create sample products:
                    </p>
                    <code class="text-sm px-4 py-2 rounded-lg inline-block"
                          style="background-color: var(--navy-800); color: var(--amber-400);">
                        python manage.py seed_payments
                    </code>
                </div>
            {% else %}
                <div class="grid gap-8 md:grid-cols-{{ products|length }} max-w-4xl mx-auto">
                    {% for product in products %}
                        <div class="rounded-xl p-8 flex flex-col"
                             style="background-color: var(--navy-800); border: 1px solid var(--slate-700);">
                            <h2 class="font-display text-xl font-bold mb-2" style="color: #e8ecf4;">
                                {{ product.name }}
                            </h2>
                            {% if product.description %}
                                <p class="text-sm mb-6" style="color: var(--slate-400);">
                                    {{ product.description }}
                                </p>
                            {% endif %}

                            <div class="flex-1 flex flex-col gap-4 mt-4">
                                {% for price in product.prices %}
                                    <div class="flex items-end justify-between gap-4 pb-4"
                                         style="border-bottom: 1px solid var(--slate-700);">
                                        <div>
                                            <span class="font-display text-2xl font-bold" style="color: #e8ecf4;">
                                                {{ price.display }}
                                            </span>
                                            {% if price.recurring %}
                                                <span class="text-sm" style="color: var(--slate-400);">/{{ price.recurring.interval }}</span>
                                            {% endif %}
                                        </div>
                                        <form method="post" action="{{ price.checkout_url }}">
                                            {% csrf_token %}
                                            <button type="submit"
                                                    class="px-5 py-2 text-xs font-semibold rounded-lg tracking-wide"
                                                    style="background-color: var(--amber-400); color: var(--navy-950);">
                                                {% if price.recurring %}Subscribe{% else %}Buy{% endif %}
                                            </button>
                                        </form>
                                    </div>
                                {% endfor %}
                            </div>
                        </div>
                    {% endfor %}
                </div>
            {% endif %}
        </div>
    </section>
</c-layout>
''',

    'templates/payments/success.html': '''\
<c-layout title="Payment Successful">
    <section class="flex-1 py-16 lg:py-24" style="background-color: var(--navy-950);">
        <div class="max-w-3xl mx-auto px-6 sm:px-10 lg:px-16 text-center">
            <p class="text-xs font-semibold tracking-[0.3em] uppercase mb-4" style="color: var(--amber-400);">Payment Confirmed</p>
            <h1 class="font-display text-3xl sm:text-4xl font-bold mb-4" style="color: #e8ecf4;">
                Thank you for your purchase!
            </h1>
            <p class="text-base mb-8" style="color: var(--slate-400);">
                Your payment was processed successfully.
            </p>
            <a href="{% url 'dashboard' %}"
               class="inline-block px-6 py-3 rounded-lg font-semibold text-sm transition-colors"
               style="background-color: var(--amber-400); color: var(--navy-950);">
                Go to Dashboard
            </a>
        </div>
    </section>
</c-layout>
''',

    'templates/payments/cancel.html': '''\
<c-layout title="Payment Cancelled">
    <section class="flex-1 py-16 lg:py-24" style="background-color: var(--navy-950);">
        <div class="max-w-3xl mx-auto px-6 sm:px-10 lg:px-16 text-center">
            <p class="text-xs font-semibold tracking-[0.3em] uppercase mb-4" style="color: var(--amber-400);">Payment Cancelled</p>
            <h1 class="font-display text-3xl sm:text-4xl font-bold mb-4" style="color: #e8ecf4;">
                No worries — nothing was charged.
            </h1>
            <p class="text-base mb-8" style="color: var(--slate-400);">
                You can try again whenever you\'re ready.
            </p>
            <a href="{% url 'dashboard' %}"
               class="inline-block px-6 py-3 rounded-lg font-semibold text-sm transition-colors"
               style="background-color: var(--amber-400); color: var(--navy-950);">
                Back to Dashboard
            </a>
        </div>
    </section>
</c-layout>
''',
}


def create_payments_app(base_dir):
    """Create all payments app files under base_dir. Skips files that already exist."""
    all_files = {**PAYMENTS_FILES, **TEMPLATE_FILES}

    for rel_path, content in all_files.items():
        full_path = os.path.join(base_dir, rel_path)

        if os.path.exists(full_path):
            continue

        os.makedirs(os.path.dirname(full_path), exist_ok=True)
        with open(full_path, 'w') as f:
            f.write(content)


def main(base_dir=None):
    """Run the full payments scaffold against base_dir (defaults to cwd)."""
    if base_dir is None:
        base_dir = os.getcwd()

    config_dir = os.path.join(base_dir, 'config')
    settings_path = os.path.join(config_dir, 'settings.py')
    urls_path = os.path.join(config_dir, 'urls.py')
    env_path = os.path.join(base_dir, '.env.example')
    justfile_path = os.path.join(base_dir, 'justfile')

    print('Creating payments app files...')
    create_payments_app(base_dir)

    print('Injecting djstripe and payments into INSTALLED_APPS...')
    inject_installed_apps(settings_path)

    print('Appending Stripe settings...')
    append_stripe_settings(settings_path)

    print('Wiring payments URLs...')
    wire_urls(urls_path)

    print('Updating .env.example...')
    update_env_example(env_path)

    print('Adding seed-payments recipe to justfile...')
    add_justfile_recipe(justfile_path)

    print('Done! Payments scaffold complete.')


if __name__ == '__main__':
    main()
