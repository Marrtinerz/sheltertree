# apps/users/adapter.py

from allauth.account.adapter import DefaultAccountAdapter
from django.urls import reverse
from django.contrib import messages
from django.utils.translation import gettext_lazy as _
import random
from django.utils.encoding import force_str

class MyAccountAdapter(DefaultAccountAdapter):

    # def get_login_redirect_url(self, request):
    #     """
    #     This method is called after a user successfully logs in.

    #     We first check for a specific redirect URL that we manually saved
    #     in the session. This is the most reliable way to handle redirects
    #     that must survive a complex flow like email confirmation.

    #     If our specific URL isn't found, we fall back to Allauth's default
    #     logic, which will use the `next` parameter or the LOGIN_REDIRECT_URL.
    #     """
        
    #     # --- THE DEFINITIVE FIX ---
    #     # Try to retrieve (and remove) our manually saved URL from the session.
    #     # The .pop() method is ideal here.
    #     redirect_url = request.session.pop('login_redirect_url', None)
        
    #     if redirect_url:
    #         # If we found our URL, use it. This is our highest priority.
    #         return redirect_url
        
    #     # If our session variable wasn't there, fall back to the default behavior.
    #     return super().get_login_redirect_url(request)
    
    def get_password_change_redirect_url(self, request):
        """
        --- THE CRITICAL FIX ---
        The method signature has been corrected to (self, request), which matches
        the parent class in django-allauth. The 'user' argument has been removed.
        
        This method is called by allauth after a password is successfully changed.
        We override it to redirect to the user's profile hub.
        """
        # We can still access the user via request.user if needed, but it's not required here.
        
        # Add a success message that will be displayed on the destination page.
        # messages.success(request, _("Your password has been changed successfully."))
        
        # Return the URL of the profile hub.
        return reverse('account_profile')
    
    def generate_email_verification_code(self):
        """
        Overrides the default alphanumeric code generation to create a
        simple, 6-digit numeric code.
        """
        return str(random.randint(100000, 999999))
    
    def format_email_subject(self, subject):
        """
        Overrides the default subject formatting to remove the site name prefix.
        This gives us full, clean control over our email subject lines.
        """
        # The default adapter adds a "[Site Name]" prefix.
        # Our new, world-class version simply returns the subject as-is.
        return force_str(subject)