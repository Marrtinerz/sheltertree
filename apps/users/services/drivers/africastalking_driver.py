from django.conf import settings
import africastalking
import requests
import logging # Import the logging library

# Get a logger instance for this specific file
logger = logging.getLogger(__name__)

# --- SMS Initialization (This remains the same) ---
# try:
#     africastalking.initialize(
#         username=settings.AFRICASTALKING_USERNAME,
#         api_key=settings.AFRICASTALKING_API_KEY
#     )
#     sms_service = africastalking.SMS
# except Exception as e:
#     sms_service = None
#     logger.error(f"Error initializing AfricasTalking SMS SDK: {e}")


def send_sms(to_number, message):
    """Sends an SMS using the AfricasTalking Python SDK."""
    if not sms_service:
        return False, "AfricasTalking SMS SDK not initialized."
    try:
        response = sms_service.send(message, [to_number], settings.AFRICASTALKING_SENDER_ID)
        logger.info(f"AfricasTalking SMS API Response: {response}")
        return True, "Success"
    except Exception as e:
        logger.error(f"AfricasTalking SMS send failed: {e}")
        return False, str(e)


# --- THE UPGRADED WHATSAPP FUNCTION ---
def send_whatsapp(to_number, message):
    """
    Sends a WhatsApp message using the AfricasTalking Chat REST API.
    """
    url = "https://chat.africastalking.com/whatsapp/message/send"
    headers = {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
        'apiKey': settings.AFRICASTALKING_API_KEY,
    }
    payload = {
        "username": settings.AFRICASTALKING_USERNAME,
        "waNumber": settings.AFRICASTALKING_WHATSAPP_NUMBER,
        "phoneNumber": to_number,
        "body": {
            "message": message
        }
    }

    try:
        response = requests.post(url, headers=headers, json=payload, timeout=10)
        
        # --- THE UPGRADE ---
        # Instead of just raising for status, we inspect the status code.
        if response.status_code >= 400:
            # The API itself rejected our request.
            response_data = response.json()
            error_message = response_data.get('error', 'Unknown API error.')
            # Check for a specific, common error
            if "Invalid Phone Number" in error_message:
                return False, "invalid_number" # Return a machine-readable error code
            else:
                return False, f"api_error: {error_message}" # A generic API error

        response_data = response.json()
        message_status = response_data.get('status')
        logger.info(f"AfricasTalking WhatsApp API Response: {response_data}")

        if message_status == 'SENT':
            return True, "Success"
        else:
            return False, f"delivery_failed: {message_status}"
        
    
    except requests.exceptions.RequestException as e:
        logger.error(f"AfricasTalking WhatsApp API Request Failed: {e}")
        return False, "network_error"
    except Exception as e:
        logger.error(f"An unexpected error occurred in send_whatsapp: {e}")
        return False, f"An unexpected error occurred."