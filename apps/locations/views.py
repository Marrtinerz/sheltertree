
# In your_app_name/views.py
from django.http import JsonResponse
from .models import State

def get_states(request):
    """
    An API endpoint that returns a list of states for a given country ID.
    """
    country_id = request.GET.get('country_id')
    if not country_id:
        return JsonResponse({'states': []}) # Return empty list if no country_id

    try:
        # Query the database for all states matching the country ID
        states = State.objects.filter(country_id=country_id).values('id', 'name').order_by('name')
        
        # Return the data as a JSON response
        return JsonResponse({'states': list(states)})
    
    except Exception as e:
        # Handle potential errors, e.g., if country_id is not a valid number
        return JsonResponse({'error': str(e)}, status=400)