# reviews/urls.py

from django.urls import path, include
from . import views
from django.views.generic import TemplateView


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
    path('property/add/', views.AddPropertyView.as_view(), name='add-property'),
    path('property/add/success/<int:pk>/', views.add_property_success, name='add-property-success'),
    path('property/<int:property_pk>/add-review/', views.AddUnitAndReviewView.as_view(), name='add-unit-and-review'),
    path('property/unit/<int:unit_pk>/add-review/', views.AddReviewView.as_view(), name='add-review-to-unit'),
    path('review/<int:review_pk>/vote/', views.vote_on_review, name='vote_on_review'),
    path('review/success/<int:review_pk>/', views.ReviewSuccessView.as_view(), name='review_success'),
    path('property/<int:property_pk>/unit-reviews/<int:unit_pk>/', views.get_unit_reviews, name='get_unit_reviews'),
    path('property/<int:property_pk>/search-units/', views.search_units_htmx, name='search_units_htmx'),
    path('property/<int:property_pk>/unit-dropdown/', views.get_unit_dropdown_content, name='get_unit_dropdown'),
    
    
    # --- LOCATIONS ---
    path('', include('apps.locations.urls')),
    
    
    path('features/request-a-review/', views.RequestReviewComingSoonView.as_view(), name='request_review_coming_soon'),
    path('features/request-a-review/success/', TemplateView.as_view(template_name='reviews/coming_soon_success.html'), name='coming_soon_success'),
    
]