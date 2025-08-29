# apps/users/views.py
from django.urls import reverse_lazy
from django.views.generic.edit import UpdateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.gis.geoip2 import GeoIP2
from .forms import OnboardingForm, ProfileEditForm, PhoneNumberForm, PhoneVerificationCodeForm
from .models import CustomUser, Country
from django.views import View
from django.shortcuts import redirect
from django.views.generic import TemplateView
from django.contrib.messages.views import SuccessMessageMixin
from django.contrib import messages
from django.views.generic.edit import FormView
from twilio.rest import Client
from django.utils import timezone
from django.conf import settings
import random
from .services import notification_service
from django.db.models import F
from datetime import timedelta
from apps.reviews.models import Review, Property
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger

class ProfileView(LoginRequiredMixin, TemplateView):
    template_name = 'account/profile_hub.html'
    
class ProfileEditView(LoginRequiredMixin, SuccessMessageMixin, UpdateView):
    model = CustomUser
    form_class = ProfileEditForm
    template_name = 'account/profile_edit_form.html'
    success_url = reverse_lazy('account_profile') # Redirect back to the hub on success
    success_message = "Your profile has been updated successfully."

    def get_object(self):
        # Ensure the view operates on the currently logged-in user.
        return self.request.user

class OnboardingView(LoginRequiredMixin, UpdateView):
    model = CustomUser
    form_class = OnboardingForm
    template_name = 'account/onboarding.html'
    success_url = reverse_lazy('reviews:property-list')

    def get_object(self):
        """
        --- THIS IS THE DEFINITIVE FIX ---
        This method is called first to fetch the object that the form will be bound to.
        We fetch the user from the request, and if their `user_type` is not yet set,
        we modify the object in memory *before* it is passed to the form.
        """
        user = self.request.user
        
        # If the user is just starting onboarding, their user_type will be blank.
        if not user.user_type:
            # Set the default value on the in-memory user object.
            # This ensures the form's dropdown will be pre-selected with 'Renter'.
            user.user_type = CustomUser.UserType.RENTER
            
        return user

    def get_initial(self):
        """
        This method provides initial values for unbound form fields. It runs *after*
        get_object. We use it here to pre-fill the country based on the user's IP address,
        as this is new information not present on the user object itself.
        """
        initial = super().get_initial()
        
        # Check if the country is not already set on the user instance
        if not self.object.country:
            try:
                g = GeoIP2()
                # Get IP from request, with a fallback for local development
                ip = self.request.META.get('REMOTE_ADDR', '1.1.1.1')
                country_data = g.country(ip)
                country_code = country_data.get('country_code')
                
                if country_code:
                    country = Country.objects.filter(code=country_code).first()
                    if country:
                        # This will pre-select the country dropdown
                        initial['country'] = country.pk
            except Exception:
                # If the IP lookup fails for any reason (e.g., local IP, GeoIP DB missing),
                # we just don't pre-fill the field. The user can select it manually.
                pass
                
        return initial
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # This is now the single source of truth for which sprites are available.
        context['sprite_options'] = [
            "Bee", "Bloom", "Dog", "Cat", "Dove", "Butterfly", 
            "Yellow_flower", "Rabbit", "Gardenia", "Small_kitten", 
            "Bull_dog", "Yellow_flower2"
        ]
        
        return context

    def form_valid(self, form):
        """
        When the form is successfully submitted, mark onboarding as complete.
        """
        user = form.save(commit=False) # Use commit=False to modify before final save
        user.onboarding_complete = True
        user.save()
        
        # The parent form_valid handles the redirect to success_url
        return super().form_valid(form)
    

class SkipOnboardingView(LoginRequiredMixin, View):
    """
    Sets a session flag to indicate the user has chosen to skip the
    onboarding process for their current session.
    """
    def get(self, request, *args, **kwargs):
        # Set a key in the user's session
        request.session['onboarding_skipped'] = True
        # Redirect them to the homepage (or wherever you want them to go)
        return redirect('reviews:property-list')


# The Full, Updated AddPhoneView
# ==============================================================================
class AddPhoneView(LoginRequiredMixin, FormView):
    form_class = PhoneNumberForm
    template_name = 'account/phone_add_form.html'
    success_url = reverse_lazy('phone_verify')

    def get_form_kwargs(self):
        """
        --- THIS IS THE FIX ---
        This method passes keyword arguments to the form's __init__ method.
        We add the current user to the kwargs so the form can access it.
        """
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    def dispatch(self, request, *args, **kwargs):
        # The rate-limiting logic here is correct and should remain.
        if not request.user.can_request_new_code():
            messages.error(request, "Please wait at least 60 seconds before requesting a new verification code.")
            return redirect('account_profile')
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        # The rest of your form_valid logic is already world-class and does not need to change.
        user = self.request.user
        phone_number = form.cleaned_data['phone_number_e164']
        method = self.request.POST.get('method', 'whatsapp')

        user.generate_phone_verification_code(phone_number)

        success, message_code = notification_service.send_verification_code(user, method)
        
        if success:
            messages.info(self.request, "A verification code has been sent. Please check your messages.")
            return super().form_valid(form)
        else:
            if message_code == "invalid_number":
                form.add_error('phone_number', "The phone number you entered does not appear to be valid. Please check the number and try again.")
            else:
                messages.error(self.request, "We could not send a verification code due to a technical issue. Please try again in a few moments.")
            
            return self.form_invalid(form)
    
# The updated, more robust view
MAX_VERIFICATION_ATTEMPTS = 5
LOCKOUT_DURATION_MINUTES = 15

