import os

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))

DEBUG = False
TEMPLATE_DEBUG = False

ALLOWED_HOSTS = ["%(live_host)s"]

DATABASES = {
    "default": {
        # Ends with "postgresql_psycopg2", "mysql", "sqlite3" or "oracle".
        'ENGINE': 'django.contrib.gis.db.backends.postgis',
        # DB name or path to database file if using sqlite3.
        "NAME": "%(proj_name)s",
        # Not used with sqlite3.
        "USER": "%(proj_name)s",
        # Not used with sqlite3.
        "PASSWORD": "%(db_pass)s",
        # Set to empty string for localhost. Not used with sqlite3.
        "HOST": "127.0.0.1",
        # Set to empty string for default. Not used with sqlite3.
        "PORT": "%(pgbouncer_port)s",
    }
}

STATIC_ROOT = "%(venv_path)s/static"
STATIC_URL = "/static/"

SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTOCOL", "https")

CACHE_MIDDLEWARE_SECONDS = 60

CACHE_MIDDLEWARE_KEY_PREFIX = "%(proj_name)s"

CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.memcached.MemcachedCache",
        "LOCATION": "127.0.0.1:11211",
    }
}

SESSION_ENGINE = "django.contrib.sessions.backends.cache"

SESSION_COOKIE_SECURE = True

CONN_MAX_AGE = 60

if not DEBUG:
    PUSH_NOTIFICATIONS_SETTINGS = {
        "GCM_API_KEY": "AIzaSyDxi_YVwUKHLl5ePxDVDCoU7h_48mboXB8",
        "APNS_CERTIFICATE": PROJECT_ROOT + "deploy/apns_prod.pem",
    }

CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.memcached.MemcachedCache',
        'LOCATION': 'unix:%(venv_home)/run/memcached.sock',
    }
}