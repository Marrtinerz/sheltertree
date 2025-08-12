# apps/users/adapter.py

from allauth.account.adapter import DefaultAccountAdapter

class MyAccountAdapter(DefaultAccountAdapter):

    def get_login_redirect_url(self, request):
        """
        This method is called after a user successfully logs in.

        We first check for a specific redirect URL that we manually saved
        in the session. This is the most reliable way to handle redirects
        that must survive a complex flow like email confirmation.

        If our specific URL isn't found, we fall back to Allauth's default
        logic, which will use the `next` parameter or the LOGIN_REDIRECT_URL.
        """
        
        # --- THE DEFINITIVE FIX ---
        # Try to retrieve (and remove) our manually saved URL from the session.
        # The .pop() method is ideal here.
        redirect_url = request.session.pop('login_redirect_url', None)
        
        if redirect_url:
            # If we found our URL, use it. This is our highest priority.
            return redirect_url
        
        # If our session variable wasn't there, fall back to the default behavior.
        return super().get_login_redirect_url(request)