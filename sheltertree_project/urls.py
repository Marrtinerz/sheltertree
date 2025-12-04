"""
sheltertree_project URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/stable/topics/http/urls/

This is the main entry point for all URLs. It does two things:
1.  Routes the /admin/ URL (obscured as /tree-root/) to the Django admin site.
2.  Includes all other URLs from our applications, and prefixes them
    with a language code (e.g., /en/, /fr/) to enable internationalization.
"""
from django.conf import settings
from django.contrib import admin
from django.urls import path, include
from django.conf.urls.i18n import i18n_patterns
from django.conf.urls.static import static
from django.views.generic import TemplateView


# --- Error Handlers for Project-Level Templates ---
# This points Django's error handling system to your custom templates.
handler404 = TemplateView.as_view(template_name='errors/404.html')
handler500 = TemplateView.as_view(template_name='errors/500.html')


# ==============================================================================
# 1. NON-TRANSLATED URLS (Admin, API, Webhooks)
# These URLs should NOT have a language prefix.
# ==============================================================================
urlpatterns = [
    # Security: Obscured admin URL for production safety
    path('tree-root/', admin.site.urls),
]


# ==============================================================================
# 2. TRANSLATED URLS (User-Facing Pages)
# These URLs will automatically support language prefixes (e.g., /fr/about/).
# prefix_default_language=False ensures the default language (English) 
# does NOT have a prefix (e.g., just /about/, not /en/about/).
# ==============================================================================
urlpatterns += i18n_patterns(
    # --- Authentication (Allauth & User Management) ---
    path('accounts/', include('allauth.urls')),
    path('accounts/', include('apps.users.urls')),

    # --- Core Application (Home, Contact, Feedback) ---
    path('', include('apps.core.urls')),

    # --- Reviews Application (Main Product) ---
    path('', include('apps.reviews.urls')),

    # --- Intelligence Platform (Paid Reports) ---
    path('intelligence/', include('apps.intelligence.urls', namespace='intelligence')),

    # --- Careers & Hiring ---
    path('careers/', include('apps.careers.urls', namespace='careers')),

    # Configuration for i18n_patterns
    prefix_default_language=False
)


# ==============================================================================
# 3. DEVELOPMENT-ONLY URLS
# ==============================================================================
if settings.DEBUG:
    # Serve user-uploaded media files in development
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    
    # Optional: Serve static files (CSS/JS) explicitly if runserver doesn't catch them
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)