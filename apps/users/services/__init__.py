from django.conf import settings
# Import BOTH drivers. This makes switching back in the future even easier.
from .drivers import africastalking_driver, twilio_driver

class NotificationService:
    def send_verification_code(self, user, method='whatsapp'):
        phone_number = user.phone_number
        code = user.phone_verification_code
        message = f"Your ShelterTree Verification Code is {code}."

        # --- THE MIGRATION LOGIC ---
        # The service now intelligently selects the correct driver based on settings.
        if settings.SMS_VENDOR == 'TWILIO':
            driver = twilio_driver
        elif settings.SMS_VENDOR == 'AFRICASTALKING':
            driver = africastalking_driver
        else:
            # Fallback for local development
            print(f"--- MOCK SMS ({method.upper()}) ---")
            print(f"To: {phone_number}")
            print(f"Message: {message}")
            print("-------------------------")
            return True, "Success (Console)"

        if method == 'whatsapp':
            return driver.send_whatsapp(phone_number, code)
        else: # Default to SMS
            return driver.send_sms(phone_number, message)

notification_service = NotificationService()