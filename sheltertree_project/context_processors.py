# sheltertree_project/context_processors.py
import os

def api_keys(request):
    """
    Makes API keys from the environment available in templates.
    """
    return {
        'GOOGLE_MAPS_API_KEY': os.environ.get('GOOGLE_MAPS_API_KEY'),
        'MAPBOX_ACCESS_TOKEN': os.environ.get('MAPBOX_ACCESS_TOKEN'),
    }