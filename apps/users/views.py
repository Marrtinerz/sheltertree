# apps/users/views.py
from django.urls import reverse_lazy
from django.views.generic.edit import UpdateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.gis.geoip2 import GeoIP2
from .forms import ProfileCompletionForm
from .models import CustomUser, Country
from django.views import View
from django.shortcuts import redirect

class OnboardingView(LoginRequiredMixin, UpdateView):
    model = CustomUser
    form_class = ProfileCompletionForm
    template_name = 'account/onboarding.html'
    success_url = reverse_lazy('property-list') # Redirect to homepage on success

    def get_object(self):
        # The view operates on the currently logged-in user.
        return self.request.user

    def get_initial(self):
        """Pre-fills the country field based on the user's IP address."""
        initial = super().get_initial()
        try:
            g = GeoIP2()
            # Get IP from request, with a fallback for local dev
            ip = self.request.META.get('REMOTE_ADDR', '1.1.1.1')
            country_data = g.country(ip)
            country_code = country_data.get('country_code')
            if country_code:
                country = Country.objects.filter(code=country_code).first()
                if country:
                    initial['country'] = country
        except Exception:
            # If the IP lookup fails for any reason, just don't pre-fill.
            pass
        return initial

    def form_valid(self, form):
        """When the form is successfully submitted, mark onboarding as complete."""
        user = form.save()
        user.onboarding_complete = True
        user.save()
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