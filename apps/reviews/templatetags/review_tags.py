# apps/reviews/templatetags/review_tags.py
from django import template
register = template.Library()

@register.inclusion_tag('reviews/partials/_verification_badge.html')
def verification_badge(review):
    """
    Renders a badge based on the review's historical verification status.
    Now includes a state for unverified authors.
    """
    if review.is_author_phone_verified:
        return {
            "is_verified": True,
            "text": "Verified Reviewer",
            "class": "bg-primary",
            "icon": "fa-check-circle"
        }
    else:
        # --- THE NEW LOGIC ---
        return {
            "is_verified": False,
            "text": "Unverified Reviewer",
            "class": "bg-secondary",
            "icon": "fa-user"
        }

# apps/reviews/templatetags/review_tags.py
@register.simple_tag
def get_rating_insight(score):
    """
    A robust, world-class function that takes any input, safely converts it
    to a score, and returns a dictionary with a label, CSS class, and
    calculated percentage. It can never crash.
    """
    # --- THE CRITICAL FIX: Defensive Programming ---
    try:
        # Attempt to convert the score to a float. This handles numbers,
        # strings of numbers, and gracefully fails on None, '', etc.
        score = float(score)
    except (ValueError, TypeError):
        # If the input is invalid, default to a zero score.
        score = 0.0

    # Calculate the percentage securely
    percentage = (score / 5.0) * 100 if score > 0 else 0

    # The logic for determining the label and class remains the same
    if score >= 4.5:
        insight = {"label": "Excellent", "class": "bg-success"}
    elif score >= 4.0:
        insight = {"label": "Very Good", "class": "bg-primary"}
    elif score >= 3.0:
        insight = {"label": "Good", "class": "bg-info"}
    elif score >= 2.0:
        insight = {"label": "Average", "class": "bg-warning", "text": "text-dark"}
    elif score > 0:
        insight = {"label": "Poor", "class": "bg-danger"}
    else:
        insight = {"label": "No Rating", "class": "bg-light", "text": "text-dark"}
    
    # Add the score and percentage to the dictionary and return it
    insight['score'] = score
    insight['percentage'] = percentage
    return insight
    
    

@register.inclusion_tag('reviews/partials/_rating_bar.html')
def rating_bar(label, score):
    """
    Renders a complete, styled progress bar for a given rating score
    by delegating all logic to the robust `get_rating_insight` function.
    """
    return {
        'label': label,
        # Get the complete insight dictionary from our bulletproof engine
        'insight': get_rating_insight(score)
    }
    

@register.filter
def truncate_address(property):
    """
    A simple filter that calls the get_display_name method with the
    correct argument for list/card views.
    """
    return property.get_display_name(truncate_address=True)