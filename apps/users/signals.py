from allauth.account.signals import email_confirmed, user_signed_up
from django.dispatch import receiver
from apps.notifications.services import notification_service
from apps.core.event_bus import EventBus

# ==============================================================================
# REUSABLE CORE LOGIC
# ==============================================================================
def _process_welcome_sequence(user, request):
    """
    Checks the user's history. If they haven't received a welcome email yet,
    sends it and marks the flag.
    
    This is the single source of truth.
    """
    # THE GATE: Check the flag. 
    # This prevents sending it again if they change their email later.
    if not user.welcome_email_sent:
        print(f"INFO: Initiating welcome sequence for {user.email}")
        
        # 1. Send the Email
        notification_service.send_welcome_email(user)
        
        # 2. Track the Analytics Event
        # (We check if request exists, as sometimes signals fire outside a request context)
        if request:
            bus = EventBus(request)
            bus.push_event('CompleteRegistration')
        
        # 3. Update the User's Memory
        user.welcome_email_sent = True
        user.save(update_fields=['welcome_email_sent'])
    else:
        print(f"INFO: Welcome email already sent for {user.email}. Skipping.")


# ==============================================================================
# SIGNAL 1: STANDARD SIGNUP (Code Verification)
# ==============================================================================
@receiver(email_confirmed)
def handle_manual_email_confirmation(sender, request, email_address, **kwargs):
    """
    Fires when a user successfully enters the 6-digit code.
    This is the 'Verification' moment for standard users.
    """
    _process_welcome_sequence(email_address.user, request)


# ==============================================================================
# SIGNAL 2: SOCIAL SIGNUP (Google, etc.)
# ==============================================================================
@receiver(user_signed_up)
def handle_social_signup(sender, request, user, **kwargs):
    """
    Fires immediately when a user account is created.
    We check if this is a social login. If so, we treat the trust from Google
    as instant verification and send the welcome email immediately.
    """
    # 'sociallogin' is present in kwargs ONLY for social signups
    social_login = kwargs.get('sociallogin')

    if social_login:
        print(f"INFO: Social login detected for {user.email}. Bypassing manual code verification.")
        _process_welcome_sequence(user, request)