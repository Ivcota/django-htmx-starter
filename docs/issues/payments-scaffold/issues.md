# Payments Scaffold — Implementation Issues

Parent PRD: `feat: One-command Stripe payments scaffold` (saved at `/private/tmp/claude-501/prd-body.md`)

---

## Issue 1: Foundation — dj-stripe integration + mock mode infrastructure

### What to build

The foundational layer that all other payments slices depend on. This slice installs dj-stripe, wires it into Django settings, creates the `payments/` app skeleton, and implements the mock mode infrastructure that allows the entire payments system to work without a Stripe account.

End-to-end: a developer can install the app, run migrations, and toggle between mock/live mode via an environment variable. The app loads cleanly in both modes and the mock infrastructure is ready to be consumed by service functions in later slices.

**Key deliverables:**
- Add `dj-stripe` to `pyproject.toml` via `uv add`
- Create `payments/` Django app with `__init__.py`, `apps.py`, empty module files
- Add `"djstripe"` and `"payments"` to `INSTALLED_APPS` in `config/settings.py`
- Append `# --- Stripe / Payments ---` config block to `settings.py` with: `STRIPE_LIVE_SECRET_KEY`, `STRIPE_TEST_SECRET_KEY`, `DJSTRIPE_WEBHOOK_SECRET`, `STRIPE_MOCK_MODE`, `DJSTRIPE_SUBSCRIBER_MODEL`, `DJSTRIPE_FOREIGN_KEY_TO_FIELD`
- Add `payments.urls` include to `config/urls.py`
- Add dj-stripe webhook URL at `/stripe/webhook/`
- Update `.env.example` with Stripe env vars (mock mode defaults to `true`)
- Implement `payments/mock.py` with core mock infrastructure for creating fake dj-stripe model instances (prefixed with `mock_`)
- Create `payments/urls.py` with empty urlpatterns

### Acceptance criteria

- [ ] `dj-stripe` is in `pyproject.toml` and installable via `uv sync`
- [ ] `payments` app is created and registered in `INSTALLED_APPS`
- [ ] dj-stripe migrations run successfully (`python manage.py migrate`)
- [ ] `STRIPE_MOCK_MODE` setting is readable from environment and defaults to `true`
- [ ] `.env.example` contains all Stripe-related env vars with comments
- [ ] Webhook URL is registered at `/stripe/webhook/`
- [ ] `mock.py` provides helper functions for creating fake Customer, Product, Price, and PaymentIntent dj-stripe records
- [ ] Existing tests continue to pass
- [ ] New tests verify: app loads, mock mode toggle works, mock helpers create valid DB records

### Blocked by

None — can start immediately.

### User stories addressed

- User story 2 (mock mode for prototyping without Stripe)
- User story 3 (mock mode activates automatically)
- User story 19 (idempotent — app registration checks)
- User story 20 (`.env.example` updated)

---

## Issue 2: One-time checkout flow (end-to-end tracer bullet)

### What to build

The first thin, complete path through every layer of the payments system. A user can click "Buy", go through checkout, and land on a success page — with a real payment record created in the database. This proves the entire architecture works end-to-end.

In live mode, this uses Stripe Checkout (redirect). In mock mode, it skips Stripe, creates fake records, and redirects straight to the success page.

**Key deliverables:**
- `payments/services.py`: `get_customer(user)` and `charge_user(user, price_id)` functions
- `payments/views.py`: `checkout` view (creates Stripe Checkout Session or mock), `success` view, `cancel` view
- `payments/urls.py`: routes for `/payments/checkout/<price_id>/`, `/payments/success/`, `/payments/cancel/`
- `templates/payments/success.html` and `cancel.html` using Cotton components and Tailwind
- Mock mode: `charge_user()` delegates to `mock.py` to create fake PaymentIntent + Charge records, then redirects to success
- Live mode: `charge_user()` creates a real Stripe Checkout Session and redirects to Stripe

### Acceptance criteria

- [ ] `get_customer(user)` returns or creates a dj-stripe Customer linked to the Django user
- [ ] `charge_user(user, price_id)` initiates a one-time payment flow
- [ ] In mock mode: checkout creates DB records and redirects to success page
- [ ] In live mode: checkout redirects to Stripe Checkout
- [ ] Success page renders with confirmation message and uses Cotton layout
- [ ] Cancel page renders with retry messaging and uses Cotton layout
- [ ] Unauthenticated users are redirected to login
- [ ] Tests cover: full mock checkout flow, success/cancel view responses, get_customer creation and retrieval

