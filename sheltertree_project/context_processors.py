# sheltertree_project/context_processors.py
import os
from apps.reviews.forms import PropertySearchForm


def api_keys(request):
    """
    Makes API keys from the environment available in templates.
    """
    return {
        'GOOGLE_MAPS_API_KEY': os.environ.get('GOOGLE_MAPS_API_KEY'),
        'MAPBOX_ACCESS_TOKEN': os.environ.get('MAPBOX_ACCESS_TOKEN'),
        'GOOGLE_ANALYTICS_ID': os.environ.get('GOOGLE_ANALYTICS_ID'),
    }
    

def global_search_form(request):
    """
    Makes the PropertySearchForm available to all templates.
    """
    return {
        'search_form': PropertySearchForm()
    }