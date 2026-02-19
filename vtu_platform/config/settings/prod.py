from .base import *  # noqa

DEBUG = False
DATABASES = {
    'default': env.db('DATABASE_URL', default='postgres://postgres:postgres@127.0.0.1:5432/vtu_platform')
}
DATABASES['default']['ENGINE'] = 'django.db.backends.postgresql'

SECURE_HSTS_SECONDS = env.int('SECURE_HSTS_SECONDS', default=31536000)
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SECURE_SSL_REDIRECT = env.bool('SECURE_SSL_REDIRECT', default=True)
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
X_FRAME_OPTIONS = 'DENY'
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = 'strict-origin-when-cross-origin'

if VTU_PROVIDER.lower() == 'vtpass':
    VTPASS_CONFIG = get_vtpass_settings(require=True)
