from .base import *  # noqa: F401,F403

DEBUG = False

# Single flag gating every HTTPS-dependent setting below, rather than four
# independent envs -- one decision point to flip once a real domain + TLS
# cert exists in front of this. Defaults False so the first deploy (nginx
# on port 80 only, no TLS yet -- see nginx/nginx.conf) actually works;
# forcing SSL redirect/HSTS/secure cookies before TLS exists would break
# every request.
DJANGO_USE_HTTPS = env.bool("DJANGO_USE_HTTPS", default=False)
SECURE_SSL_REDIRECT = DJANGO_USE_HTTPS
SECURE_HSTS_SECONDS = 31536000 if DJANGO_USE_HTTPS else 0
CSRF_COOKIE_SECURE = DJANGO_USE_HTTPS
SESSION_COOKIE_SECURE = DJANGO_USE_HTTPS

# Static file storage: nginx serves /static/ directly from a shared volume
# populated by `collectstatic` at image build time (see backend/Dockerfile.prod
# and nginx/nginx.conf) -- no whitenoise/S3 needed at this scale.

# No email backend configured -- nothing in the app sends email yet (no
# password reset, no notifications). Add one when a feature actually needs it.

# This runs in Docker; stdout *is* the log destination (captured by
# `docker logs` / whatever aggregator sits in front of it later).
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "console": {"format": "%(asctime)s %(levelname)s %(name)s: %(message)s"},
    },
    "handlers": {
        "console": {"class": "logging.StreamHandler", "formatter": "console"},
    },
    "root": {"handlers": ["console"], "level": "INFO"},
    "loggers": {
        "django": {"handlers": ["console"], "level": "INFO", "propagate": False},
    },
}
