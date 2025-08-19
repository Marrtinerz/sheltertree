# sheltertree_project/settings/production.py
from .base import *
from decouple import config

# --- Production-Specific Settings ---

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = config('DEBUG', default=False, cast=bool)

# The SECRET_KEY MUST be set in the production environment.
SECRET_KEY = config('SECRET_KEY')

# Set your domain names here. Decouple can parse a comma-separated string.
ALLOWED_HOSTS = config('ALLOWED_HOSTS', cast=lambda v: [s.strip() for s in v.split(',')])


# --- Enhanced Production Security ---
SECURE_SSL_REDIRECT = config('SECURE_SSL_REDIRECT', default=True, cast=bool)
SECURE_HSTS_SECONDS = 2592000  # 30 days
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True


# --- TWILIO PRODUCTION CONFIGURATION ---
TWILIO_ACCOUNT_SID = config('TWILIO_ACCOUNT_SID', default=None)
TWILIO_AUTH_TOKEN = config('TWILIO_AUTH_TOKEN', default=None)
TWILIO_SMS_FROM_NUMBER = config('TWILIO_FROM_NUMBER', default=None)
TWILIO_WHATSAPP_FROM_NUMBER = config('TWILIO_WHATSAPP_FROM_NUMBER', default=None)


AFRICASTALKING_API_KEY = config('AFRICASTALKING_API_KEY', default=None)
AFRICASTALKING_USERNAME = config('AFRICASTALKING_USERNAME', default=None)
AFRICASTALKING_SENDER_ID = config('AFRICASTALKING_SENDER_ID', default=None)
AFRICASTALKING_WHATSAPP_NUMBER = config('AFRICASTALKING_WHATSAPP_NUMBER', default=None)



# --- Logging ---
# A basic logging setup that prints to the console, ideal for Docker/containerized environments.
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
        },
    },
    'root': {
        'handlers': ['console'],
        'level': 'WARNING',
    },
}