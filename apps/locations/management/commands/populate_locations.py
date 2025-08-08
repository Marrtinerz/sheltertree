# Run python manage.py populate_locations
# to update locations.


# apps/locations/management/commands/populate_locations.py
import pycountry
from django.core.management.base import BaseCommand
from django.db import transaction
from apps.locations.models import Country, State

class Command(BaseCommand):
    help = 'Syncs the database with countries and states from the pycountry library. Safe to run multiple times.'

    @transaction.atomic # This ensures the entire operation is a single, safe transaction.
    def handle(self, *args, **kwargs):
        self.stdout.write(self.style.SUCCESS('Starting location sync...'))

        # --- Dictionaries for tracking changes ---
        stats = {
            'countries_created': 0,
            'countries_updated': 0,
            'countries_deactivated': 0,
            'states_created': 0,
            'states_updated': 0,
        }

        # --- Step 1: Sync Countries ---
        # Get all country codes currently in our DB to track which ones to deactivate later.
        all_db_country_codes = set(Country.objects.values_list('code', flat=True))
        pycountry_codes = set()

        for country_data in pycountry.countries:
            country_code = country_data.alpha_2
            pycountry_codes.add(country_code)

            # Use update_or_create. This finds a country by its unique 'code'.
            # If it exists, it updates the fields in 'defaults'.
            # If it doesn't exist, it creates a new record.
            country, created = Country.objects.update_or_create(
                code=country_code,
                defaults={
                    'name': country_data.name,
                    'is_active': True # Ensure active countries are marked as such
                }
            )

            if created:
                stats['countries_created'] += 1
            else:
                stats['countries_updated'] += 1

            # --- Step 2: Sync States for the current Country ---
            try:
                subdivisions = pycountry.subdivisions.get(country_code=country_data.alpha_2)
                for sub_data in subdivisions:
                    # Same logic for states. A state is unique by its name and country.
                    state, state_created = State.objects.update_or_create(
                        country=country,
                        name=sub_data.name,
                        defaults={'is_active': True}
                    )
                    if state_created:
                        stats['states_created'] += 1
                    else:
                        stats['states_updated'] += 1

            except KeyError:
                # Some countries (like Vatican City) don't have subdivisions in pycountry.
                # We can safely ignore this and continue.
                continue

        # --- Step 3: Deactivate Countries that no longer exist in the pycountry standard ---
        codes_to_deactivate = all_db_country_codes - pycountry_codes
        if codes_to_deactivate:
            deactivated_count, _ = Country.objects.filter(code__in=codes_to_deactivate).update(is_active=False)
            stats['countries_deactivated'] = deactivated_count
            self.stdout.write(self.style.WARNING(f'Deactivated {deactivated_count} countries: {list(codes_to_deactivate)}'))

        # --- Final Report ---
        self.stdout.write(self.style.SUCCESS('--------------------'))
        self.stdout.write(self.style.SUCCESS('Sync Complete!'))
        self.stdout.write(f"  Countries Created: {stats['countries_created']}")
        self.stdout.write(f"  Countries Updated: {stats['countries_updated']}")
        self.stdout.write(f"  Countries Deactivated: {stats['countries_deactivated']}")
        self.stdout.write(f"  States Created: {stats['states_created']}")
        self.stdout.write(f"  States Updated: {stats['states_updated']}")
        
        
