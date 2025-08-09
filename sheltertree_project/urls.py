"""
sheltertree_project URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/stable/topics/http/urls/

This is the main entry point for all URLs. It does two things:
1.  Routes the /admin/ URL to the Django admin site.
2.  Includes all other URLs from our 'reviews' application, and prefixes them
    with a language code (e.g., /en/, /fr/) to enable internationalization.
"""
from django.contrib import admin
from django.urls import path, include
from django.conf.urls.i18n import i18n_patterns
from django.contrib.auth import views as auth_views

# URLs that should NOT be translated or prefixed with a language code.
# The admin interface is a primary example.
urlpatterns = [
    path('admin/', admin.site.urls),
]
urlpatterns += i18n_patterns(
    # This line tells Django to look at the `reviews/urls.py` file
    # for any URL that isn't handled above.
    path('', include('apps.reviews.urls')),
    path('', include('apps.locations.urls')),
    # The login URL is needed so Django knows where to redirect unauthenticated users
    path('login/', auth_views.LoginView.as_view(template_name='reviews/login.html'), name='login'), # Assuming you have a login template
    
    # This is the line that fixes your error.
    # It tells Django to use its built-in LogoutView for the /logout/ URL.
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),

    # If you add more apps in the future, you would include their URLs here too.
    # path('another-app/', include('another_app.urls')),
)