class VerifyPhoneView(LoginRequiredMixin, FormView):
    """
    Handles the second and final step of phone verification: submitting the code.

    This view is designed with a world-class standard of security and user experience:
    1.  **Brute-Force Protection:** Locks a user out after too many failed attempts.
    2.  **Graceful Error Handling:** On a wrong code, it re-renders the page with an
        error message instead of redirecting, allowing the user to try again.
    3.  **Clean Architecture:** Delegates validation logic to the form and state-change
        logic to the model, keeping the view lean and focused on flow control.
    """
    form_class = PhoneVerificationCodeForm
    template_name = 'account/phone_verify_form.html'

    def get_form_kwargs(self):
        """
        Passes the 'request' object to the form's __init__ method. This is
        crucial so the form can access the currently logged-in user for validation.
        """
        kwargs = super().get_form_kwargs()
        kwargs['request'] = self.request
        return kwargs

    def get_context_data(self, **kwargs):
        """
        Adds extra context to the template to improve the user experience.
        """
        context = super().get_context_data(**kwargs)
        # Calculate and pass the number of remaining attempts to the template.
        remaining_attempts = MAX_VERIFICATION_ATTEMPTS - self.request.user.phone_verification_attempts
        context['remaining_attempts'] = remaining_attempts
        return context

    def dispatch(self, request, *args, **kwargs):
        """
        This method runs before any other view logic. It acts as a security
        gatekeeper to check if the user is currently locked out.
        """
        user = request.user
        
        # Security Check: Is the user currently in a lockout period?
        if user.phone_lockout_until and timezone.now() < user.phone_lockout_until:
            lockout_ends = user.phone_lockout_until.strftime("%-I:%M %p")
            messages.error(request, f"Too many failed attempts. For security, please try again after {lockout_ends}.")
            return redirect('account_profile')
            
        return super().dispatch(request, *args, **kwargs)

    def form_invalid(self, form):
        """
        This method is called automatically when form.is_valid() fails, which
        in our design means the verification code was incorrect or expired.
        This is where we handle the attempt counting and lockout logic.
        """
        user = self.request.user
        
        # Increment the attempt counter in the database.
        user.phone_verification_attempts += 1
        
        # Check if this failed attempt has triggered a lockout.
        if user.phone_verification_attempts >= MAX_VERIFICATION_ATTEMPTS:
            user.phone_lockout_until = timezone.now() + timedelta(minutes=LOCKOUT_DURATION_MINUTES)
            messages.error(self.request, f"Maximum attempts reached. You have been locked out for {LOCKOUT_DURATION_MINUTES} minutes.")
        
        user.save(update_fields=['phone_verification_attempts', 'phone_lockout_until'])
        
        # Re-render the page with the validation error messages from the form.
        return super().form_invalid(form)

    def form_valid(self, form):
        """
        Handles successful code entry. This now includes an immediate check
        for recent, already-approved reviews.
        """
        user = self.request.user

        # --- THE IMMEDIATE CHECK ---
        # First, check if the user is currently unverified. This ensures this logic
        # only runs once, during their first successful verification.
        if not user.is_phone_verified:
            
            # Define the time window for the retroactive update.
            grace_period_start_time = timezone.now() - timedelta(
                hours=settings.REVIEW_VERIFICATION_GRACE_PERIOD_HOURS
            )
            
            # Find all of this user's RECENT reviews that are ALREADY APPROVED
            # and do not yet have the verified badge.
            reviews_to_update = Review.objects.filter(
                author=user,
                is_author_phone_verified=False,
                created_at__gte=grace_period_start_time,
                # This is the crucial new filter for this view:
                unit__property__status='APPROVED' # Adjust to your 'APPROVED' status value
            )
            
            if reviews_to_update.exists():
                updated_count = reviews_to_update.update(is_author_phone_verified=True)
                messages.success(self.request, f"Your new 'Verified' badge has been applied to {updated_count} of your recent, approved reviews!")

        # --- END OF IMMEDIATE CHECK ---

        # The original logic to finalize the user's status remains.
        user.mark_phone_as_verified()
        
        messages.success(self.request, "Your phone number has been successfully verified!")
        
        # Redirect to the original destination or profile.
        success_url = self.request.session.pop('next_url', reverse_lazy('account_profile'))
        return redirect(success_url)
    

# Define pagination settings in one place
ITEMS_PER_PAGE = 5

class MyContributionsView(LoginRequiredMixin, TemplateView):
    template_name = 'account/my_contributions.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user

        # --- REVIEWS PAGINATION (Unchanged) ---
        all_reviews_list = Review.objects.filter(author=user).select_related(
            'unit__property'
        ).order_by('-created_at')
        review_paginator = Paginator(all_reviews_list, ITEMS_PER_PAGE)
        review_page_number = self.request.GET.get('review_page')
        context['reviews'] = review_paginator.get_page(review_page_number)

        # --- PROPERTIES PAGINATION (Unchanged) ---
        all_properties_list = Property.objects.filter(added_by=user).order_by('-created_at')
        property_paginator = Paginator(all_properties_list, ITEMS_PER_PAGE)
        property_page_number = self.request.GET.get('property_page')
        context['properties'] = property_paginator.get_page(property_page_number)
            
        # --- THE CRITICAL FIX ---
        # Determine which tab should be active based on the URL query parameters.
        # If 'property_page' is in the URL, the properties tab should be active.
        # Otherwise, default to the reviews tab.
        if 'property_page' in self.request.GET:
            context['active_tab'] = 'properties'
        else:
            context['active_tab'] = 'reviews'

        return context