import json
from django.conf import settings
from twilio.rest import Client
from twilio.base.exceptions import TwilioRestException
import logging

# Get a logger for this module
logger = logging.getLogger(__name__)

def send_sms(to_number, message):
    """Sends an SMS using the Twilio API."""
    if not all([settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN, settings.TWILIO_SMS_FROM_NUMBER]):
        logger.error("Twilio SMS settings are not fully configured.")
        return False, "service_misconfigured"

    try:
        client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
        client.messages.create(
            body=message,
            from_=settings.TWILIO_SMS_FROM_NUMBER,
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

def send_whatsapp(to_number, code):
    """
    Sends a WhatsApp message using a pre-approved Twilio template.
    
    :param to_number: The recipient's phone number.
    :param code: The verification code (or other variable) to inject into the template.
    :return: A tuple (success_boolean, status_string).
    """
    # Refined settings check to include the Content SID
    if not all([settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN, settings.TWILIO_WHATSAPP_FROM_NUMBER, settings.TWILIO_WHATSAPP_CONTENT_SID]):
        logger.error("Twilio WhatsApp settings are not fully configured.")
        return False, "service_misconfigured"
        
    try:
        client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)

        # World-Class Fix: Build a dictionary and convert to a JSON string.
        content_vars = {
            "1": code
        }

        client.messages.create(
            from_=f"whatsapp:{settings.TWILIO_WHATSAPP_FROM_NUMBER}",
            to=f"whatsapp:{to_number}",
            content_sid=settings.TWILIO_WHATSAPP_CONTENT_SID,
            content_variables=json.dumps(content_vars)
        )
        logger.info(f"Twilio WhatsApp message sent successfully to {to_number}")
        return True, "Success"

    except TwilioRestException as e:
        logger.error(f"Twilio WhatsApp API error for {to_number}: {e}")
        # Updated error checks for production scenarios
        if e.code == 21614: # 'To' number is not a valid WhatsApp number
            return False, "invalid_number"
        if e.code == 63032: # Template has not been approved by WhatsApp/Meta
            return False, "template_not_approved"
        if e.code == 63016: # General failure to send, could be many reasons
            return False, "failed_to_send"
        return False, "api_error"