from allauth.account.signals import email_confirmed
from django.dispatch import receiver
from apps.notifications.services import notification_service

@receiver(email_confirmed)
def handle_email_confirmation(sender, request, email_address, **kwargs):
    """
    Listens for the signal that a user has successfully confirmed their email.
    This is the trigger to send our beautiful welcome email.
    """
    user = email_address.user
    
    # We can add a check to ensure we only send this once
    # if not user.welcome_email_sent: # (Requires adding a new field to CustomUser)
    
    print(f"INFO: Email confirmed for {user.username}. Sending welcome email.")
    notification_service.send_welcome_email(user)
    
    # user.welcome_email_sent = True
    # user.save(update_fields=['welcome_email_sent'])