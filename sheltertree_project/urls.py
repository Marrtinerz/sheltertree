"""
sheltertree_project URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/stable/topics/http/urls/

This is the main entry point for all URLs. It does two things:
1.  Routes the /admin/ URL to the Django admin site.
2.  Includes all other URLs from our 'reviews' application, and prefixes them
    with a language code (e.g., /en/, /fr/) to enable internationalization.
"""
from django.conf import settings
from django.contrib import admin
from django.urls import path, include
from django.conf.urls.i18n import i18n_patterns
from django.contrib.auth import views as auth_views
from django.conf.urls.static import static
from django.views.generic import TemplateView


# --- Error Handlers for Project-Level Templates ---
# This is the correct way to point Django's error handling system
# to your templates located in the root 'templates/' directory.
# The .as_view() method creates a view instance on the fly.
handler404 = TemplateView.as_view(template_name='errors/404.html')
handler500 = TemplateView.as_view(template_name='errors/500.html')


# --- URL patterns that should NOT be translated ---
# This should typically only include the admin panel.
urlpatterns = [
    # Your obscured admin URL
    path('tree-root/', admin.site.urls),
]


# --- URL patterns that SHOULD be translated and prefixed ---
# This includes ALL user-facing pages: authentication, core pages, reviews, etc.
# By placing everything inside, we ensure consistent URL behavior.
urlpatterns += i18n_patterns(
    # Authentication URLs
    path('accounts/', include('allauth.urls')),
    path('accounts/', include('apps.users.urls')),

    # Your user-facing application URLs
    path('', include('apps.core.urls')),
    path('', include('apps.reviews.urls')),

    # This setting is the key to removing '/en/' from your default language URLs.
    prefix_default_language=False
)

# --- Add this to the end of the file ---
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)