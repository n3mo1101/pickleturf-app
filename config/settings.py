"""
Django settings for config project.

For more information on this file, see
https://docs.djangoproject.com/en/4.2/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/4.2/ref/settings/
"""


import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = os.environ.get('SECRET_KEY', 'fallback-dev-key')
DEBUG = os.environ.get('DEBUG', 'True') == 'True'
ALLOWED_HOSTS = os.environ.get('ALLOWED_HOSTS', 'localhost').split(',')

# ─── APPLICATIONS ─────────────────────────────────────────────────────────────

DJANGO_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.sites',
]

THIRD_PARTY_APPS = [
    'cloudinary_storage',
    'cloudinary',           
    'allauth',
    'allauth.account',
    'allauth.socialaccount',
    'allauth.socialaccount.providers.google',
    'allauth.socialaccount.providers.facebook',
    'crispy_forms',
    'crispy_bootstrap5',
]

LOCAL_APPS = [
    'accounts',
    'courts',
    'bookings',
    'openplay',
    'inventory',
    'dashboard',
    'announcements',
    'transactions',
    'core',
]

INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS

SITE_ID = 1

# ─── MIDDLEWARE ───────────────────────────────────────────────────────────────

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',       # Static files in prod
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'allauth.account.middleware.AccountMiddleware',
]

ROOT_URLCONF = 'config.urls'

# ─── TEMPLATES ────────────────────────────────────────────────────────────────

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'accounts.context_processors.user_role',
                'announcements.context_processors.active_announcements',
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'

# ─── DATABASE ─────────────────────────────────────────────────────────────────

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': os.environ.get('DB_NAME', 'pickleball_db'),
        'USER': os.environ.get('DB_USER', 'postgres'),
        'PASSWORD': os.environ.get('DB_PASSWORD', ''),
        'HOST': os.environ.get('DB_HOST', 'localhost'),
        'PORT': os.environ.get('DB_PORT', '5432'),
    }
}

# ─── AUTH ─────────────────────────────────────────────────────────────────────

AUTH_USER_MODEL = 'accounts.User'

AUTHENTICATION_BACKENDS = [
    'django.contrib.auth.backends.ModelBackend',
    'allauth.account.auth_backends.AuthenticationBackend',
]

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

# ─── ALLAUTH CONFIG ────────────────────────────────────────────────────────────

ACCOUNT_LOGIN_METHODS             = {'email', 'username'}   # ← allow both
ACCOUNT_USER_MODEL_USERNAME_FIELD = 'username'              # ← point to our field
ACCOUNT_SIGNUP_FIELDS             = ['email*', 'password1*', 'password2*']
ACCOUNT_EMAIL_VERIFICATION        = 'mandatory'
ACCOUNT_CONFIRM_EMAIL_ON_GET      = True
ACCOUNT_LOGOUT_ON_GET             = True
ACCOUNT_ADAPTER                   = 'accounts.adapters.AccountAdapter'
SOCIALACCOUNT_ADAPTER             = 'accounts.adapters.SocialAccountAdapter'
ACCOUNT_FORMS                     = {'signup': 'accounts.forms.CustomSignupForm'}

LOGIN_URL = '/accounts/login/'
LOGIN_REDIRECT_URL = '/dashboard/'
LOGOUT_REDIRECT_URL = '/'

# ─── EMAIL ────────────────────────────────────────────────────────────────────

RESEND_API_KEY     = os.environ.get('RESEND_API_KEY', '')
DEFAULT_FROM_EMAIL = os.environ.get(
    'DEFAULT_FROM_EMAIL', 'PickleTurf <onboarding@resend.dev>'
)

if DEBUG:
    EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
else:
    EMAIL_BACKEND = 'accounts.email_backend.ResendEmailBackend'

# ─── STATIC & MEDIA ───────────────────────────────────────────────────────────

STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_DIRS = [BASE_DIR / 'static']
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# ─── MISC ─────────────────────────────────────────────────────────────────────

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'Asia/Singapore'
USE_I18N = True
USE_TZ = True
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

CRISPY_ALLOWED_TEMPLATE_PACKS = 'bootstrap5'
CRISPY_TEMPLATE_PACK = 'bootstrap5'

# ─── ALLAUTH ADAPTERS ─────────────────────────────────────────────────────────

ACCOUNT_ADAPTER        = 'accounts.adapters.AccountAdapter'
SOCIALACCOUNT_ADAPTER  = 'accounts.adapters.SocialAccountAdapter'
ACCOUNT_FORMS          = {'signup': 'accounts.forms.CustomSignupForm'}

SOCIALACCOUNT_PROVIDERS = {
    'google': {
        'SCOPE': ['profile', 'email'],
        'AUTH_PARAMS': {'access_type': 'online'},
        'APP': {
            'client_id': os.environ.get('GOOGLE_CLIENT_ID', ''),
            'secret':    os.environ.get('GOOGLE_CLIENT_SECRET', ''),
            'key':       '',
        },
    },
    'facebook': {
        'METHOD': 'oauth2',
        'SCOPE': ['email', 'public_profile'],
        'APP': {
            'client_id': os.environ.get('FACEBOOK_CLIENT_ID', ''),
            'secret':    os.environ.get('FACEBOOK_CLIENT_SECRET', ''),
            'key':       '',
        },
    },
}

# ─── PRODUCTION DATABASE ──────────────────────────────────────────────────────
import dj_database_url

DATABASES = {
    'default': dj_database_url.config(
        default=os.environ.get('DATABASE_URL'),
        conn_max_age=600,
    )
}

# ─── CLOUDINARY (Media Files) ─────────────────────────────────────────────────
CLOUDINARY_STORAGE = {
    'CLOUD_NAME': os.environ.get('CLOUDINARY_CLOUD_NAME'),
    'API_KEY':    os.environ.get('CLOUDINARY_API_KEY'),
    'API_SECRET': os.environ.get('CLOUDINARY_API_SECRET'),
}

# Only use Cloudinary in production
if not DEBUG:
    DEFAULT_FILE_STORAGE = 'cloudinary_storage.storage.MediaCloudinaryStorage'

# ─── SECURITY (Production Only) ───────────────────────────────────────────────
if not DEBUG:
    SECURE_PROXY_SSL_HEADER      = ('HTTP_X_FORWARDED_PROTO', 'https')
    SECURE_SSL_REDIRECT          = True
    SESSION_COOKIE_SECURE        = True
    CSRF_COOKIE_SECURE           = True
    SECURE_HSTS_SECONDS          = 31536000
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD          = True
    SECURE_CONTENT_TYPE_NOSNIFF  = True

    CSRF_TRUSTED_ORIGINS = [
    f"https://{host}" for host in os.environ.get('ALLOWED_HOSTS', '').split(',') if host
    ]

# ─── BOOKING CONFIG ───────────────────────────────────────────────────────────
BOOKING_OPENING_HOUR = 8    # 8:00 AM
BOOKING_CLOSING_HOUR = 22   # 10:00 PM
BOOKING_PRICE        = 300  # Default price per hour (₱)
BOOKING_SLOT_HOURS   = 1    # Fixed 1-hour slots