### Blocked by

- Blocked by Issue 1 (Foundation)

### User stories addressed

- User story 1 (start building paid product immediately)
- User story 4 (`charge_user()` simple function call)
- User story 7 (`get_customer()` helper)
- User story 9 (Stripe Checkout redirect)
- User story 10 (success and cancel pages)

---

## Issue 3: Subscription checkout + access control decorator

### What to build

Extends the checkout flow to support recurring subscriptions and adds the `@requires_subscription` decorator for gating views behind an active subscription.

**Key deliverables:**
- `payments/services.py`: `create_subscription(user, price_id)` function
- `payments/decorators.py`: `@requires_subscription(price_id=None)` view decorator
- Modify `checkout` view to handle both one-time and subscription prices (determined by Price type)
- Mock mode: `create_subscription()` creates fake Subscription records with `status="active"` and appropriate period dates
- `@requires_subscription` checks for active dj-stripe Subscription on the user's Customer; redirects to pricing page if none found

### Acceptance criteria

- [ ] `create_subscription(user, price_id)` initiates a subscription flow
- [ ] In mock mode: creates fake Subscription record and redirects to success
- [ ] In live mode: creates Stripe Checkout Session in subscription mode
- [ ] Checkout view auto-detects whether a Price is one-time or recurring
- [ ] `@requires_subscription` allows access for users with active subscriptions
- [ ] `@requires_subscription` redirects users without subscriptions (to pricing page)
- [ ] `@requires_subscription(price_id="specific_id")` gates on a specific price/plan
- [ ] `@requires_subscription` with no args gates on any active subscription
- [ ] Tests cover: mock subscription flow, decorator allows/denies access, decorator with specific price_id

### Blocked by

- Blocked by Issue 2 (One-time checkout)

### User stories addressed

- User story 5 (`create_subscription()`)
- User story 6 (`@requires_subscription` decorator)

---

## Issue 4: Dynamic pricing page

### What to build

A pricing page that dynamically renders Products and Prices from the dj-stripe database, with "Subscribe" and "Buy" buttons that initiate the checkout flow. Uses Cotton components and Tailwind CSS to match the starter's design language.

**Key deliverables:**
- `payments/views.py`: `pricing` view that queries active Products and their Prices from dj-stripe models
- `templates/payments/pricing.html`: dynamic pricing page using Cotton layout component
- Pricing cards for each Product showing name, description, price(s), and billing interval
- "Subscribe" button for recurring prices, "Buy" button for one-time prices — both link to checkout
- Monthly/yearly toggle for subscription products with multiple price points
- Responsive design matching the starter's existing aesthetic

### Acceptance criteria

- [ ] Pricing page renders at `/payments/pricing/`
- [ ] Products and Prices are pulled dynamically from dj-stripe models (not hardcoded)
- [ ] Each product displays as a styled card with name, description, and price
- [ ] Recurring prices show billing interval (e.g., "$10/month")
- [ ] One-time prices show flat amount (e.g., "$199")
- [ ] Buy/Subscribe buttons link to `/payments/checkout/<price_id>/`
- [ ] Page uses Cotton layout component and Tailwind styling
- [ ] Page is responsive (mobile-friendly)
- [ ] Empty state: page handles gracefully when no products exist (shows message to run seed command)
- [ ] Tests cover: page renders, displays seeded products, buttons link to correct checkout URLs

### Blocked by

- Blocked by Issue 2 (One-time checkout — needs checkout URLs to link to)

### User stories addressed

- User story 8 (dynamic pricing page from database)
- User story 21 (Cotton components + Tailwind styling)

---

## Issue 5: Billing portal, signal handlers, and admin customization

### What to build

Three related capabilities that round out the payments experience: a billing portal redirect for subscription self-service, Django signal handlers for reacting to payment events, and admin customization for viewing payment data.

**Key deliverables:**
- `payments/views.py`: `billing_portal` view that creates a Stripe Billing Portal session and redirects (in mock mode: redirects to dashboard with toast)
- `payments/urls.py`: add `/payments/portal/` route
- `payments/signals.py`: handlers for `payment_succeeded` and `subscription_changed` events, connected to dj-stripe webhook processing, with clear comments showing where to add custom logic
- `payments/admin.py`: register/customize dj-stripe models (Customer, Product, Price, Subscription, PaymentIntent) in Django admin with useful list displays and search

