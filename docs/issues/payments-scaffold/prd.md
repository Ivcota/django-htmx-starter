## Problem Statement

When a developer clones this starter and wants to add payments to their app, they face a significant setup burden: choosing a Stripe library, installing it, configuring Django settings, setting up webhook handling, creating models, building checkout flows, and wiring up the admin — all before they can even test a single purchase. This friction slows down the critical "idea to revenue" path and is especially painful when the developer doesn't yet have a Stripe account or wants to prototype before committing to payment infrastructure.

## Solution

A single `just add-payments` command that fully scaffolds a production-ready payments system into the project. The command installs dj-stripe, creates a `payments/` Django app with a clean developer API (`charge_user()`, `create_subscription()`, `@requires_subscription`), wires up Stripe Checkout (redirect-based), adds a dynamic pricing page, configures webhook handling, and registers everything in the admin.

Critically, the scaffold includes a **mock mode** that activates automatically when no Stripe API keys are configured. In mock mode, the entire payments flow works — the developer API creates real database records, the admin shows purchases and subscriptions, and views behave correctly — all without touching the Stripe API. When the developer is ready to go live, they add their Stripe keys, flip `STRIPE_MOCK_MODE=false`, and everything switches to real Stripe seamlessly.

## User Stories

1. As a developer cloning this starter, I want to run a single command to add payments, so that I can start building a paid product immediately.
2. As a developer without a Stripe account, I want payments to work in mock mode, so that I can prototype my product's purchase flows without signing up for Stripe.
3. As a developer, I want mock mode to activate automatically when no Stripe keys are set, so that I don't need to configure anything to get started.
4. As a developer, I want to charge a user with a simple function call like `charge_user(user, price_id)`, so that I don't need to learn the Stripe API to process payments.
5. As a developer, I want to create subscriptions with `create_subscription(user, price_id)`, so that I can offer recurring billing with minimal code.
6. As a developer, I want a `@requires_subscription` decorator, so that I can gate views behind an active subscription with one line of code.
7. As a developer, I want a `get_customer(user)` helper, so that I can easily access or create the Stripe customer linked to a Django user.
8. As a developer, I want a dynamic pricing page that pulls Products and Prices from the database, so that I can update my offerings without changing templates.
9. As a developer, I want Stripe Checkout (redirect-based) for payment collection, so that I get PCI compliance without building payment forms.
10. As a developer, I want success and cancel pages after checkout, so that users get clear feedback on their payment status.
11. As a developer, I want a billing portal redirect, so that my users can manage their subscriptions and payment methods through Stripe's hosted portal.
12. As a developer, I want purchases and subscriptions to appear in the Django admin, so that I can see payment activity without logging into Stripe.
13. As a developer, I want the admin to display Customers, Products, Prices, Subscriptions, and PaymentIntents, so that I have full visibility into payment data.
14. As a developer, I want webhook handling configured automatically, so that subscription status changes and payment events are processed without manual setup.
15. As a developer, I want Django signal handlers scaffolded for `payment_succeeded` and `subscription_changed`, so that I can easily hook into payment events to grant access or send emails.
16. As a developer, I want a `just seed-payments` command, so that I can populate example Products and Prices for development and testing.
17. As a developer, I want the seed command to create a sample subscription product (Pro Plan — monthly and yearly prices) and a one-time product (Lifetime Access), so that I have realistic test data immediately.
18. As a developer, I want the scaffold to include tests for the payments module, so that I can verify the payments system works and have examples to follow for my own tests.
19. As a developer, I want the `just add-payments` command to be idempotent, so that running it twice doesn't break my project.
20. As a developer, I want the `.env.example` updated with Stripe environment variables, so that I know exactly which keys I need when going live.
21. As a developer, I want the pricing page to use the existing Cotton component system and Tailwind styling, so that it matches the rest of the starter's design language.
22. As a developer transitioning from mock to live mode, I want to only change environment variables (add Stripe keys, set `STRIPE_MOCK_MODE=false`), so that the switch requires zero code changes.
23. As a developer, I want clear inline comments in the scaffolded code, so that I can understand and customize the payments module for my specific needs.

## Implementation Decisions

### Command & Orchestration
- `just add-payments` is the entry point — it calls a Python script (not a shell script) for reliable text manipulation of settings and URL files
- The command is idempotent — safe to run multiple times without duplicating configuration
- The Python script handles: installing dj-stripe via `uv add`, creating the `payments/` app, modifying `config/settings.py`, modifying `config/urls.py`, updating `.env.example`, and adding `justfile` recipes

### Settings Injection
- `"djstripe"` and `"payments"` are inserted directly into the existing `INSTALLED_APPS` list (inline, not appended separately)
- A clearly marked `# --- Stripe / Payments ---` configuration block is appended to the bottom of `settings.py` containing: `STRIPE_LIVE_SECRET_KEY`, `STRIPE_TEST_SECRET_KEY`, `DJSTRIPE_WEBHOOK_SECRET`, `STRIPE_MOCK_MODE`, `DJSTRIPE_SUBSCRIBER_MODEL` (pointing to the custom User model), and `DJSTRIPE_FOREIGN_KEY_TO_FIELD`

