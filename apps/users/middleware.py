# apps/users/middleware.py
from django.shortcuts import redirect
from django.urls import reverse

class OnboardingMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # --- THE FIX: Check for the session key ---
        if (
            request.user.is_authenticated and
            not request.user.onboarding_complete and
            not request.session.get('onboarding_skipped', False) # Check the session!
        ):
            # Add our new 'onboarding-skip' URL to the list of allowed paths
            allowed_paths = [
                reverse('onboarding'),
                reverse('onboarding-skip'), # Add this line
                reverse('account_logout'),
            ]
            if request.path.startswith('/admin/'):
                return self.get_response(request)

            if request.path not in allowed_paths:
                return redirect('onboarding')

        return self.get_response(request)