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
