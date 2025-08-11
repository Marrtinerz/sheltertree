# apps/users/urls.py
from django.urls import path
from .views import OnboardingView, SkipOnboardingView, ProfileView, ProfileEditView

urlpatterns = [
    path('onboarding/', OnboardingView.as_view(), name='onboarding'),
    path('onboarding/skip/', SkipOnboardingView.as_view(), name='onboarding-skip'),
    path('profile/', ProfileView.as_view(), name='account_profile'),
    path('profile/edit/', ProfileEditView.as_view(), name='account_profile_edit'),
]