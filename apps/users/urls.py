# apps/users/urls.py
from django.urls import path
from . import views

urlpatterns = [
    path('onboarding/', views.OnboardingView.as_view(), name='onboarding'),
    path('onboarding/skip/', views.SkipOnboardingView.as_view(), name='onboarding-skip'),
    path('profile/', views.ProfileView.as_view(), name='account_profile'),
    path('profile/edit/', views.ProfileEditView.as_view(), name='account_profile_edit'),
    path('phone/add/', views.AddPhoneView.as_view(), name='phone_add'),
    path('phone/verify/', views.VerifyPhoneView.as_view(), name='phone_verify'),
    path('my-contributions/', views.MyContributionsView.as_view(), name='my_contributions'),
]