### Payments App Architecture
- New `payments/` Django app with the following modules:
  - `services.py` — `charge_user()`, `create_subscription()`, `get_customer()` functions that abstract dj-stripe/Stripe API calls
  - `decorators.py` — `@requires_subscription` view decorator that checks for active subscription status
  - `mock.py` — Mock mode logic that creates fake dj-stripe database records instead of calling Stripe API
  - `signals.py` — Handlers for payment and subscription lifecycle events
  - `views.py` — Checkout session creation, success/cancel pages, billing portal redirect, pricing page
  - `urls.py` — Routes under `/payments/` prefix
  - `admin.py` — Customized admin registration for dj-stripe models
  - `management/commands/seed_payments.py` — Seeds example Products and Prices

### Mock Mode
- Implemented at the Django level (not using stripe-mock server) — no additional Docker services required
- Activated when `STRIPE_MOCK_MODE=true` (defaults to `true` in `.env.example`)
- The service functions in `services.py` check the mock flag and delegate to either real Stripe calls or `mock.py` functions
- Mock functions create real dj-stripe model instances in the database with fake Stripe IDs (prefixed with `mock_`)
- The admin, decorators, and all query-based logic work identically in mock and live mode since they query the same database models

### Checkout Flow
- Stripe Checkout with redirect (not embedded) — PCI compliant with zero frontend work
- Flow: User clicks buy → `checkout` view creates a Stripe Checkout Session → redirect to Stripe → Stripe redirects to success/cancel URL
- In mock mode: the checkout view skips Stripe, creates the records directly, and redirects straight to the success page

### Pricing Page
- Dynamically renders Products and Prices from dj-stripe database models
- Uses Django Cotton components and Tailwind CSS to match the starter's existing design
- Each product shows a "Subscribe" or "Buy" button that initiates the checkout flow

### Billing Portal
- Single redirect view that creates a Stripe Billing Portal session and redirects the user
- In mock mode: redirects to dashboard with a toast notification explaining that billing portal is only available in live mode

### Signal Handlers
- Scaffolded handlers for `payment_succeeded` and `subscription_changed` with clear comments showing where developers should add their custom logic (e.g., granting access, sending emails)
- Connected to dj-stripe's webhook event processing

### URL Structure
- `/payments/pricing/` — Dynamic pricing page
- `/payments/checkout/<price_id>/` — Initiate checkout for a specific price
- `/payments/success/` — Post-checkout success page
- `/payments/cancel/` — Post-checkout cancel page
- `/payments/portal/` — Redirect to Stripe billing portal
- `/stripe/webhook/` — dj-stripe webhook endpoint (standard dj-stripe path)

### Justfile Recipes
- `add-payments` — Runs the scaffold script
- `seed-payments` — Runs the `seed_payments` management command

## Testing Decisions

A good test for the payments module verifies **external behavior through the public interface** — it tests what the service functions return and what the views respond with, not how they internally call Stripe or construct objects.

### What Will Be Tested
- **Services**: `charge_user()`, `create_subscription()`, and `get_customer()` in mock mode — verify they create correct database records and return expected objects
- **Decorators**: `@requires_subscription` — verify it allows users with active subscriptions and redirects users without
- **Views**: Checkout, success, cancel, pricing, and portal views — verify correct HTTP responses, redirects, and template rendering
- **Seed Command**: Verify it creates the expected Products and Prices in the database
- **Mock Mode**: Verify the mock flag correctly toggles between mock and live behavior

### Testing Approach
- Follow the existing pattern in `core/tests.py`: `TestCase` classes, Django test client, direct assertions
- All tests run in mock mode (no Stripe keys needed in CI)
- Tests are included in `payments/tests.py`

## Out of Scope

- Multi-currency support
- Coupons or promotional codes
- Usage-based or metered billing
- Tax calculation (Stripe Tax)
- Team or organization-level billing (one subscription covering multiple users)
- Invoicing beyond what Stripe auto-generates
- Embedded payment forms (using Stripe Checkout redirect only)
- Stripe Connect or marketplace payments
- Payment method management outside of Stripe's hosted billing portal
- Email notifications (signal handlers are scaffolded but sending emails is left to the developer)

## Further Notes

- The scaffold is designed to be a starting point, not a complete billing system. Developers are expected to customize the services, views, and templates for their specific product.
- dj-stripe maintains its own models and migrations. The `payments/` app's migrations will only cover any custom models if needed — the core Stripe data lives in dj-stripe's tables.
- When transitioning from mock to live mode, developers should: (1) create a Stripe account, (2) add API keys to `.env`, (3) set `STRIPE_MOCK_MODE=false`, (4) run `python manage.py djstripe_sync_models` to pull their Stripe data, and (5) use `stripe listen --forward-to localhost:8000/stripe/webhook/` for local webhook testing.
- The mock mode seed data (via `just seed-payments`) creates: 1 subscription Product ("Pro Plan") with 2 Prices ($10/month, $100/year) and 1 one-time Product ("Lifetime Access") at $199.
