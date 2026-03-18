"""Tests for the add_payments scaffold script."""

import os
import tempfile
import unittest

CLEAN_SETTINGS_INSTALLED_APPS = """\
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.sites',
    'allauth',
    'allauth.account',
    'allauth.socialaccount',
    'django_cotton',
    'django_htmx',
    'tailwind',
    'theme',
    'core',
]
"""


class InjectInstalledAppsTests(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.settings_path = os.path.join(self.tmpdir, 'settings.py')
        with open(self.settings_path, 'w') as f:
            f.write(CLEAN_SETTINGS_INSTALLED_APPS)

    def test_inserts_djstripe_and_payments_before_core(self):
        from scripts.add_payments import inject_installed_apps

        inject_installed_apps(self.settings_path)

        with open(self.settings_path) as f:
            content = f.read()

        self.assertIn("    'djstripe',\n", content)
        self.assertIn("    'payments',\n", content)
        # Both should appear before 'core'
        djstripe_pos = content.index("'djstripe'")
        payments_pos = content.index("'payments'")
        core_pos = content.index("'core'")
        self.assertLess(djstripe_pos, core_pos)
        self.assertLess(payments_pos, core_pos)

    def test_idempotent_no_duplicates(self):
        from scripts.add_payments import inject_installed_apps

        inject_installed_apps(self.settings_path)
        inject_installed_apps(self.settings_path)

        with open(self.settings_path) as f:
            content = f.read()

        self.assertEqual(content.count("'djstripe'"), 1)
        self.assertEqual(content.count("'payments'"), 1)


CLEAN_SETTINGS_TAIL = """\
LOGGING = {
    'version': 1,
}
"""


class AppendStripeSettingsTests(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.settings_path = os.path.join(self.tmpdir, 'settings.py')
        with open(self.settings_path, 'w') as f:
            f.write(CLEAN_SETTINGS_TAIL)

    def test_appends_stripe_config_block(self):
        from scripts.add_payments import append_stripe_settings

        append_stripe_settings(self.settings_path)

        with open(self.settings_path) as f:
            content = f.read()

        self.assertIn('# --- Stripe / Payments ---', content)
        self.assertIn('STRIPE_MOCK_MODE', content)
        self.assertIn('DJSTRIPE_SUBSCRIBER_MODEL', content)
        self.assertIn('DJSTRIPE_FOREIGN_KEY_TO_FIELD', content)

    def test_idempotent(self):
        from scripts.add_payments import append_stripe_settings

        append_stripe_settings(self.settings_path)
        append_stripe_settings(self.settings_path)

        with open(self.settings_path) as f:
            content = f.read()

        self.assertEqual(content.count('# --- Stripe / Payments ---'), 1)


CLEAN_URLS = """\
from django.contrib import admin
from django.urls import include, path

from core import views

urlpatterns = [
    path('', views.home, name='home'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('health/', views.health, name='health'),
    path('admin/', admin.site.urls),
    path('', include('allauth.urls')),
]
"""


class WireUrlsTests(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.urls_path = os.path.join(self.tmpdir, 'urls.py')
        with open(self.urls_path, 'w') as f:
            f.write(CLEAN_URLS)

    def test_adds_payments_and_djstripe_urls(self):
        from scripts.add_payments import wire_urls

        wire_urls(self.urls_path)

        with open(self.urls_path) as f:
            content = f.read()

        self.assertIn("path('payments/', include('payments.urls'))", content)
        self.assertIn("path('stripe/', include('djstripe.urls', namespace='djstripe'))", content)

    def test_urls_inserted_before_admin(self):
        from scripts.add_payments import wire_urls

        wire_urls(self.urls_path)

        with open(self.urls_path) as f:
            content = f.read()

        payments_pos = content.index("payments.urls")
        admin_pos = content.index("admin.site.urls")
        self.assertLess(payments_pos, admin_pos)

    def test_idempotent(self):
        from scripts.add_payments import wire_urls

        wire_urls(self.urls_path)
        wire_urls(self.urls_path)

        with open(self.urls_path) as f:
            content = f.read()

        self.assertEqual(content.count("payments.urls"), 1)
        self.assertEqual(content.count("djstripe.urls"), 1)


CLEAN_ENV_EXAMPLE = """\
SECRET_KEY=django-insecure-dev-key-change-me
DEBUG=true
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/django_starter
"""


class UpdateEnvExampleTests(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.env_path = os.path.join(self.tmpdir, '.env.example')
        with open(self.env_path, 'w') as f:
            f.write(CLEAN_ENV_EXAMPLE)

    def test_appends_stripe_env_vars(self):
        from scripts.add_payments import update_env_example

        update_env_example(self.env_path)

        with open(self.env_path) as f:
            content = f.read()

        self.assertIn('STRIPE_MOCK_MODE=true', content)
        self.assertIn('STRIPE_LIVE_SECRET_KEY=', content)
        self.assertIn('STRIPE_TEST_SECRET_KEY=', content)
        self.assertIn('DJSTRIPE_WEBHOOK_SECRET=', content)

    def test_idempotent(self):
        from scripts.add_payments import update_env_example

        update_env_example(self.env_path)
        update_env_example(self.env_path)

        with open(self.env_path) as f:
            content = f.read()

        self.assertEqual(content.count('STRIPE_MOCK_MODE'), 1)


CLEAN_JUSTFILE = """\
manage := "uv run python manage.py"

# Run tests
[group: 'quality']
test *args:
    {{manage}} test {{args}}
"""


class AddJustfileRecipeTests(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.justfile_path = os.path.join(self.tmpdir, 'justfile')
        with open(self.justfile_path, 'w') as f:
            f.write(CLEAN_JUSTFILE)

    def test_adds_seed_payments_recipe(self):
        from scripts.add_payments import add_justfile_recipe

        add_justfile_recipe(self.justfile_path)

        with open(self.justfile_path) as f:
            content = f.read()

        self.assertIn('seed-payments', content)
        self.assertIn('seed_payments', content)

    def test_idempotent(self):
        from scripts.add_payments import add_justfile_recipe

        add_justfile_recipe(self.justfile_path)
        add_justfile_recipe(self.justfile_path)

        with open(self.justfile_path) as f:
            content = f.read()

        self.assertEqual(content.count('seed-payments'), 1)


class CreatePaymentsAppTests(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()

    def test_creates_all_python_modules(self):
        from scripts.add_payments import create_payments_app

        create_payments_app(self.tmpdir)

        expected_files = [
            'payments/__init__.py',
            'payments/apps.py',
            'payments/urls.py',
            'payments/views.py',
            'payments/services.py',
            'payments/mock.py',
            'payments/decorators.py',
            'payments/signals.py',
            'payments/admin.py',
            'payments/tests.py',
            'payments/management/__init__.py',
            'payments/management/commands/__init__.py',
            'payments/management/commands/seed_payments.py',
        ]
        for filepath in expected_files:
            full_path = os.path.join(self.tmpdir, filepath)
            self.assertTrue(os.path.exists(full_path), f'Missing: {filepath}')

    def test_creates_templates(self):
        from scripts.add_payments import create_payments_app

        create_payments_app(self.tmpdir)

        for template in ['pricing.html', 'success.html', 'cancel.html']:
            path = os.path.join(self.tmpdir, 'templates', 'payments', template)
            self.assertTrue(os.path.exists(path), f'Missing template: {template}')

    def test_idempotent_does_not_overwrite(self):
        from scripts.add_payments import create_payments_app

        create_payments_app(self.tmpdir)

        # Write a marker into a file
        marker_path = os.path.join(self.tmpdir, 'payments', 'views.py')
        with open(marker_path) as f:
            original = f.read()

        create_payments_app(self.tmpdir)

        with open(marker_path) as f:
            after = f.read()

        self.assertEqual(original, after)

    def test_apps_py_has_ready_method(self):
        from scripts.add_payments import create_payments_app

        create_payments_app(self.tmpdir)

        with open(os.path.join(self.tmpdir, 'payments', 'apps.py')) as f:
            content = f.read()

        self.assertIn('def ready(self)', content)
        self.assertIn('import payments.signals', content)

    def test_urls_py_has_app_name(self):
        from scripts.add_payments import create_payments_app

        create_payments_app(self.tmpdir)

        with open(os.path.join(self.tmpdir, 'payments', 'urls.py')) as f:
            content = f.read()

        self.assertIn("app_name = 'payments'", content)

    def test_services_has_key_functions(self):
        from scripts.add_payments import create_payments_app

        create_payments_app(self.tmpdir)

        with open(os.path.join(self.tmpdir, 'payments', 'services.py')) as f:
            content = f.read()

        self.assertIn('def get_customer(', content)
        self.assertIn('def charge_user(', content)
        self.assertIn('def create_subscription(', content)

    def test_decorators_has_requires_subscription(self):
        from scripts.add_payments import create_payments_app

        create_payments_app(self.tmpdir)

        with open(os.path.join(self.tmpdir, 'payments', 'decorators.py')) as f:
            content = f.read()

        self.assertIn('def requires_subscription(', content)


class MainFunctionTests(unittest.TestCase):
    """Test the main() orchestrator with a realistic project directory."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        # Create config/ dir with clean settings.py and urls.py
        config_dir = os.path.join(self.tmpdir, 'config')
        os.makedirs(config_dir)
        with open(os.path.join(config_dir, 'settings.py'), 'w') as f:
            f.write(CLEAN_SETTINGS_INSTALLED_APPS + CLEAN_SETTINGS_TAIL)
        with open(os.path.join(config_dir, 'urls.py'), 'w') as f:
            f.write(CLEAN_URLS)
        with open(os.path.join(self.tmpdir, '.env.example'), 'w') as f:
            f.write(CLEAN_ENV_EXAMPLE)
        with open(os.path.join(self.tmpdir, 'justfile'), 'w') as f:
            f.write(CLEAN_JUSTFILE)

    def test_main_creates_complete_payments_system(self):
        from scripts.add_payments import main

        main(self.tmpdir)

        # Spot-check key results
        settings = open(os.path.join(self.tmpdir, 'config', 'settings.py')).read()
        self.assertIn("'djstripe'", settings)
        self.assertIn('STRIPE_MOCK_MODE', settings)

        urls = open(os.path.join(self.tmpdir, 'config', 'urls.py')).read()
        self.assertIn('payments.urls', urls)

        self.assertTrue(os.path.exists(os.path.join(self.tmpdir, 'payments', 'views.py')))
        self.assertTrue(os.path.exists(os.path.join(self.tmpdir, 'templates', 'payments', 'pricing.html')))

    def test_main_idempotent(self):
        from scripts.add_payments import main

        main(self.tmpdir)
        main(self.tmpdir)

        settings = open(os.path.join(self.tmpdir, 'config', 'settings.py')).read()
        self.assertEqual(settings.count("'djstripe'"), 1)
        self.assertEqual(settings.count('# --- Stripe / Payments ---'), 1)

    def test_main_prints_status(self):
        import io
        from contextlib import redirect_stdout

        from scripts.add_payments import main

        buf = io.StringIO()
        with redirect_stdout(buf):
            main(self.tmpdir)

        output = buf.getvalue()
        self.assertIn('INSTALLED_APPS', output)
        self.assertIn('payments', output.lower())


if __name__ == '__main__':
    unittest.main()
