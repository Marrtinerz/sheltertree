# sheltertree_project/settings/production.py

from .base import *
from decouple import config
import dj_database_url

# --- CORE PRODUCTION SETTINGS ---

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = config('DEBUG', default=False, cast=bool)

# For the build process, we provide a dummy key. The REAL key will be
# provided by the Render environment when the app is running.
SECRET_KEY = config('SECRET_KEY', default='dummy-secret-key-for-build-process')

# Decouple will parse a comma-separated string from the environment variable.
# For the build process, we can use a harmless default.
ALLOWED_HOSTS = config('ALLOWED_HOSTS', default='localhost,127.0.0.1', cast=lambda v: [s.strip() for s in v.split(',')])


# --- DATABASE CONFIGURATION ---
# The database is NOT needed for collectstatic, so we provide a dummy default URL.
# This prevents the build from failing if DATABASE_URL is not set.
# The real URL will be present in the live environment.
DATABASES = {
    'default': dj_database_url.config(
        default='postgres://user:pass@localhost/db', # Dummy URL
        conn_max_age=600,
        ssl_require=True
    )
}

# --- STATIC FILES & WHITENOISE ---
# Whitenoise is already in your base middleware, so we just need the storage setting.
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'


# --- AWS S3 Media Files Configuration ---
# These are not needed for collectstatic, so we provide safe, empty defaults.
AWS_ACCESS_KEY_ID = config('AWS_ACCESS_KEY_ID', default='')
AWS_SECRET_ACCESS_KEY = config('AWS_SECRET_ACCESS_KEY', default='')
AWS_STORAGE_BUCKET_NAME = config('AWS_STORAGE_BUCKET_NAME', default='')
AWS_S3_REGION_NAME = config('AWS_S3_REGION_NAME', default='') # e.g., 'eu-west-1'
AWS_S3_CUSTOM_DOMAIN = f'{AWS_STORAGE_BUCKET_NAME}.s3.amazonaws.com' if AWS_STORAGE_BUCKET_NAME else ''
AWS_S3_OBJECT_PARAMETERS = {'CacheControl': 'max-age=86400'}
DEFAULT_FILE_STORAGE = 'storages.backends.s3boto3.S3Boto3Storage'


# --- ENHANCED PRODUCTION SECURITY ---
SECURE_SSL_REDIRECT = True
SECURE_HSTS_SECONDS = 2592000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True


# --- THIRD-PARTY SERVICE CONFIGURATIONS ---
# All third-party API keys can be safely defaulted to None or empty strings
# for the build process, as they are not needed for `collectstatic`.

# --- TWILIO ---
TWILIO_ACCOUNT_SID = config('TWILIO_ACCOUNT_SID', default=None)
TWILIO_AUTH_TOKEN = config('TWILIO_AUTH_TOKEN', default=None)
TWILIO_SMS_FROM_NUMBER = config('TWILIO_SMS_FROM_NUMBER', default=None)
TWILIO_WHATSAPP_FROM_NUMBER = config('TWILIO_WHATSAPP_FROM_NUMBER', default=None)

# --- AFRICASTALKING (Example, uncomment if you use it) ---
# AFRICASTALKING_API_KEY = config('AFRICASTALKING_API_KEY', default=None)
# AFRICASTALKING_USERNAME = config('AFRICASTALKING_USERNAME', default=None)
# AFRICASTALKING_SENDER_ID = config('AFRICASTALKING_SENDER_ID', default=None)
# AFRICASTALKING_WHATSAPP_NUMBER = config('AFRICASTALKING_WHATSAPP_NUMBER', default=None)


# --- ZEPTOEMAIL PROVIDER ---
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_USE_TLS = True
EMAIL_HOST = config('EMAIL_HOST', default='')
EMAIL_PORT = config('EMAIL_PORT', default='587', cast=int)
EMAIL_HOST_USER = config('EMAIL_HOST_USER', default='')
EMAIL_HOST_PASSWORD = config('EMAIL_HOST_PASSWORD', default='')
DEFAULT_FROM_EMAIL = config('DEFAULT_FROM_EMAIL', default='webmaster@localhost')


# --- LOGGING ---
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