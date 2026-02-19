from pathlib import Path
import environ
from django.core.exceptions import ImproperlyConfigured

BASE_DIR = Path(__file__).resolve().parent.parent.parent
APPS_DIR = BASE_DIR / 'apps'

env = environ.Env(
    DEBUG=(bool, False),
    ALLOWED_HOSTS=(list, ['localhost', '127.0.0.1']),
)
environ.Env.read_env(BASE_DIR / '.env')

SECRET_KEY = env('DJANGO_SECRET_KEY', default='unsafe-dev-secret-key')
DEBUG = env('DEBUG')
ALLOWED_HOSTS = env('ALLOWED_HOSTS')

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'apps.accounts',
    'apps.ledger',
    'apps.payments',
    'apps.vtu',
    'apps.referrals',
    'apps.dashboard',
    'apps.core',
]

MIDDLEWARE = [
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
                'apps.core.context_processors.site_context',
            ],
        },
    }
]

WSGI_APPLICATION = 'config.wsgi.application'
ASGI_APPLICATION = 'config.asgi.application'

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'Africa/Lagos'
USE_I18N = True
USE_TZ = True

STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_DIRS = [BASE_DIR / 'static']
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
LOGIN_REDIRECT_URL = 'core:home'
LOGOUT_REDIRECT_URL = 'core:home'

LOG_DIR = BASE_DIR / 'logs'
LOG_DIR.mkdir(exist_ok=True)
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {'format': '%(levelname)s %(asctime)s %(name)s %(message)s'},
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
        'file': {
            'class': 'logging.FileHandler',
            'filename': LOG_DIR / 'django.log',
            'formatter': 'verbose',
        },
    },
    'root': {
        'handlers': ['console', 'file'],
        'level': env('DJANGO_LOG_LEVEL', default='INFO'),
    },
}

MONNIFY_BASE_URL = env('MONNIFY_BASE_URL', default='https://sandbox.monnify.com')
MONNIFY_API_KEY = env('MONNIFY_API_KEY', default='')
MONNIFY_SECRET_KEY = env('MONNIFY_SECRET_KEY', default='')
MONNIFY_CONTRACT_CODE = env('MONNIFY_CONTRACT_CODE', default='')

VTU_PROVIDER = env('VTU_PROVIDER', default='stub')


def get_vtpass_settings(*, require: bool = False):
    env_map = {
        'base_url': 'VTPASS_BASE_URL',
        'api_key': 'VTPASS_API_KEY',
        'username': 'VTPASS_USERNAME',
        'password': 'VTPASS_PASSWORD',
    }
    config = {
        'base_url': env('VTPASS_BASE_URL', default='https://sandbox.vtpass.com'),
        'api_key': env('VTPASS_API_KEY', default=''),
        'username': env('VTPASS_USERNAME', default=''),
        'password': env('VTPASS_PASSWORD', default=''),
    }
    if require:
        missing = [env_map[key] for key, value in config.items() if not value]
        if missing:
            names = ', '.join(missing)
            raise ImproperlyConfigured(f'VTpass is enabled for production but required env vars are missing: {names}.')
    return config


VTPASS_CONFIG = get_vtpass_settings(require=False)
REFERRAL_BONUS_PERCENT = env.float('REFERRAL_BONUS_PERCENT', default=1.0)
REFERRAL_MIN_FUND = env.float('REFERRAL_MIN_FUND', default=1000.0)
