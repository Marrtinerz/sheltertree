from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.postgres.search import SearchVector
from .models import Property

@receiver(post_save, sender=Property)
def update_property_search_vector(sender, instance, **kwargs):
    """
    A signal handler that correctly updates the search_vector for a Property
    instance after it has been saved, avoiding recursion and FieldError.
    """
    # --- The Correct Pattern ---
    
    # 1. Temporarily disconnect the signal to prevent an infinite loop
    post_save.disconnect(update_property_search_vector, sender=Property)

    # 2. Calculate the search vector using an .annotate() query.
    #    This is a SELECT operation, which fully supports joins.
    vector = SearchVector('name', 'address', 'city', 'state__name', 'country__name')
    
    # We must operate on the specific instance. We annotate it and update the field in memory.
    instance.search_vector = Property.objects.filter(pk=instance.pk).annotate(
        vector=vector
    ).values('vector').first()['vector']
    
    # 3. Save the instance again, but only update the search_vector field.
    #    This save() call will NOT trigger the signal because it is disconnected.
    instance.save(update_fields=['search_vector'])

    # 4. Reconnect the signal for future saves on other instances.
    post_save.connect(update_property_search_vector, sender=Property)