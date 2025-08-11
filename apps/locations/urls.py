# apps/locations/urls.py
from django.urls import path
from . import views


app_name = 'locations'

urlpatterns = [
    path('api/get-states/', views.get_states, name='get-states'),
]