# In apps/core/admin.py

from django.contrib import admin
from django.utils.translation import gettext_lazy as _
from .models import PlatformFeedback

@admin.register(PlatformFeedback)
class PlatformFeedbackAdmin(admin.ModelAdmin):
    """
    The world-class admin interface for managing user feedback.

    This interface is designed for analysis and insight, not for modification.
    It is therefore read-only by default and optimized for performance.
    """

    # 1. List Display: What you see in the main table.
    # We show the most critical information at a glance.
    list_display = (
        'user',
        'short_feedback', # A custom method for a clean, truncated view.
        'source_url',
        'created_at',
    )

    # 2. Filtering: How you can slice the data.
    # Filtering by date is the most common and useful way to track feedback over time.
    list_filter = (
        'created_at',
    )

    # 3. Search: How you can find specific feedback.
    # We enable searching across the most relevant fields.
    search_fields = (
        'feedback_text',
        'user__username', # Search by the user's name
        'user__email',    # Search by the user's email
        'source_url',     # Find all feedback from a specific page
    )

    # 4. Read-Only Fields: To preserve data integrity.
    # An admin should never edit a user's direct feedback.
    readonly_fields = (
        'user',
        'feedback_text',
        'source_url',
        'created_at',
    )
    
    # 5. Performance Optimization: The mark of a professional.
    # We use `select_related` to prevent hundreds of database queries
    # when fetching the user for each row in the list display (the N+1 problem).
    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        return queryset.select_related('user')

    # 6. Custom Method for a clean list display.
    @admin.display(description=_('Feedback Snippet'))
    def short_feedback(self, obj):
        """
        Returns a truncated version of the feedback text for the list view.
        """
        return (obj.feedback_text[:75] + '...') if len(obj.feedback_text) > 75 else obj.feedback_text

    # --- World-Class UX Enhancement ---
    # We override this method to prevent admins from adding feedback manually,
    # as this data should only ever come from the users themselves.
    def has_add_permission(self, request):
        return False