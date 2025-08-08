# reviews/urls.py

from django.urls import path
from . import views

urlpatterns = [
    # --- READ-ONLY VIEWS (for the public) ---
    # The homepage of our site will be the list of all approved properties.
    path('', views.PropertyListView.as_view(), name='property-list'),

    # The detail page for a single approved property.
    path('property/<int:pk>/', views.PropertyDetailView.as_view(), name='property-detail'),


    # --- WRITE/SUBMISSION VIEWS (for logged-in users) ---

    # Journey 1, Step 1: User submits a new property that doesn't exist.
    path('property/add/', views.add_property, name='add-property'),

    # Journey 1, Step 2: The success page shown after property submission.
    path('property/add/success/<int:pk>/', views.add_property_success, name='add-property-success'),

    # Journey 1 (Step 3) & Journey 2: User adds a NEW unit and a review to a property.
    # The property_pk links it to the correct parent property.
    path('property/<int:property_pk>/add-review/', views.add_unit_and_review, name='add-unit-and-review'),

    # Journey 3: User adds a review to an EXISTING unit.
    # This is a placeholder for the view we will build next.
    path('unit/<int:unit_pk>/add-review/', views.add_review_to_unit, name='add-review-to-unit'),
]