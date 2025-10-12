# apps/core/event_bus.py
import json
from django.utils.safestring import mark_safe

class EventBus:
    """
    A simple, session-based event bus for passing backend events
    to the frontend dataLayer. This is a clean, decoupled, world-class pattern.
    """
    SESSION_KEY = '_event_bus_events'

    def __init__(self, request):
        self.session = request.session
        if self.SESSION_KEY not in self.session:
            self.session[self.SESSION_KEY] = []

    def push_event(self, event_name, event_data=None):
        """Adds a new event to the queue."""
        event = {'event': event_name}
        if event_data:
            event.update(event_data)
        self.session[self.SESSION_KEY].append(event)
        self.session.modified = True

    def get_and_clear_events(self):
        """Retrieves all queued events and clears the queue."""
        events = self.session.get(self.SESSION_KEY, [])
        self.session[self.SESSION_KEY] = []
        self.session.modified = True
        return events

    def render_events(self):
        """
        Renders the events into a safe <script> tag for the template.
        """
        events = self.get_and_clear_events()
        if not events:
            return ""
        
        script = f"""
        <script>
            document.addEventListener('DOMContentLoaded', function() {{
                window.dataLayer = window.dataLayer || [];
                const events = {json.dumps(events)};
                events.forEach(event => {{
                    console.log("GA Event Fired:", event);
                    window.dataLayer.push(event);
                }});
            }});
        </script>
        """
        return mark_safe(script)