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

# INSTALLED_APPS = ['whitenoise.runserver_nostatic'] + [app for app in INSTALLED_APPS if app != 'whitenoise']
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

SKIP_APPROVAL_EMAIL_SEND = config('SKIP_APPROVAL_EMAIL_SEND', default=False, cast=bool)
SKIP_REVIEW_EMAIL_SEND = config('SKIP_REVIEW_EMAIL_SEND', default=False, cast=bool)


# --- EMAIL CONFIGURATION (World-Class Standard) ---
# In production, this should be True to use an encrypted connection.
EMAIL_USE_TLS = True

# These settings are loaded securely from your .env file.
EMAIL_HOST = config('EMAIL_HOST')
EMAIL_PORT = config('EMAIL_PORT', cast=int)
EMAIL_HOST_USER = config('EMAIL_HOST_USER')
EMAIL_HOST_PASSWORD = config('EMAIL_HOST_PASSWORD')

# This is the "From" name and address that users will see.
DEFAULT_FROM_EMAIL = config('DEFAULT_FROM_EMAIL')


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
