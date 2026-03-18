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
