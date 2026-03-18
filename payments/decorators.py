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
