from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.postgres.search import SearchVector
from .models import Property, Review, PropertyStatus

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


@receiver(post_save, sender=Review)
def update_review_verification_on_approval(sender, instance, **kwargs):
    """
    Listens for a Review being saved. If the review's property is now APPROVED,
    this function checks the author's current phone verification status
    and updates the review's historical flag accordingly.
    """
    # We only care about reviews whose property status is APPROVED.
    if instance.unit.property.status != PropertyStatus.APPROVED:
        return

    # Check if the review's badge is currently False, but the author IS verified.
    # This is the exact condition we want to catch.
    if not instance.is_author_phone_verified and instance.author and instance.author.is_phone_verified:
        
        # Update the review's historical flag.
        # We use .update() to avoid triggering the save signal again and causing an infinite loop.
        Review.objects.filter(pk=instance.pk).update(is_author_phone_verified=True)
        print(f"Retroactively applied 'Verified' badge to Review PK: {instance.pk}") # For debugging