### Acceptance criteria

- [ ] `/payments/portal/` redirects to Stripe Billing Portal in live mode
- [ ] `/payments/portal/` redirects to dashboard with toast notification in mock mode
- [ ] Portal view requires authentication
- [ ] `payment_succeeded` signal handler is connected and fires on webhook events
- [ ] `subscription_changed` signal handler is connected and fires on status changes
- [ ] Signal handlers include clear inline comments for developer customization
- [ ] Django admin shows Customer, Product, Price, Subscription, PaymentIntent models
- [ ] Admin list views have useful columns (customer email, amount, status, dates)
- [ ] Admin has search and filter capabilities on key fields
- [ ] Tests cover: portal redirect behavior (mock + conceptual live), signal handlers fire, admin views load

### Blocked by

- Blocked by Issue 3 (Subscriptions — portal and signals depend on subscription infrastructure)

### User stories addressed

- User story 11 (billing portal redirect)
- User story 12 (purchases in admin)
- User story 13 (admin displays all payment models)
- User story 14 (webhook handling)
- User story 15 (signal handlers)

---

## Issue 6: Seed command

### What to build

A Django management command that populates the database with example Products and Prices for development and testing. Runnable via `just seed-payments`.

**Key deliverables:**
- `payments/management/commands/seed_payments.py`: creates example dj-stripe Product and Price records
- Seed data:
  - 1 subscription Product: "Pro Plan" with 2 Prices ($10/month, $100/year)
  - 1 one-time Product: "Lifetime Access" at $199
- Command is idempotent (skips creation if products already exist)
- Add `seed-payments` recipe to `justfile`

### Acceptance criteria

- [ ] `python manage.py seed_payments` creates the expected Products and Prices
- [ ] Running the command twice does not create duplicates
- [ ] Products appear correctly on the pricing page (if Issue 4 is complete)
- [ ] Products and Prices appear in Django admin
- [ ] `just seed-payments` recipe works
- [ ] Tests cover: seed creates expected records, idempotency (run twice, same count)

### Blocked by

- Blocked by Issue 1 (Foundation — needs dj-stripe models available)

### User stories addressed

- User story 16 (`just seed-payments` command)
- User story 17 (sample products: Pro Plan + Lifetime Access)

---

## Issue 7: Scaffold script (`just add-payments`)

### What to build

The capstone: a Python script that generates everything from Issues 1–6 automatically with a single `just add-payments` command. The script takes a fresh clone of the starter and adds the complete payments system — installing dependencies, creating the `payments/` app, injecting settings, wiring URLs, and adding all templates.

**Key deliverables:**
- `scripts/add_payments.py`: Python script that:
  - Runs `uv add dj-stripe`
  - Creates the `payments/` app directory with all modules (services, views, decorators, mock, signals, admin, urls, tests, management command, templates)
  - Injects `"djstripe"` and `"payments"` into `INSTALLED_APPS` (inline in the list)
  - Appends Stripe config block to `settings.py`
  - Adds `payments.urls` and webhook URL to `urls.py`
  - Updates `.env.example` with Stripe env vars
  - Adds `seed-payments` recipe to `justfile`
  - All operations are idempotent (checks before modifying)
- `justfile`: `add-payments` recipe that calls the script
- Clear console output during execution showing each step

### Acceptance criteria

- [ ] `just add-payments` runs successfully on a fresh clone
- [ ] Running `just add-payments` twice produces no errors or duplicate configuration
- [ ] After running, `python manage.py migrate` succeeds
- [ ] After running, `python manage.py test payments` passes
- [ ] After running, `just seed-payments` creates example products
- [ ] All files from Issues 1–6 are generated correctly
- [ ] Settings injection places apps in `INSTALLED_APPS` inline (not appended as separate block)
- [ ] Script provides clear console output for each step
- [ ] Inline comments in generated code help developers understand and customize (User story 23)
- [ ] Switching from mock to live requires only env var changes (User story 22)

### Blocked by

- Blocked by Issues 1–6 (needs all payments features built and tested first)

### User stories addressed

- User story 1 (single command to add payments)
- User story 19 (idempotent)
- User story 22 (mock-to-live via env vars only)
- User story 23 (clear inline comments)
