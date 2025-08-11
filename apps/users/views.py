# apps/users/views.py
from django.urls import reverse_lazy
from django.views.generic.edit import UpdateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.gis.geoip2 import GeoIP2
from .forms import OnboardingForm, ProfileEditForm
from .models import CustomUser, Country
from django.views import View
from django.shortcuts import redirect
from django.views.generic import TemplateView
from django.contrib.messages.views import SuccessMessageMixin


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