from django.urls import path
from . import views
from django.views.generic import TemplateView


# This makes it easy to reference these URLs from any app, e.g., 'core:terms_of_service'
app_name = 'core'

urlpatterns = [
    path('terms-of-service/', views.TermsOfServiceView.as_view(), name='terms_of_service'),
    path('privacy-policy/', views.PrivacyPolicyView.as_view(), name='privacy_policy'),
    path('help-center/', views.HelpCenterView.as_view(), name='help_center'),
    path('about/', TemplateView.as_view(template_name='core/about_us.html'), name='about_us'),
    path('contact/', views.FeedbackCreateView.as_view(), name='contact_us'),
    path('contact/success/', TemplateView.as_view(template_name='core/contact_success.html'), name='contact_success'),
]