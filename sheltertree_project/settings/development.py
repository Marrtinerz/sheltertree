# sheltertree_project/settings/development.py
from .base import *
from decouple import config

# --- Development-Specific Settings ---

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = config('DEBUG', default=True, cast=bool)

# SECURITY WARNING: keep the secret key used in production secret!
# For development, we can use a simpler key from our .env file.
SECRET_KEY = config('SECRET_KEY')

# Allow requests from localhost and the Docker container's IP
ALLOWED_HOSTS = ['localhost', '127.0.0.1']


EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

# Optional: Add Django Debug Toolbar for a huge development boost
# INSTALLED_APPS += ['debug_toolbar']
# MIDDLEWARE += ['debug_toolbar.middleware.DebugToolbarMiddleware']
# INTERNAL_IPS = ['127.0.0.1']

# --- TWILIO PRODUCTION CONFIGURATION ---
TWILIO_ACCOUNT_SID = config('TWILIO_ACCOUNT_SID', default=None)
TWILIO_AUTH_TOKEN = config('TWILIO_AUTH_TOKEN', default=None)
TWILIO_SMS_FROM_NUMBER = config('TWILIO_SMS_FROM_NUMBER', default=None)
TWILIO_WHATSAPP_FROM_NUMBER = config('TWILIO_WHATSAPP_FROM_NUMBER', default=None)


# AfricasTalking Settings
AFRICASTALKING_API_KEY = config('AFRICASTALKING_API_KEY', default=None)
AFRICASTALKING_USERNAME = config('AFRICASTALKING_USERNAME', default=None)
AFRICASTALKING_SENDER_ID = config('AFRICASTALKING_SENDER_ID', default=None)
AFRICASTALKING_WHATSAPP_NUMBER = config('AFRICASTALKING_WHATSAPP_NUMBER', default=None)