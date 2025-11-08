# reviews/admin.py

from django.contrib import admin, messages
from django.urls import reverse
from django.utils.html import format_html
from django.utils.translation import ngettext
from django.utils.translation import gettext_lazy as _
from apps.notifications.services import notification_service
from .models import Property, PropertyUnit, Review, PropertyStatus, ReviewStatus, Vote

# A constant list of review statuses that are considered "active" and
# should be affected when a parent property is rejected or removed.
ACTIVE_REVIEW_STATUSES = [
    ReviewStatus.PENDING_PROPERTY_APPROVAL,
    ReviewStatus.PENDING_CONTENT_REVIEW,
    ReviewStatus.APPROVED,
]

# --- Inline ModelAdmins ---
class PropertyUnitInline(admin.TabularInline):
    """Allows editing PropertyUnits directly within the Property admin page."""
    model = PropertyUnit
    extra = 1
    fields = ('unit_identifier', 'created_at')
    readonly_fields = ('created_at',)
    ordering = ('-created_at',)


# --- Main ModelAdmins ---

@admin.register(Property)
class PropertyAdmin(admin.ModelAdmin):
    actions = ['make_approved', 'make_rejected', 'make_removed']
    list_display = ('name', 'address', 'status', 'city', 'country', 'created_at', 'added_by')
    list_filter = ('status', 'country', 'city')
    search_fields = ('name', 'address', 'google_place_id', 'added_by__username')
    inlines = [PropertyUnitInline]
    readonly_fields = ('name', 'address', 'google_place_id', 'city', 'state', 'postal_code', 'country', 'longitude', 'latitude', 'created_at', 'added_by')

    # --- BULK ACTIONS (from list view) ---

    @admin.action(description=_('Approve selected properties'))
    def make_approved(self, request, queryset):
        
        # --- THE WORLD-CLASS FIX ---
        # We iterate through the queryset *before* updating to send emails.
        for prop in queryset:
            # We only send a notification if the status is actually changing.
            if prop.status != PropertyStatus.APPROVED:
                notification_service.send_property_approved_email(prop)
        
        updated_count = queryset.update(status=PropertyStatus.APPROVED)
        reviews_to_promote = Review.objects.filter(
            unit__property__in=queryset,
            status=ReviewStatus.PENDING_PROPERTY_APPROVAL
        )
        promoted_review_count = reviews_to_promote.update(status=ReviewStatus.PENDING_CONTENT_REVIEW)
        self.message_user(request, ngettext(
            '%d property was approved and %d associated review was moved to content moderation.',
            '%d properties were approved and %d associated reviews were moved to content moderation.',
            updated_count,
        ) % (updated_count, promoted_review_count), messages.SUCCESS)

    @admin.action(description=_('Reject selected properties'))
    def make_rejected(self, request, queryset):
        # --- THE WORLD-CLASS FIX ---
        for prop in queryset:
            if prop.status != PropertyStatus.REJECTED:
                # For a rejection, it's best practice to provide a generic reason for bulk actions.
                reason = "This submission did not meet our content guidelines."
                notification_service.send_property_rejected_email(prop, reason)
        
        updated_count = queryset.update(status=PropertyStatus.REJECTED)
        reviews_to_reject = Review.objects.filter(
            unit__property__in=queryset,
            status__in=ACTIVE_REVIEW_STATUSES
        )
        rejected_review_count = reviews_to_reject.update(status=ReviewStatus.PROPERTY_REJECTED)
        self.message_user(request, ngettext(
            '%d property was rejected and %d associated active review was also rejected.',
            '%d properties were rejected and %d associated active reviews were also rejected.',
            updated_count,
        ) % (updated_count, rejected_review_count), messages.WARNING)

    @admin.action(description=_('Remove selected properties (e.g., demolished)'))
    def make_removed(self, request, queryset):
        updated_count = queryset.update(status=PropertyStatus.ADMIN_REMOVED)
        reviews_to_remove = Review.objects.filter(
            unit__property__in=queryset,
            status__in=ACTIVE_REVIEW_STATUSES
        )
        removed_review_count = reviews_to_remove.update(status=ReviewStatus.PROPERTY_REMOVED)
        self.message_user(request, ngettext(
            '%d property was removed and %d associated active review was also removed.',
            '%d properties were removed and %d associated active reviews were also removed.',
            updated_count,
        ) % (updated_count, removed_review_count), messages.ERROR)


    # --- INDIVIDUAL SAVE (from detail view) ---

    def save_model(self, request, obj, form, change):
        original_status = None
        if obj.pk:
            try:
                original_status = Property.objects.get(pk=obj.pk).status
            except Property.DoesNotExist:
                pass

        super().save_model(request, obj, form, change)
        new_status = obj.status

        # Case 1: Property just approved
        if original_status != PropertyStatus.APPROVED and new_status == PropertyStatus.APPROVED:
            # --- THE WORLD-CLASS FIX ---
            notification_service.send_property_approved_email(obj)
            
            reviews_to_promote = Review.objects.filter(unit__property=obj, status=ReviewStatus.PENDING_PROPERTY_APPROVAL)
            promoted_review_count = reviews_to_promote.update(status=ReviewStatus.PENDING_CONTENT_REVIEW)
            self.message_user(request, ngettext(
                'The property was approved and %d review has been moved to content moderation.',
                'The property was approved and %d reviews have been moved to content moderation.',
                promoted_review_count
            ) % promoted_review_count, messages.SUCCESS)

        # Case 2: Property just rejected
        elif original_status != PropertyStatus.REJECTED and new_status == PropertyStatus.REJECTED:            
            # --- THE WORLD-CLASS FIX ---
            # In an individual save, you could have a field to type a reason.
            # For now, we'll use a standard reason.
            reason = "This submission did not meet our content guidelines. Please review our policies for more details."
            notification_service.send_property_rejected_email(obj, reason)

            reviews_to_reject = Review.objects.filter(unit__property=obj, status__in=ACTIVE_REVIEW_STATUSES)
            rejected_review_count = reviews_to_reject.update(status=ReviewStatus.PROPERTY_REJECTED)
            self.message_user(request, ngettext(
                'The property was rejected and %d active review was also rejected.',
                'The property was rejected and %d active reviews were also rejected.',
                rejected_review_count
            ) % rejected_review_count, messages.WARNING)

        # Case 3: Property just removed
        elif original_status != PropertyStatus.ADMIN_REMOVED and new_status == PropertyStatus.ADMIN_REMOVED:
            reviews_to_remove = Review.objects.filter(unit__property=obj, status__in=ACTIVE_REVIEW_STATUSES)
            removed_review_count = reviews_to_remove.update(status=ReviewStatus.PROPERTY_REMOVED)
            self.message_user(request, ngettext(
                'The property was removed and %d active review was also removed.',
                'The property was removed and %d active reviews were also removed.',
                removed_review_count
            ) % removed_review_count, messages.ERROR)


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    actions = ['approve_reviews', 'reject_reviews']
    list_display = ('unit', 'get_property_link', 'author', 'status', 'created_at')
    list_display_links = ('unit',)
    list_filter = ('status',)
    search_fields = ('unit__property__name', 'unit__unit_identifier', 'author__username', 'pros', 'cons')
    raw_id_fields = ('unit', 'author')
    readonly_fields = ('created_at', 'get_property_link', 'pros', 'cons', 'author', 'security_rating', 'electricity_rating', 'water_rating', 'mobile_network_rating', 'road_network_rating', 'management_rating', 'flooding_severity')
    fields = ('unit', 'get_property_link', 'author', 'security_rating', 'electricity_rating', 'water_rating', 'mobile_network_rating', 'road_network_rating', 'management_rating', 'pros', 'cons', 'is_author_phone_verified', 'flooding_severity', 'status', 'created_at')

    
    @admin.display(description=_('Parent Property'), ordering='unit__property__name')
    def get_property_link(self, obj):
        """
        Displays a link to the parent property, now using the robust
        get_admin_display_name() method to ensure it's never empty.
        """
        # --- THE CRITICAL FIX IS HERE ---
        # We now call our intelligent helper method instead of the raw .name field.
        display_name = obj.unit.property.get_admin_display_name()
        
        link = reverse("admin:reviews_property_change", args=[obj.unit.property.id])
        return format_html('<a href="{}">{}</a>', link, display_name)

    @admin.action(description=_('Approve selected reviews (content checked)'))
    def approve_reviews(self, request, queryset):
        
        # --- THE WORLD-CLASS FIX ---
        for review in queryset:
            if review.status != ReviewStatus.APPROVED:
                notification_service.send_review_approved_email(review)
                
        updated_count = queryset.update(status=ReviewStatus.APPROVED)
        self.message_user(request, ngettext(
            '%d review was successfully approved and is now public.',
            '%d reviews were successfully approved and are now public.',
            updated_count,
        ) % updated_count, messages.SUCCESS)

    @admin.action(description=_('Reject selected reviews (content issue)'))
    def reject_reviews(self, request, queryset):
        # --- THE WORLD-CLASS FIX ---
        for review in queryset:
            if review.status != ReviewStatus.REJECTED:
                reason = "This review did not meet our content guidelines for clarity and respectfulness."
                notification_service.send_review_rejected_email(review, reason)
        
        updated_count = queryset.update(status=ReviewStatus.REJECTED)
        self.message_user(request, ngettext(
            '%d review was rejected.',
            '%d reviews were rejected.',
            updated_count,
        ) % updated_count, messages.WARNING)
        
    
    def save_model(self, request, obj, form, change):
        """
        Overrides the default save behavior to trigger notifications for
        individual review moderation actions.
        """
        original_status = None
        # 'change' is True if this is an update, False if it's a new object
        if change:
            try:
                # Get the review's status from the database *before* we save the change.
                original_status = Review.objects.get(pk=obj.pk).status
            except Review.DoesNotExist:
                pass # Should not happen in a change view, but good to be safe

        # Save the object first to commit the status change.
        super().save_model(request, obj, form, change)
        new_status = obj.status

        # Case 1: Review was just approved
        if original_status != ReviewStatus.APPROVED and new_status == ReviewStatus.APPROVED:
            notification_service.send_review_approved_email(obj)
            self.message_user(request, "The review was approved, and a notification has been sent to the user.")

        # Case 2: Review was just rejected
        elif original_status != ReviewStatus.REJECTED and new_status == ReviewStatus.REJECTED:
            # You could add a field to the admin form for a custom reason.
            # For now, we use a standard, helpful reason.
            reason = "This review did not meet our content guidelines for clarity and respectfulness."
            notification_service.send_review_rejected_email(obj, reason)
            self.message_user(request, "The review was rejected, and a notification has been sent to the user.", level=messages.WARNING)


@admin.register(PropertyUnit)
class PropertyUnitAdmin(admin.ModelAdmin):
    list_display = ('unit_identifier', 'get_property_name', 'created_at')
    search_fields = ('property__name', 'unit_identifier')
    readonly_fields = ('created_at',)
    list_display_links = ('unit_identifier',)

    @admin.display(description=_('Parent Property'), ordering='property__name')
    def get_property_name(self, obj):
        return obj.property.name
    

@admin.register(Vote)
class UserAdmin(admin.ModelAdmin):
        list_display = ('user', 'review', 'value')