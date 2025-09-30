# sheltertree_project/settings/production.py
from .base import *
from decouple import config
import dj_database_url

# --- Production-Specific Settings ---

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = config('DEBUG', default=False, cast=bool)

SECRET_KEY = config('DJANGO_SECRET_KEY')
# After: We tell decouple to look for the EXACT environment variable named 'DJANGO_ALLOWED_HOSTS'.
ALLOWED_HOSTS = config('DJANGO_ALLOWED_HOSTS', cast=lambda v: [s.strip() for s in v.split(',')])

DATABASE_URL = config('DATABASE_URL')

# --- DATABASE CONFIGURATION ---
# Use dj-database-url to parse the DATABASE_URL from the environment (e.g., from Render).
# This is cleaner and automatically handles SSL requirements.
DATABASES = {
    'default': dj_database_url.config(
        conn_max_age=600,      # Keep database connections alive for 10 minutes
        ssl_require=True       # Enforce SSL connection to the database for security
    )
}

# --- STATIC FILES & WHITENOISE ---
# This is the correct home for the production staticfiles storage engine.
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'


# --- AWS S3 Media Files Configuration ---
# --- AWS S3 Media Files Configuration ---
AWS_ACCESS_KEY_ID = config('AWS_ACCESS_KEY_ID')
AWS_SECRET_ACCESS_KEY = config('AWS_SECRET_ACCESS_KEY')
AWS_STORAGE_BUCKET_NAME = config('AWS_STORAGE_BUCKET_NAME')
AWS_S3_REGION_NAME = config('AWS_S3_REGION_NAME')
AWS_S3_CUSTOM_DOMAIN = f'{AWS_STORAGE_BUCKET_NAME}.s3.amazonaws.com'
AWS_S3_OBJECT_PARAMETERS = {'CacheControl': 'max-age=86400'}
DEFAULT_FILE_STORAGE = 'storages.backends.s3boto3.S3Boto3Storage'


# --- Enhanced Production Security ---
SECURE_SSL_REDIRECT = True
SECURE_HSTS_SECONDS = 2592000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True


# --- TWILIO PRODUCTION CONFIGURATION ---
TWILIO_ACCOUNT_SID = config('TWILIO_ACCOUNT_SID', default=None)
TWILIO_AUTH_TOKEN = config('TWILIO_AUTH_TOKEN', default=None)
TWILIO_SMS_FROM_NUMBER = config('TWILIO_SMS_FROM_NUMBER', default=None)
TWILIO_WHATSAPP_FROM_NUMBER = config('TWILIO_WHATSAPP_FROM_NUMBER', default=None)


# AFRICASTALKING_API_KEY = config('AFRICASTALKING_API_KEY', default=None)
# AFRICASTALKING_USERNAME = config('AFRICASTALKING_USERNAME', default=None)
# AFRICASTALKING_SENDER_ID = config('AFRICASTALKING_SENDER_ID', default=None)
# AFRICASTALKING_WHATSAPP_NUMBER = config('AFRICASTALKING_WHATSAPP_NUMBER', default=None)


## Zeptoemail provider
# --- EMAIL CONFIGURATION (World-Class Standard) ---
# In production, this should be True to use an encrypted connection.
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_USE_TLS = True
# These settings are loaded securely from your .env file.
EMAIL_HOST = config('EMAIL_HOST')
EMAIL_PORT = config('EMAIL_PORT', cast=int)
EMAIL_HOST_USER = config('EMAIL_HOST_USER')
EMAIL_HOST_PASSWORD = config('EMAIL_HOST_PASSWORD')

# This is the "From" name and address that users will see.
DEFAULT_FROM_EMAIL = config('DEFAULT_FROM_EMAIL') 


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