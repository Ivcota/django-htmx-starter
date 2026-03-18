from unittest.mock import MagicMock, patch

from django.conf import settings
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
