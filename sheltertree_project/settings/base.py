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


AUTH_USER_MODEL = 'users.CustomUser'


GEOIP_PATH = os.path.join(BASE_DIR, 'geoip')



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
    'apps.users.apps.UsersConfig',
    
    #allauth apps
    'django.contrib.sites', # Required by allauth
    'allauth',
    'allauth.account',
    'allauth.socialaccount',
    # Optional - we will configure this in Day 7(b) or (c)
    # 'allauth.socialaccount.providers.google',
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
    # The allauth middleware is required for its advanced session
    # management and other authentication-related features.
    "allauth.account.middleware.AccountMiddleware",
    'apps.users.middleware.OnboardingMiddleware',
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
SITE_ID = 1

AUTHENTICATION_BACKENDS = [
    'django.contrib.auth.backends.ModelBackend',
    'allauth.account.auth_backends.AuthenticationBackend',
]

# --- LOGIN & SIGNUP ---
# NEW: Replaces ACCOUNT_AUTHENTICATION_METHOD. Users can log in with username or email.
ACCOUNT_LOGIN_METHODS = {'username', 'email'}

# NEW: Replaces ACCOUNT_USERNAME_REQUIRED and ACCOUNT_EMAIL_REQUIRED.
# Defines the fields on the signup form. '*' means the field is required.
ACCOUNT_SIGNUP_FIELDS = ['username*', 'email*', 'password1*', 'password2*']

# We are not collecting passwords on the initial form in our staged onboarding.
# Allauth handles this, so we don't need to list password fields here.

# --- EMAIL VERIFICATION ---
ACCOUNT_EMAIL_VERIFICATION = 'mandatory'

# --- REDIRECTS ---
LOGIN_URL = 'account_login'
LOGIN_REDIRECT_URL = '/'
ACCOUNT_LOGOUT_REDIRECT_URL = '/'

# --- OTHER SETTINGS ---
ACCOUNT_SESSION_REMEMBER = True
# This still correctly points to our minimal form for Stage 1.
ACCOUNT_FORMS = {'signup': 'apps.users.forms.MinimalSignupForm'}

ACCOUNT_LOGIN_ON_EMAIL_CONFIRMATION = True
# ACCOUNT_CONFIRM_EMAIL_ON_GET = True