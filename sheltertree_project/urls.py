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


# URLs that should NOT be translated or prefixed with a language code.
# The admin interface is a primary example.
urlpatterns = [
    path('admin/', admin.site.urls),
    path('accounts/', include('allauth.urls')),
    path('accounts/', include('apps.users.urls')),
    
]
urlpatterns += i18n_patterns(
    # This line tells Django to look at the `reviews/urls.py` file
    # for any URL that isn't handled above.
    path('', include('apps.core.urls')),
    path('', include('apps.reviews.urls')),
    # The login URL is needed so Django knows where to redirect unauthenticated users
    

    # If you add more apps in the future, you would include their URLs here too.
    # path('another-app/', include('another_app.urls')),
)

# We can use TemplateView directly because these are simple pages.
handler404 = TemplateView.as_view(template_name='errors/404.html')
handler500 = TemplateView.as_view(template_name='errors/500.html')






# --- Add this to the end of the file ---
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)