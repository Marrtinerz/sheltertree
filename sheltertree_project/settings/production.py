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