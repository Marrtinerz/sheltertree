# reviews/admin.py

from django.contrib import admin, messages
from django.urls import reverse
from django.utils.html import format_html
from django.utils.translation import ngettext
from django.utils.translation import gettext_lazy as _

from .models import Property, PropertyUnit, Review, PropertyStatus, ReviewStatus

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
    list_display = ('name', 'city', 'country', 'created_at', 'added_by', 'status')
    list_filter = ('status', 'country', 'city')
    search_fields = ('name', 'address', 'google_place_id', 'added_by__username')
    inlines = [PropertyUnitInline]
    readonly_fields = ('name', 'address', 'google_place_id', 'city', 'state', 'postal_code', 'country', 'longitude', 'latitude', 'created_at', 'added_by')

    # --- BULK ACTIONS (from list view) ---

    @admin.action(description=_('Approve selected properties'))
    def make_approved(self, request, queryset):
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
            reviews_to_promote = Review.objects.filter(unit__property=obj, status=ReviewStatus.PENDING_PROPERTY_APPROVAL)
            promoted_review_count = reviews_to_promote.update(status=ReviewStatus.PENDING_CONTENT_REVIEW)
            self.message_user(request, ngettext(
                'The property was approved and %d review has been moved to content moderation.',
                'The property was approved and %d reviews have been moved to content moderation.',
                promoted_review_count
            ) % promoted_review_count, messages.SUCCESS)

        # Case 2: Property just rejected
        elif original_status != PropertyStatus.REJECTED and new_status == PropertyStatus.REJECTED:
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
    readonly_fields = ('created_at', 'unit', 'get_property_link', 'pros', 'cons', 'author', 'security_rating', 'electricity_rating', 'water_rating', 'mobile_network_rating', 'road_network_rating', 'management_rating')
    fields = ('unit', 'get_property_link', 'author', 'security_rating', 'electricity_rating', 'water_rating', 'mobile_network_rating', 'road_network_rating', 'management_rating', 'pros', 'cons', 'status', 'created_at')

    @admin.display(description=_('Parent Property'))
    def get_property_link(self, obj):
        link = reverse("admin:reviews_property_change", args=[obj.unit.property.id])
        return format_html('<a href="{}">{}</a>', link, obj.unit.property.name)

    @admin.action(description=_('Approve selected reviews (content checked)'))
    def approve_reviews(self, request, queryset):
        updated_count = queryset.update(status=ReviewStatus.APPROVED)
        self.message_user(request, ngettext(
            '%d review was successfully approved and is now public.',
            '%d reviews were successfully approved and are now public.',
            updated_count,
        ) % updated_count, messages.SUCCESS)

    @admin.action(description=_('Reject selected reviews (content issue)'))
    def reject_reviews(self, request, queryset):
        updated_count = queryset.update(status=ReviewStatus.REJECTED)
        self.message_user(request, ngettext(
            '%d review was rejected.',
            '%d reviews were rejected.',
            updated_count,
        ) % updated_count, messages.WARNING)


@admin.register(PropertyUnit)
class PropertyUnitAdmin(admin.ModelAdmin):
    list_display = ('unit_identifier', 'get_property_name', 'created_at')
    search_fields = ('property__name', 'unit_identifier')
    readonly_fields = ('created_at',)
    list_display_links = ('unit_identifier',)

    @admin.display(description=_('Parent Property'), ordering='property__name')
    def get_property_name(self, obj):
        return obj.property.name