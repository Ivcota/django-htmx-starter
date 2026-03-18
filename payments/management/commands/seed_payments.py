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
