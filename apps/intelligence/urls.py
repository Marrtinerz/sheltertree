# In apps/intelligence/urls.py
from django.urls import path
from django.views.generic import TemplateView
from .views import SheltertreeIntelligenceLandingPageView

app_name = 'intelligence'

urlpatterns = [
    # This URL is clean, brandable, and provides a clear entry point to the new platform.
    path('', SheltertreeIntelligenceLandingPageView.as_view(), name='landing-page'),

    # The thank-you page remains a necessary part of the flow.
    path('inquiry/thank-you/', TemplateView.as_view(template_name='intelligence/inquiry_thank_you.html'), name='inquiry-thank-you'),
]
