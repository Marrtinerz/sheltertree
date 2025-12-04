# apps/users/middleware.py
from datetime import timedelta
from django.shortcuts import redirect
from django.urls import reverse
from apps.reviews.models import Property, Review
from django.utils import timezone

class OnboardingMiddleware:
    """
    Acts as the primary Traffic Controller for user flows.
    
    Responsibilities:
    1. Lazy Registration Intercept: Ensures users who just signed up after 
       submitting a review/property are routed to the success/claim handler.
       Includes logic to prevent redirection loops once the flow is complete.
    2. Onboarding Gatekeeper: Ensures users complete their profile before 
       accessing the main platform (with specific exemptions).
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        
        # ==============================================================================
        # 1. LAZY REGISTRATION INTERCEPT (High Priority)
        # ==============================================================================
        if request.user.is_authenticated:
            # Check the DB flag first (Ultimate Source of Truth)
            if not request.user.lazy_registration_complete:
                
                # Prevent infinite loops if already at handlers
                current_path = request.path
                handler_review_url = reverse('reviews:process-pending-review')
                handler_property_url = reverse('reviews:process-pending-property')
                skip_url = reverse('reviews:lazy-flow-skip') # Whitelist the skip URL!
                
                if current_path in [handler_review_url, handler_property_url, skip_url]:
                    return self.get_response(request)

                # A. Session Check
                if 'pending_review_submission' in request.session:
                    return redirect('reviews:process-pending-review')
                if 'pending_property_submission' in request.session:
                    return redirect('reviews:process-pending-property')
                
                # B. Database Fallback
                if current_path == '/':
                    recent_time = timezone.now() - timedelta(minutes=10) # 10 mins window
                    if Review.objects.filter(author=request.user, created_at__gte=recent_time).exists():
                        return redirect('reviews:process-pending-review')
                    if Property.objects.filter(added_by=request.user, created_at__gte=recent_time).exists():
                        return redirect('reviews:process-pending-property')
                    
                    # If we are here, the user has lazy_registration_complete=False 
                    # BUT no recent content. This is a stale state (e.g., they abandoned 
                    # the flow yesterday). We should auto-complete them to stop the check.
                    # This is a self-healing mechanism.
                    request.user.lazy_registration_complete = True
                    request.user.save(update_fields=['lazy_registration_complete'])

        # ==============================================================================
        # 2. ONBOARDING GATEKEEPER
        # Forces profile completion for authenticated users.
        # ==============================================================================
        if (
            request.user.is_authenticated and
            not request.user.onboarding_complete and
            not request.session.get('onboarding_skipped', False)
        ):
            # --- Whitelist Logic ---
            
            # 1. Admin exemption
            if request.path.startswith('/admin/'):
                return self.get_response(request)

            # 2. Exact Match Exemptions (Auth & Handlers)
            allowed_exact_paths = {
                # Onboarding Control
                reverse('onboarding'),
                reverse('onboarding-skip'),
                
                # Account Management
                reverse('account_logout'),
                reverse('change_signup_email'),
                
                # Phone Verification Flow
                reverse('phone_add'),
                reverse('phone_verify'),
                
                # Lazy Registration Handlers (Must be allowed to run)
                reverse('reviews:process-pending-review'),
                reverse('reviews:process-pending-property'),
                reverse('reviews:lazy-flow-verify'),
                reverse('reviews:lazy-flow-skip'),
                
                
            }

            if request.path in allowed_exact_paths:
                return self.get_response(request)

            # 3. Dynamic Whitelist (Success Pages)
            # Allows users to see the "You're Amazing" / Success page before being gated.
            # Checks if the path contains '/success/' (handles IDs in URLs).
            if '/success/' in request.path:
                return self.get_response(request)
            
            if '/property/add/success/' in request.path:
                return self.get_response(request)

            # --- THE FIX ---
            # Allow the continue handler: /property/12/continue/
            if '/continue/' in request.path and '/property/' in request.path:
                return self.get_response(request)
            
            # Allow the review additions: /add-review/ 
            if '/add-review/' in request.path:
                return self.get_response(request)

            # 4. If not exempt, redirect to Onboarding
            return redirect('onboarding')

        return self.get_response(request)