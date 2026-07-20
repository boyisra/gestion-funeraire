"""
Django settings — Application de Gestion de Cimetière GI2 2026
"""
import environ
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

env = environ.Env(DEBUG=(bool, False))
environ.Env.read_env(BASE_DIR / '.env')

SECRET_KEY = env('SECRET_KEY')
DEBUG = env('DEBUG')
ALLOWED_HOSTS = env.list('ALLOWED_HOSTS', default=['localhost', '127.0.0.1'])

# ─── Applications ───────────────────────────────────────────────────────────
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    # Tiers
    'corsheaders',
    'ninja',

    # Applications locales
    'apps.auth_users',
    'apps.terrain',
    'apps.reservations',
    'apps.paiements',
    'apps.concessions',
    'apps.notifications',
    'apps.rapports',
    'apps.documents',
]

MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'config.urls'
WSGI_APPLICATION = 'config.wsgi.application'

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
            ],
        },
    },
]

# ─── Base de données PostgreSQL + PostGIS ────────────────────────────────────
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': env('DB_NAME'),
        'USER': env('DB_USER'),
        'PASSWORD': env('DB_PASSWORD'),
        'HOST': env('DB_HOST', default='localhost'),
        'PORT': env('DB_PORT', default='5432'),
    }
}

# ─── Authentification personnalisée ─────────────────────────────────────────
AUTH_USER_MODEL = 'auth_users.Utilisateur'

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator', 'OPTIONS': {'min_length': 8}},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

# ─── JWT ─────────────────────────────────────────────────────────────────────
from datetime import timedelta
SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=env.int('JWT_ACCESS_TOKEN_LIFETIME_MINUTES', default=60)),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=env.int('JWT_REFRESH_TOKEN_LIFETIME_DAYS', default=7)),
    'ROTATE_REFRESH_TOKENS': True,
    'BLACKLIST_AFTER_ROTATION': True,
    'ALGORITHM': 'HS256',
    'AUTH_HEADER_TYPES': ('Bearer',),
}

# ─── Email ───────────────────────────────────────────────────────────────────
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = env('EMAIL_HOST', default='smtp.gmail.com')
EMAIL_PORT = env.int('EMAIL_PORT', default=587)
EMAIL_USE_TLS = True
EMAIL_HOST_USER = env('EMAIL_HOST_USER', default='')
EMAIL_HOST_PASSWORD = env('EMAIL_HOST_PASSWORD', default='')
DEFAULT_FROM_EMAIL = env('DEFAULT_FROM_EMAIL', default='noreply@cimetiere-gi2.com')

# URL publique de l'app frontend (Flet) — utilisée pour construire le lien
# de vérification MFA envoyé par email (ex: https://app.cimetiere-gi2.com)
FRONTEND_URL = env('FRONTEND_URL', default='http://localhost:8550')

# ─── Celery (tâches asynchrones) ─────────────────────────────────────────────
CELERY_BROKER_URL = env('REDIS_URL', default='redis://localhost:6379/0')
CELERY_RESULT_BACKEND = env('REDIS_URL', default='redis://localhost:6379/0')
CELERY_TIMEZONE = 'Africa/Brazzaville'
CELERY_BEAT_SCHEDULER = 'django_celery_beat.schedulers:DatabaseScheduler'

# ─── CORS (pour Flet en mode web) ────────────────────────────────────────────
CORS_ALLOWED_ORIGINS = [
    "http://localhost:8550",
    "http://127.0.0.1:8550",
]
CORS_ALLOW_CREDENTIALS = True

# ─── Internationalisation ────────────────────────────────────────────────────
LANGUAGE_CODE = 'fr-fr'
TIME_ZONE = 'Africa/Brazzaville'
USE_I18N = True
USE_TZ = True

# ─── Fichiers statiques et médias ────────────────────────────────────────────
STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# ─── Paiements Mobile Money ──────────────────────────────────────────────────
MTN_MOMO = {
    'BASE_URL': env('MTN_MOMO_BASE_URL', default='https://sandbox.momodeveloper.mtn.com'),
    'API_USER': env('MTN_MOMO_API_USER', default=''),
    'API_KEY': env('MTN_MOMO_API_KEY', default=''),
    'SUBSCRIPTION_KEY': env('MTN_MOMO_SUBSCRIPTION_KEY', default=''),
    'ENVIRONMENT': env('MTN_MOMO_ENVIRONMENT', default='sandbox'),
}

AIRTEL_MONEY = {
    'BASE_URL': env('AIRTEL_BASE_URL', default='https://openapi.airtel.africa'),
    'CLIENT_ID': env('AIRTEL_CLIENT_ID', default=''),
    'CLIENT_SECRET': env('AIRTEL_CLIENT_SECRET', default=''),
    'COUNTRY': env('AIRTEL_COUNTRY', default='CG'),
    'CURRENCY': env('AIRTEL_CURRENCY', default='XAF'),
}

# ─── Paramètres métier ───────────────────────────────────────────────────────
ALERTE_PLACES_CRITIQUES = 10   # Notifier admin quand < 10 places disponibles
DELAI_EXPIRATION_RESERVATION = 48  # Heures avant annulation si non payé
