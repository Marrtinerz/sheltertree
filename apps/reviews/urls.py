# reviews/urls.py

from django.urls import path, include
from . import views


app_name = 'reviews'


urlpatterns = [
    
    # --- CORE PAGES ---
    # The root URL of the site now points to our new HomePageView.
    path('', views.HomePageView.as_view(), name='home'),
    
    
    # --- READ-ONLY VIEWS (for the public) ---
    # The homepage of our site will be the list of all approved properties.
    path('properties/', views.PropertyListView.as_view(), name='property-list'),
    
    # --- SEARCH ---
    path('search/', views.SearchView.as_view(), name='search'),
    path('search/live/', views.live_search_results, name='live-search'),
    
    
    # --- PROPERTY & REVIEW ACTIONS ---
    
    path('property/<int:pk>/', views.PropertyDetailView.as_view(), name='property-detail'),
    path('property/add/', views.add_property, name='add-property'),
    path('property/add/success/<int:pk>/', views.add_property_success, name='add-property-success'),
    path('property/<int:property_pk>/add-review/', views.add_unit_and_review, name='add-unit-and-review'),
    path('unit/<int:unit_pk>/add-review/', views.add_review_to_unit, name='add-review-to-unit'),
    
    
    # --- LOCATIONS ---
    path('', include('apps.locations.urls')),
    
]