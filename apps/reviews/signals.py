from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.postgres.search import SearchVector
from .models import Property, Review, PropertyStatus

@receiver(post_save, sender=Property)
def update_property_search_vector(sender, instance, **kwargs):
    """
    A robust, world-class signal handler that correctly updates the search_vector
    for a Property instance after it has been saved, avoiding both recursion and FieldError.
    """
    # --- The Correct and Final Pattern ---
    
    # 1. Temporarily disconnect the signal to prevent an infinite loop.
    post_save.disconnect(update_property_search_vector, sender=Property)

    try:
        # 2. Calculate the search vector using a query that supports joins (.annotate).
        # We operate on a queryset for the specific instance.
        property_with_vector = Property.objects.filter(pk=instance.pk).annotate(
            vector=SearchVector('name', 'address', 'city', 'state__name', 'country__name')
        ).first()

        if property_with_vector:
            # 3. Update the specific instance's search_vector field in the database
            # with the pre-calculated value. This query does NOT contain joins.
            Property.objects.filter(pk=instance.pk).update(
                search_vector=property_with_vector.vector
            )
    finally:
        # 4. Reconnect the signal for future saves.
        post_save.connect(update_property_search_vector, sender=Property)


@receiver(post_save, sender=Review)
def update_review_verification_on_approval(sender, instance, **kwargs):
    """
    Listens for a Review being saved. If the review's property is now APPROVED,
    this function checks the author's current phone verification status
    and updates the review's historical flag accordingly.
    """
    if instance.unit.property.status != PropertyStatus.APPROVED:
        return

    if not instance.is_author_phone_verified and instance.author and instance.author.is_phone_verified:
        Review.objects.filter(pk=instance.pk).update(is_author_phone_verified=True)
        print(f"Retroactively applied 'Verified' badge to Review PK: {instance.pk}") # For debugging