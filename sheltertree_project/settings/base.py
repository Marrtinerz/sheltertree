# sheltertree_project/settings/base.py
"""
Base Django settings for the ShelterTree project.
These settings are shared across all environments.
For environment-specific settings, see development.py or production.py.
"""
import os
from pathlib import Path
from decouple import config
from django.utils.translation import gettext_lazy as _

# --- Core Paths ---
# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent.parent
# This points to the project root (where manage.py is), which is more useful.


# --- Application Definition ---
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    # Our app - using the 'apps' prefix is a good practice for clarity.
    'apps.reviews',
    'apps.locations',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    # LocaleMiddleware must come after SessionMiddleware and before CommonMiddleware
    'django.middleware.locale.LocaleMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'sheltertree_project.urls'
WSGI_APPLICATION = 'sheltertree_project.wsgi.application'


# --- Templates ---
TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [os.path.join(BASE_DIR, 'templates')], # Add a project-level templates directory
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                # Our custom context processor for API keys
                'sheltertree_project.context_processors.api_keys',
                'sheltertree_project.context_processors.global_search_form',
                
            ],
        },
    },
]


# --- Database ---
# https://docs.djangoproject.com/en/5.2/ref/settings/#databases
# The actual connection details will be in dev/prod files.
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': config('POSTGRES_DB'),
        'USER': config('POSTGRES_USER'),
        'PASSWORD': config('POSTGRES_PASSWORD'),
        'HOST': config('DATABASE_HOST', default='db'),
        'PORT': config('DATABASE_PORT', default='5432'),
    }
}


# --- Password Validation ---
# https://docs.djangoproject.com/en/5.2/ref/settings/#auth-password-validators
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]


# --- Internationalization & Localization (i18n, l10n) ---
# https://docs.djangoproject.com/en/5.2/topics/i18n/
LANGUAGES = [
    ('en', _('English')),
    ('fr', _('French')),
]
LANGUAGE_CODE = 'en-us'
LOCALE_PATHS = [os.path.join(BASE_DIR, 'locale')]
USE_I18N = True
USE_L10N = True # Renamed in Django 4.0, USE_L10N is for formatting
USE_TZ = True
TIME_ZONE = 'UTC'


# --- Static & Media Files ---
# https://docs.djangoproject.com/en/5.2/howto/static-files/
STATIC_URL = '/static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles') # For production 'collectstatic'
STATICFILES_DIRS = [os.path.join(BASE_DIR, 'static')] # For development assets

MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media') # For user-uploaded files


# --- Default primary key field type ---
# https://docs.djangoproject.com/en/5.2/ref/settings/#default-auto-field
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'


# --- Auth ---
# We will create user-facing login pages eventually.
LOGIN_URL = '/admin/login' # Name of the URL pattern for the login page
LOGIN_REDIRECT_URL = '/' # Where to go after a successful login
LOGOUT_REDIRECT_URL = '/' # Where to go after logging out