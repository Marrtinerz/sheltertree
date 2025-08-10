# apps/users/urls.py
from django.urls import path
from .views import OnboardingView, SkipOnboardingView

urlpatterns = [
    path('onboarding/', OnboardingView.as_view(), name='onboarding'),
    path('onboarding/skip/', SkipOnboardingView.as_view(), name='onboarding-skip'),
]