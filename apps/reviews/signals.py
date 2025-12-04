from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.postgres.search import SearchVector
from .models import Property, Review, PropertyStatus, ReviewStatus
from allauth.account.signals import user_signed_up, user_logged_in
from apps.core.models import PlatformFeedback

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

        
def claim_pending_submissions(request, user):
    """
    Common logic to claim pending submissions (Review, Property, Feedback) from session.
    """
    if not request:
        return

    # 1. Claim Review & Feedback
    review_data = request.session.get('pending_review_submission')
    
    if review_data:
        # A. Claim Review
        review_id = review_data.get('review_id')
        try:
            review = Review.objects.get(pk=review_id)
            
            # --- TRUSTED HANDOFF LOGIC ---
            # We claim the review if:
            # 1. It is PENDING_SIGNUP (Orphan/Limbo)
            # 2. OR It is Orphan (author is None)
            # 3. OR It is PENDING_CONTENT_REVIEW (claimed by Typo User) BUT we have the session key.
            # We skip if it is APPROVED or REJECTED to protect live data.
            
            can_claim = review.status in [ReviewStatus.PENDING_SIGNUP, ReviewStatus.PENDING_CONTENT_REVIEW, ReviewStatus.PENDING_PROPERTY_APPROVAL]
            
            if can_claim:
                review.author = user
                
                # Sync verification status
                if user.is_phone_verified:
                    review.is_author_phone_verified = True
                
                # Note: We do NOT promote status here anymore. 
                # We leave it as-is. The Handler view will ensure it's correct.
                # Exception: If it was purely PENDING_SIGNUP, we can leave it or promote it.
                # To be safe, we let the Handler do the final promotion.
                
                review.save()
                
        except Review.DoesNotExist:
            pass

        # B. Claim Feedback (Preserved)
        feedback_id = review_data.get('feedback_id')
        if feedback_id:
            try:
                # Only claim if it's currently anonymous
                feedback = PlatformFeedback.objects.get(pk=feedback_id, user__isnull=True)
                feedback.user = user
                feedback.save()
            except PlatformFeedback.DoesNotExist:
                pass

    # 2. Claim Property
    prop_data = request.session.get('pending_property_submission')
    if prop_data:
        prop_id = prop_data.get('property_id')
        try:
            prop = Property.objects.get(pk=prop_id)
            
            # Allow claiming if pending approval (fresh) or orphan
            if prop.status == PropertyStatus.PENDING_APPROVAL:
                prop.added_by = user
                prop.save()
                
        except Property.DoesNotExist:
            pass

@receiver(user_signed_up)
def handle_user_signup(sender, request, user, **kwargs):
    # This runs BEFORE the session might be flushed/rotated
    claim_pending_submissions(request, user)
    
    # Reset the Lazy Flow flag so the Middleware knows to guide them
    if request.session.get('pending_review_submission') or request.session.get('pending_property_submission'):
        user.lazy_registration_complete = False
        user.save(update_fields=['lazy_registration_complete'])

@receiver(user_logged_in)
def handle_user_login(sender, request, user, **kwargs):
    # This runs on standard login
    claim_pending_submissions(request, user)