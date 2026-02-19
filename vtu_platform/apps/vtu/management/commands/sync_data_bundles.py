from decimal import Decimal

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from apps.vtu.models import DataBundlePlan, ServiceProvider
from apps.vtu.providers.vtpass import VTpassProvider


class Command(BaseCommand):
    help = 'Import/update VTpass data bundle plans.'

    def add_arguments(self, parser):
        parser.add_argument('--service-id', required=True, help='VTpass service id (e.g. mtn-data).')
        parser.add_argument('--provider-slug', default='vtpass')

    def handle(self, *args, **options):
        if settings.VTU_PROVIDER.lower() != 'vtpass':
            raise CommandError('VTU_PROVIDER must be set to vtpass to sync plans.')

        provider, _ = ServiceProvider.objects.get_or_create(
            slug=options['provider_slug'], defaults={'name': 'VTpass', 'is_active': True}
        )
        client = VTpassProvider(config=settings.VTPASS_CONFIG)
        plans = client.fetch_data_plans(options['service_id'])
        if not plans:
            self.stdout.write(self.style.WARNING('No plans returned by VTpass. Use admin CRUD as fallback.'))
            return

        updated = 0
        for plan in plans:
            amount = Decimal(str(plan.get('variation_amount', '0') or '0'))
            DataBundlePlan.objects.update_or_create(
                plan_code=plan.get('variation_code', ''),
                defaults={
                    'provider': provider,
                    'network': options['service_id'],
                    'name': plan.get('name') or plan.get('variation_code') or 'Unknown plan',
                    'amount': amount,
                    'is_active': bool(plan.get('is_active', True)),
                    'raw': plan,
                },
            )
            updated += 1

        self.stdout.write(self.style.SUCCESS(f'Synced {updated} plans for {options["service_id"]}.'))
