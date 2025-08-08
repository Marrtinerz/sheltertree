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

# Optional: Add Django Debug Toolbar for a huge development boost
# INSTALLED_APPS += ['debug_toolbar']
# MIDDLEWARE += ['debug_toolbar.middleware.DebugToolbarMiddleware']
# INTERNAL_IPS = ['127.0.0.1']