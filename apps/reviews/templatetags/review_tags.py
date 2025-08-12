# apps/reviews/templatetags/review_tags.py
from django import template
register = template.Library()

@register.inclusion_tag('reviews/partials/_verification_badge.html')
def verification_badge(review):
    """
    Renders a verification badge if the review's author was phone-verified
    at the time the review was written.
    """
    return {'is_verified': review.is_author_phone_verified}