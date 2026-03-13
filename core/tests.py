from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.db import OperationalError
from django.test import TestCase

User = get_user_model()


class HomePageTests(TestCase):
    def test_home_page_returns_200(self):
        response = self.client.get('/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Build.')

    def test_home_page_unauthenticated_shows_sign_in(self):
        response = self.client.get('/')
        self.assertContains(response, 'Sign In')

    def test_home_page_authenticated_shows_dashboard_cta(self):
        User.objects.create_user(username='testuser', email='test@example.com', password='testpass123')
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get('/')
        self.assertContains(response, 'Dashboard')


class DashboardTests(TestCase):
    def test_dashboard_requires_login(self):
        response = self.client.get('/dashboard/')
        self.assertEqual(response.status_code, 302)
        self.assertIn('/accounts/login/', response.url)

    def test_dashboard_authenticated(self):
        User.objects.create_user(username='testuser', email='test@example.com', password='testpass123')
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get('/dashboard/')
        self.assertEqual(response.status_code, 200)


class CounterPageTests(TestCase):
    def test_counter_page_returns_200(self):
        response = self.client.get('/examples/counter/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '0')


class CounterUpdateTests(TestCase):
    """Tests for the HTMX counter update endpoint.

    All POST requests include HTTP_HX_REQUEST='true' to simulate
    real HTMX requests, which sets request.htmx via django-htmx
    middleware.
    """

    def test_get_not_allowed(self):
        response = self.client.get('/examples/counter/update/')
        self.assertEqual(response.status_code, 405)

    def test_non_htmx_post_rejected(self):
        response = self.client.post('/examples/counter/update/', {
            'count': '0',
            'action': 'increment',
        })
        self.assertEqual(response.status_code, 400)

    def test_increment(self):
        response = self.client.post('/examples/counter/update/', {
            'count': '5',
            'action': 'increment',
        }, HTTP_HX_REQUEST='true')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '6')

    def test_decrement(self):
        response = self.client.post('/examples/counter/update/', {
            'count': '5',
            'action': 'decrement',
        }, HTTP_HX_REQUEST='true')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '4')

    def test_invalid_count_defaults_to_zero(self):
        response = self.client.post('/examples/counter/update/', {
            'count': 'abc',
            'action': 'increment',
        }, HTTP_HX_REQUEST='true')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '1')

    def test_empty_count_defaults_to_zero(self):
        response = self.client.post('/examples/counter/update/', {
            'count': '',
            'action': 'increment',
        }, HTTP_HX_REQUEST='true')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '1')

    def test_unknown_action_no_change(self):
        response = self.client.post('/examples/counter/update/', {
            'count': '5',
            'action': 'unknown',
        }, HTTP_HX_REQUEST='true')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '5')


class HealthCheckTests(TestCase):
    def test_health_check_ok(self):
        response = self.client.get('/health/')
        self.assertEqual(response.status_code, 200)
        self.assertJSONEqual(response.content, {'status': 'ok'})

    def test_health_check_db_down(self):
        with patch('core.views.connection') as mock_conn:
            mock_conn.ensure_connection.side_effect = OperationalError('connection refused')
            response = self.client.get('/health/')
            self.assertEqual(response.status_code, 503)
            self.assertJSONEqual(response.content, {'status': 'unhealthy'})


class ErrorPageTests(TestCase):
    def test_404_returns_custom_page(self):
        response = self.client.get('/this-page-does-not-exist/')
        self.assertEqual(response.status_code, 404)
        self.assertContains(response, '404', status_code=404)


class CustomUserModelTests(TestCase):
    def test_custom_user_model_configured(self):
        from django.conf import settings
        self.assertEqual(settings.AUTH_USER_MODEL, 'core.User')

    def test_create_user(self):
        user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123',
            first_name='Test',
            last_name='User',
        )
        self.assertEqual(user.email, 'test@example.com')
        self.assertEqual(user.get_full_name(), 'Test User')
