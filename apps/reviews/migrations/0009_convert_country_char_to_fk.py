# In reviews/migrations/0009_convert_country_char_to_fk.py

from django.db import migrations, models
import django.db.models.deletion

def convert_country_and_state_data(apps, schema_editor):
    """
    This function will read the old string-based country/state names,
    find the corresponding objects in the locations app, and populate
    the new ForeignKey fields.
    """
    Property = apps.get_model('reviews', 'Property')
    Country = apps.get_model('locations', 'Country')
    State = apps.get_model('locations', 'State')

    # Use a dictionary for fast lookups
    countries = {c.name: c for c in Country.objects.all()}
    states = {f"{s.name},{s.country.name}": s for s in State.objects.all()}

    for prop in Property.objects.all():
        # Find the country object that matches the old text name
        country_obj = countries.get(prop.country_name)
        if country_obj:
            prop.country_fk = country_obj
        
        # Find the state object
        # NOTE: This assumes your old state field stored a simple name like "Lagos"
        # We need to find a state named "Lagos" within the found country.
        if country_obj and prop.state_name:
            state_obj = State.objects.filter(name=prop.state_name, country=country_obj).first()
            if state_obj:
                prop.state_fk = state_obj
        
        prop.save()


class Migration(migrations.Migration):

    dependencies = [
        ('reviews', '0007_alter_property_name'), # The broken migration
        ('locations', '0001_initial'), # Make sure this matches your locations app's first migration
    ]

    operations = [
        # 1. Temporarily rename the old CharFields to store their data
        migrations.RenameField(
            model_name='property',
            old_name='country',
            new_name='country_name',
        ),
        migrations.RenameField(
            model_name='property',
            old_name='state',
            new_name='state_name',
        ),

        # 2. Create the new, empty ForeignKey fields
        migrations.AddField(
            model_name='property',
            name='country_fk',
            field=models.ForeignKey(
                to='locations.country',
                on_delete=django.db.models.deletion.SET_NULL,
                null=True,
                blank=True
            ),
        ),
        migrations.AddField(
            model_name='property',
            name='state_fk',
            field=models.ForeignKey(
                to='locations.state',
                on_delete=django.db.models.deletion.SET_NULL,
                null=True,
                blank=True
            ),
        ),

        # 3. Run our custom Python function to migrate the data
        migrations.RunPython(convert_country_and_state_data),

        # 4. Remove the old temporary CharFields
        migrations.RemoveField(
            model_name='property',
            name='country_name',
        ),
        migrations.RemoveField(
            model_name='property',
            name='state_name',
        ),

        # 5. Rename the new ForeignKey fields to the final names ('country' and 'state')
        migrations.RenameField(
            model_name='property',
            old_name='country_fk',
            new_name='country',
        ),
        migrations.RenameField(
            model_name='property',
            old_name='state_fk',
            new_name='state',
        ),
    ]