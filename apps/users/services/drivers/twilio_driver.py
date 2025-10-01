from django.conf import settings
from twilio.rest import Client
from twilio.base.exceptions import TwilioRestException
import logging

# Get a logger for this module
logger = logging.getLogger(__name__)

def send_sms(to_number, message):
    """Sends an SMS using the Twilio API."""
    if not all([settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN, settings.TWILIO_MESSAGING_SERVICE_SID, settings.TWILIO_SMS_FROM_NUMBER]):
        logger.error("Twilio SMS settings are not fully configured.")
        return False, "service_misconfigured"

    try:
        client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
        client.messages.create(
            body=message,
            from_=settings.TWILIO_SMS_FROM_NUMBER,
            messaging_service_sid=settings.TWILIO_MESSAGING_SERVICE_SID,
            to=to_number
        )
        logger.info(f"Twilio SMS sent successfully to {to_number}")
        return True, "Success"
    except TwilioRestException as e:
        logger.error(f"Twilio SMS API error for {to_number}: {e}")
        # Check for a common, user-fixable error
        if e.code == 21211: # Invalid 'To' Phone Number
            return False, "invalid_number"
        return False, "api_error"

def send_whatsapp(to_number, message):
    """Sends a WhatsApp message using the Twilio API."""
    if not all([settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN, settings.TWILIO_MESSAGING_SERVICE_SID, settings.TWILIO_WHATSAPP_FROM_NUMBER]):
        logger.error("Twilio WhatsApp settings are not fully configured.")
        return False, "service_misconfigured"
        
    try:
        client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
        client.messages.create(
            body=message,
            from_=f"whatsapp:{settings.TWILIO_WHATSAPP_FROM_NUMBER}",
            messaging_service_sid=settings.TWILIO_MESSAGING_SERVICE_SID,
            to=f"whatsapp:{to_number}"
        )
        logger.info(f"Twilio WhatsApp message sent successfully to {to_number}")
        return True, "Success"
    except TwilioRestException as e:
        logger.error(f"Twilio WhatsApp API error for {to_number}: {e}")
        # Check for common, user-fixable errors
        if e.code == 63018: # User has not enabled the sandbox or opted in
            return False, "whatsapp_opt_in_required"
        if e.code == 21614: # 'To' number is not a valid WhatsApp number
            return False, "invalid_number"
        return False, "api_error"