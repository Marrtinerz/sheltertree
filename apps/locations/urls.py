# apps/locations/urls.py
from django.urls import path
from . import views

urlpatterns = [
    path('api/get-states/', views.get_states, name='get-states'),
]