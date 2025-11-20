from allauth.account.signals import email_confirmed, user_signed_up
from django.dispatch import receiver
from apps.notifications.services import notification_service
from apps.core.event_bus import EventBus

# --- THE NEW, WORLD-CLASS HANDLER ---
@receiver(email_confirmed)
def handle_first_email_confirmation(sender, request, email_address, **kwargs):
    """
    Listens for the signal that a user has confirmed their email.
    It then checks if a welcome email has already been sent. If not, it sends one
    and sets a flag to prevent it from being sent again.
    """
    user = email_address.user

    # This is the "Gate". We only proceed if the "memory" says we haven't sent it yet.
    if not user.welcome_email_sent:
        print(f"INFO: First email confirmation for {user.username}. Sending welcome email.")
        notification_service.send_welcome_email(user)
        
        # the trigger for the signup funnel in GA.
        bus = EventBus(request)
        bus.push_event('CompleteRegistration')
        
        # This is the crucial step: update the user's "memory".
        user.welcome_email_sent = True
        # Use update_fields for an efficient database query.
        user.save(update_fields=['welcome_email_sent'])
    else:
        print(f"INFO: A subsequent email was confirmed for {user.username}. No welcome email will be sent.")


# --- (Optional but Recommended) Cleanup ---
# This handler is not needed for the welcome email logic. You can remove it
# or keep it for other "on signup" tasks that don't depend on verification.
@receiver(user_signed_up)
def handle_user_signup(sender, request, user, **kwargs):
    """
    Listens for the signal that a new user has signed up.
    This is a great place to create an initial user profile, but not for sending
    a welcome email that should only go out after verification.
    """
    print(f"INFO: New user '{user.username}' has signed up. Their account is created but may not yet be verified.")