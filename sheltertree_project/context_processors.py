# sheltertree_project/context_processors.py
import os
from apps.reviews.forms import PropertySearchForm
from django.conf import settings


def api_keys(request):
    """
    Makes API keys from the environment available in templates.
    """
    return {
        'GOOGLE_MAPS_API_KEY': settings.GOOGLE_MAPS_API_KEY,
        'MAPBOX_ACCESS_TOKEN': settings.MAPBOX_ACCESS_TOKEN,
        'ENABLE_CONSENT_BANNER': settings.ENABLE_CONSENT_BANNER,
        'GOOGLE_ANALYTICS_ID': settings.GOOGLE_ANALYTICS_ID,
    }
    

def global_search_form(request):
    """
    Makes the PropertySearchForm available to all templates.
    """
    return {
        'search_form': PropertySearchForm()
    }