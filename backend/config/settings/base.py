"""
Base settings shared by all environments. Environment-specific overrides
live in local.py (dev) and prod.py (deploy) — both import * from here.
"""

from datetime import timedelta
from pathlib import Path

import environ
from celery.schedules import crontab

BASE_DIR = Path(__file__).resolve().parent.parent.parent

env = environ.Env()
environ.Env.read_env(BASE_DIR.parent / ".env")

SECRET_KEY = env("DJANGO_SECRET_KEY")
DEBUG = env.bool("DJANGO_DEBUG", default=False)
ALLOWED_HOSTS = env.list("DJANGO_ALLOWED_HOSTS", default=[])

# Explicit allowlist (never CORS_ALLOW_ALL_ORIGINS), consistent with how
# ALLOWED_HOSTS is handled. The Vite dev server is the first real
# cross-origin caller of this API.
CORS_ALLOWED_ORIGINS = env.list("CORS_ALLOWED_ORIGINS", default=[])

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "corsheaders",
    "rest_framework",
    "rest_framework_simplejwt.token_blacklist",
    # local apps
    "apps.users",
    "apps.entities",
    "apps.ledger",
    "apps.currencies",
    "apps.imports",
    "apps.budgets",
    "apps.reports",
    "apps.ap_ar",
    "apps.api",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"

DATABASES = {
    "default": env.db("DATABASE_URL"),
}

AUTH_USER_MODEL = "users.User"

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "en-au"
# Display-only default; storage is always UTC internally since USE_TZ=True,
# so this needs no rework for the eventual move to China.
TIME_ZONE = "Australia/Sydney"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
# Only used by collectstatic (a prod deploy step) -- runserver's dev static
# serving doesn't need it, but it's harmless to define unconditionally here.
STATIC_ROOT = BASE_DIR / "staticfiles"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

REDIS_URL = env("REDIS_URL", default="redis://redis:6379/0")

# Celery broker/result-backend use distinct logical Redis DBs from the
# app's general-purpose REDIS_URL (db 0), so a future Redis-backed Django
# cache or other consumer never collides with Celery's keyspace.
_redis_host = REDIS_URL.rsplit("/", 1)[0]
CELERY_BROKER_URL = env("CELERY_BROKER_URL", default=f"{_redis_host}/1")
CELERY_RESULT_BACKEND = env("CELERY_RESULT_BACKEND", default=f"{_redis_host}/2")
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"
# Deliberately UTC, independent of the display TIME_ZONE above -- the beat
# schedule below is computed in UTC against ECB's publish time, and pinning
# this avoids the schedule silently shifting if TIME_ZONE ever changes.
CELERY_TIMEZONE = "UTC"
CELERY_BEAT_SCHEDULE = {
    "fetch-latest-exchange-rates-daily": {
        "task": "apps.currencies.tasks.fetch_latest_exchange_rates",
        # ECB publishes reference rates ~16:00 CET (~14:00-15:00 UTC
        # depending on DST). 16:30 UTC gives a safe buffer past either case.
        "schedule": crontab(hour=16, minute=30),
    },
}

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ],
    # Default-deny: every endpoint requires authentication, with per-viewset
    # HasEntityRole layered on top for entity-scoped role checks.
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
    "DEFAULT_RENDERER_CLASSES": [
        "rest_framework.renderers.JSONRenderer",
    ],
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 50,
    "DATETIME_FORMAT": "iso-8601",
    "DATE_FORMAT": "iso-8601",
}

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=15),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=7),
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": True,
    "UPDATE_LAST_LOGIN": True,
    "ALGORITHM": "HS256",
    "SIGNING_KEY": SECRET_KEY,
    "AUTH_HEADER_TYPES": ("Bearer",),
    "USER_ID_FIELD": "id",
    "USER_ID_CLAIM": "user_id",
}
