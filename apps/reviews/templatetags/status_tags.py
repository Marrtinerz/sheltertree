from django import template
from ..models import PropertyStatus, ReviewStatus

register = template.Library()

@register.inclusion_tag('reviews/partials/_status_badge.html')
def status_badge(status):
    """
    Renders a Bootstrap badge with appropriate color and text for a given status.
    This tag is now resilient and handles raw string values for both PropertyStatus and ReviewStatus.
    """
    # --- THE FIX: Create dictionaries from the .choices attributes for a safe lookup ---
    review_status_map = dict(ReviewStatus.choices)
    property_status_map = dict(PropertyStatus.choices)
    
    # First, try to get the human-readable label from the ReviewStatus map.
    text = review_status_map.get(status)
    
    # If the status was not a ReviewStatus, try the PropertyStatus map.
    if text is None:
        text = property_status_map.get(status)

    # If we still haven't found a label (e.g., for an old or unknown status),
    # create a sensible default instead of crashing.
    if text is None:
        text = str(status).replace('_', ' ').title()

    # --- The color logic remains the same, comparing the raw string status value ---
    css_class = 'bg-secondary' # Default color

    # Positive, Final State (Green)
    if status in (PropertyStatus.APPROVED.value, ReviewStatus.APPROVED.value):
        css_class = 'bg-success'
    
    # Neutral / Pending States (Yellow)
    elif status in (PropertyStatus.PENDING_APPROVAL.value, 
                    ReviewStatus.PENDING_PROPERTY_APPROVAL.value,
                    ReviewStatus.PENDING_CONTENT_REVIEW.value,
                    ReviewStatus.UNDER_REVIEW.value):
        css_class = 'bg-warning text-dark'

    # Negative / Rejected / Removed States (Red)
    elif status in (ReviewStatus.REJECTED.value,
                    ReviewStatus.PROPERTY_REJECTED.value,
                    ReviewStatus.USER_DELETED.value,
                    ReviewStatus.ADMIN_REMOVED.value,
                    ReviewStatus.PROPERTY_REMOVED.value):
        css_class = 'bg-danger'

    return {'css_class': css_class, 'text': text}