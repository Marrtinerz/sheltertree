# apps/users/adapter.py

from datetime import timedelta
from allauth.account.adapter import DefaultAccountAdapter
from django.urls import reverse
from django.contrib import messages
from django.utils.translation import gettext_lazy as _
import random
from django.utils.encoding import force_str
from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from allauth.core.exceptions import ImmediateHttpResponse
from django.shortcuts import redirect
from django.contrib.auth import get_user_model
from django.utils import timezone
from apps.reviews.models import Review, Property

class MyAccountAdapter(DefaultAccountAdapter):

    def get_login_redirect_url(self, request):
        # print("DEBUG: get_login_redirect_url called")
        smart_url = self._get_smart_redirect(request, request.user)
        if smart_url:
            # print(f"DEBUG: Redirecting to {smart_url}")
            return smart_url
        # print("DEBUG: Falling back to default login redirect")
        return super().get_login_redirect_url(request)

    def get_email_verification_redirect_url(self, email_address):
        # print("DEBUG: get_email_verification_redirect_url called")
        request = self.request 
        # email_address.user is the user instance associated with the email
        user = email_address.user
        # print(f"DEBUG: User is {user}")

        smart_url = self._get_smart_redirect(request, user)
        if smart_url:
            # print(f"DEBUG: Redirecting to {smart_url}")
            return smart_url
        
        # print("DEBUG: Falling back to default email verification redirect")
        return super().get_email_verification_redirect_url(email_address)

    def _get_smart_redirect(self, request, user):
        """
        Intelligent redirection.
        """
        # 0. EXIT EARLY if flow is already complete
        if user and hasattr(user, 'lazy_registration_complete') and user.lazy_registration_complete:
            # print("DEBUG: User has already completed lazy flow. Ignoring recent content.")
            return None

        # 1. Session Check (Fastest)
        if request and 'pending_review_submission' in request.session:
            # print("DEBUG: Found pending_review_submission in session")
            return reverse('reviews:process-pending-review')
        if request and 'pending_property_submission' in request.session:
            # print("DEBUG: Found pending_property_submission in session")
            return reverse('reviews:process-pending-property')

        # 2. Database Fallback (No Time Limit)
        # We simply check if this user has authored ANY content recently.
        if user:
            # print(f"DEBUG: Checking DB for user {user.pk}")
            
            # Check for ANY review by this author (We assume the most recent is the one)
            # We sort by ID desc to get the latest.
            latest_review = Review.objects.filter(author=user).order_by('-id').first()
            if latest_review:
                # print(f"DEBUG: Found review {latest_review.pk} for user")
                return reverse('reviews:process-pending-review')
            
            # Check for ANY property
            latest_prop = Property.objects.filter(added_by=user).order_by('-id').first()
            if latest_prop:
                # print(f"DEBUG: Found property {latest_prop.pk} for user")
                return reverse('reviews:process-pending-property')
            
            # print("DEBUG: No reviews or properties found for user in DB")

        return None

    # ... (Keep generate_email_verification_code and format_email_subject as is) ...
    def generate_email_verification_code(self):
        return str(random.randint(100000, 999999))
    
    def format_email_subject(self, subject):
        return force_str(subject)
    

class CustomSocialAccountAdapter(DefaultSocialAccountAdapter):
    def pre_social_login(self, request, sociallogin):
        """
        This method is called right after a user successfully authenticates
        with a social provider, but before the login process is finalized.
        It's our chance to intervene.
        """
        user = sociallogin.user

        if user.pk:
            return

        try:
            # --- CORRECTED CALL ---
            # We call the imported get_user_model() function directly, not as a method of self.
            User = get_user_model()
            existing_user = User.objects.get(email__iexact=user.email)

            # If we find an existing user, we stop the signup process.
            messages.error(request, _(
                "An account with this email address already exists. "
                "Please log in with your password to connect your Google account."
            ))
            raise ImmediateHttpResponse(redirect(reverse('account_login')))

        # --- CORRECTED CALL ---
        except get_user_model().DoesNotExist:
            # If no user with this email exists, the signup can proceed as normal.
            pass