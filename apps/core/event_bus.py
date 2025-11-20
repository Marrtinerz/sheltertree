# apps/core/event_bus.py
import json
from django.utils.safestring import mark_safe

class EventBus:
    """
    A simple, session-based event bus for passing backend events to frontend
    analytics services like Google Tag Manager and the Meta Pixel. This is the
    single source of truth for conversion tracking.
    """
    SESSION_KEY = '_event_bus_events'

    def __init__(self, request):
        self.session = request.session
        if self.SESSION_KEY not in self.session:
            self.session[self.SESSION_KEY] = []

    def push_event(self, event_name, event_data=None):
        """
        Adds a new event to the queue.
        :param event_name: The name of the event (e.g., 'Lead', 'CompleteRegistration').
        :param event_data: A dictionary of additional data (e.g., {'value': 10.00, 'currency': 'USD'}).
        """
        # For Google Tag Manager, the event name is part of the dictionary.
        google_event = {'event': event_name}
        if event_data:
            google_event.update(event_data)
        
        # For Facebook, the event name and data are separate. We store them together.
        fb_event = {'name': event_name, 'data': event_data or {}}

        # Store a tuple containing both formats to avoid re-processing later.
        self.session[self.SESSION_KEY].append((google_event, fb_event))
        self.session.modified = True

    def get_and_clear_events(self):
        """Retrieves all queued events and clears the queue."""
        events = self.session.get(self.SESSION_KEY, [])
        if events:
            self.session[self.SESSION_KEY] = []
            self.session.modified = True
        return events

    def render_events(self):
        """
        Renders the events into a safe <script> tag for the template.
        This method is the bridge between our Django backend and frontend analytics.
        """
        events = self.get_and_clear_events()
        if not events:
            return ""
        
        script_lines = ["<script>"]
        
        for google_event, fb_event in events:
            # 1. Google Tag Manager dataLayer Push
            # This is the universal format that GTM listens for.
            script_lines.append(f"window.dataLayer = window.dataLayer || [];")
            script_lines.append(f"window.dataLayer.push({json.dumps(google_event)});")

            # 2. Meta (Facebook) Pixel fbq Call
            # We call fbq directly for maximum reliability.
            event_name = fb_event['name']
            event_data_json = json.dumps(fb_event['data'])
            
            # The 'if (typeof fbq...)' is a world-class safety check. It ensures
            # the site doesn't crash if an ad blocker stops the pixel from loading.
            if fb_event['data']:
                # Event with parameters (e.g., for a future Purchase event)
                script_lines.append(f"if (typeof fbq === 'function') {{ fbq('track', '{event_name}', {event_data_json}); }}")
            else:
                # Event without parameters (like 'Lead' or 'CompleteRegistration')
                script_lines.append(f"if (typeof fbq === 'function') {{ fbq('track', '{event_name}'); }}")
        
        script_lines.append("</script>")
        
        return mark_safe("\n".join(script_lines))