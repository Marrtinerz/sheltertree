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
from sheltertree_project.configuration.username_blacklist import BLACKLIST as USERNAME_BLACKLIST
import dj_database_url
# --- Core Paths ---
# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent.parent
# This points to the project root (where manage.py is), which is more useful.


AUTH_USER_MODEL = 'users.CustomUser'


GEOIP_PATH = os.path.join(BASE_DIR, 'geoip')

# sms and whatsapp vendor
SMS_VENDOR = config('SMS_VENDOR', default='CONSOLE')

# --- Application Definition ---
INSTALLED_APPS = [
    'whitenoise.runserver_nostatic',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    # 'compressor',
    'widget_tweaks',
    'storages',
    'django.contrib.humanize',
    
    # Our app - using the 'apps' prefix is a good practice for clarity.
    'apps.reviews',
    'apps.locations',
    'apps.users.apps.UsersConfig',
    'apps.core.apps.CoreConfig',
    'apps.notifications',
    'apps.intelligence',
    'apps.careers',
    
    #allauth apps
    'django.contrib.sites', # Required by allauth
    'allauth',
    'allauth.account',
    'allauth.socialaccount',
    'allauth.socialaccount.providers.google',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'csp.middleware.CSPMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
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
    'allauth.account.middleware.AccountMiddleware',
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
        'NAME': config('POSTGRES_DB', default='sheltertree_dev'),
        'USER': config('POSTGRES_USER', default='your_local_username'),
        'PASSWORD': config('POSTGRES_PASSWORD', default=''),
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

# This tells Django to use the libsass compiler when `runserver` looks for static files.
STATICFILES_FINDERS = [
    'django.contrib.staticfiles.finders.FileSystemFinder',
    'django.contrib.staticfiles.finders.AppDirectoriesFinder',
]

SASS_PRECISION = 8


# --- Default primary key field type ---
# https://docs.djangoproject.com/en/5.2/ref/settings/#default-auto-field
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'


# --- Auth ---
SITE_ID = 1

AUTHENTICATION_BACKENDS = [
    'django.contrib.auth.backends.ModelBackend',
    'allauth.account.auth_backends.AuthenticationBackend',
]

SOCIALACCOUNT_ADAPTER = 'apps.users.adapter.CustomSocialAccountAdapter'

SOCIALACCOUNT_PROVIDERS = {
    'google': {
        'SCOPE': ['profile', 'email'],
        'AUTH_PARAMS': {'access_type': 'online'},
        'VERIFIED_EMAIL': True # A great setting for added trust
    }
}

# UX Improvements
SOCIALACCOUNT_SIGNUP_FORM_CLASS = 'apps.users.forms.CustomSocialSignupForm'
SOCIALACCOUNT_AUTO_SIGNUP=False # Automatically sign up new social users

ENABLE_CONSENT_BANNER=config('ENABLE_CONSENT_BANNER', default=False, cast=bool)
GOOGLE_MAPS_API_KEY=config('GOOGLE_MAPS_API_KEY')
MAPBOX_ACCESS_TOKEN=config('MAPBOX_ACCESS_TOKEN')
GOOGLE_ANALYTICS_ID=config('GOOGLE_ANALYTICS_ID', default=None)

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

# This one line changes the entire verification behavior of the platform.
ACCOUNT_EMAIL_VERIFICATION_BY_CODE_ENABLED = True

ACCOUNT_EMAIL_VERIFICATION_SUPPORTS_RESEND = True

ACCOUNT_UNIQUE_EMAIL = True

# We can also configure the code's length for a better UX
ACCOUNT_EMAIL_VERIFICATION_CODE_LENGTH = 6

ADMIN_EMAIL_RECEIVER = 'support@mysheltertree.com'

# --- REDIRECTS ---
LOGIN_URL = 'account_login'
LOGIN_REDIRECT_URL = '/'
ACCOUNT_LOGOUT_REDIRECT_URL = '/'

# --- OTHER SETTINGS ---
ACCOUNT_SESSION_REMEMBER = True
# This still correctly points to our minimal form for Stage 1.
ACCOUNT_FORMS = {
    'login': 'apps.users.forms.CustomLoginForm', # Use our new custom login form
    'signup': 'apps.users.forms.MinimalSignupForm',
    }

ACCOUNT_EMAIL_SUBJECT_PREFIX = None

ACCOUNT_CHANGE_EMAIL = True

ACCOUNT_LOGIN_ON_EMAIL_CONFIRMATION = True
# ACCOUNT_CONFIRM_EMAIL_ON_GET = True

ACCOUNT_ADAPTER = 'apps.users.adapter.MyAccountAdapter'

ACCOUNT_USERNAME_BLACKLIST = USERNAME_BLACKLIST

# --- ShelterTree Business Logic Settings ---

# The time window (in hours) within which a new review will be retroactively
# marked as "verified" if the user verifies their phone number.
REVIEW_VERIFICATION_GRACE_PERIOD_HOURS = 48


# --- Media Files Configuration (User-uploaded content) ---
# The absolute filesystem path to the directory that will hold user-uploaded files.
# MEDIA_ROOT = BASE_DIR / 'media'
MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')





# #Paystack settings
# PAYSTACK_PUBLIC_KEY = config('PAYSTACK_PUBLIC_KEY')
# PAYSTACK_SECRET_KEY = config('PAYSTACK_SECRET_KEY')



# ==============================================================================
# CONTENT SECURITY POLICY (CSP)
# A world-class security feature to prevent XSS and other injection attacks.
# We explicitly whitelist trusted sources for scripts, styles, images, etc.
# ==============================================================================

# Defines the default policy for any directive not explicitly set.
# 'self' allows resources from our own domain.
CSP_DEFAULT_SRC = ("'self'",)

# Defines where scripts can be loaded from.
CSP_SCRIPT_SRC = (
    "'self'",
    "'unsafe-inline'",         # NOTE: Often required by Bootstrap/HTMX for inline scripts. Long-term, we can aim to remove this.
    "connect.facebook.net",    # REQUIRED for Facebook Pixel
    "embed.tawk.to",           # REQUIRED for Tawk.to chat widget
)

# Defines where stylesheets can be loaded from.
CSP_STYLE_SRC = (
    "'self'",
    "'unsafe-inline'",         # NOTE: Often required by Bootstrap.
    "fonts.googleapis.com",    # If you use Google Fonts
)

# Defines where images can be loaded from.
CSP_IMG_SRC = (
    "'self'",
    "data:",                   # Allows for inline images (e.g., base64 encoded)
    "https://*.facebook.com",  # Facebook's tracking pixels and images
)

# Defines where fonts can be loaded from.
CSP_FONT_SRC = (
    "'self'",
    "fonts.gstatic.com",       # Companion to Google Fonts
)

# Defines where we can make background requests to (XHR, Fetch, etc.).
CSP_CONNECT_SRC = (
    "'self'",
    "connect.facebook.net",    # REQUIRED for Facebook Pixel events
    "embed.tawk.to",           # REQUIRED for Tawk.to
    "wss://*.tawk.to",         # REQUIRED for Tawk.to's live WebSocket connection
)

# Defines which sites can embed our content in an iframe.
CSP_FRAME_ANCESTORS = ("'self'",)

# Defines which sites we can embed in an iframe on our page.
CSP_FRAME_SRC = (
    "'self'",
    "https://*.facebook.com",  # Allows for Facebook's iframes (e.g., for login buttons)
)