# apps/core/templatetags/event_tags.py
from django import template
from ..event_bus import EventBus

register = template.Library()

@register.simple_tag(takes_context=True)
def render_analytics_events(context):
    """
    Renders all queued analytics events from the EventBus into a script tag.
    """
    request = context.get('request')
    if not request:
        return ""
    
    bus = EventBus(request)
    return bus.render_events()