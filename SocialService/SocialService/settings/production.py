from .base import *  # noqa
from .base import env

# GENERAL
# ------------------------------------------------------------------------------
# https://docs.djangoproject.com/en/dev/ref/settings/#secret-key
SECRET_KEY = env("DJANGO_SECRET_KEY")
# https://docs.djangoproject.com/en/dev/ref/settings/#allowed-hosts
ALLOWED_HOSTS = env.list("DJANGO_ALLOWED_HOSTS", default=["127.0.0.1"])

# CACHES
# ------------------------------------------------------------------------------
# https://docs.djangoproject.com/en/dev/ref/settings/#caches
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        "LOCATION": "",
    }
}

if DEBUG:
    # django-debug-toolbar
    # ------------------------------------------------------------------------------
    # https://django-debug-toolbar.readthedocs.io/en/latest/installation.html#prerequisites
    INSTALLED_APPS += ["debug_toolbar"]  # noqa F405
    # https://django-debug-toolbar.readthedocs.io/en/latest/installation.html#middleware
    MIDDLEWARE += ["debug_toolbar.middleware.DebugToolbarMiddleware"]  # noqa F405
    # https://django-debug-toolbar.readthedocs.io/en/latest/configuration.html#debug-toolbar-config
    DEBUG_TOOLBAR_CONFIG = {
        "DISABLE_PANELS": ["debug_toolbar.panels.redirects.RedirectsPanel"],
        "SHOW_TEMPLATE_CONTEXT": True,
    }
    # https://django-debug-toolbar.readthedocs.io/en/latest/installation.html#internal-ips
    INTERNAL_IPS = ["127.0.0.1", "10.0.2.2"]

# django-extensions
# ------------------------------------------------------------------------------
# https://django-extensions.readthedocs.io/en/latest/installation_instructions.html#configuration
INSTALLED_APPS += ["django_extensions"]  # noqa F405

# DATABASES
# ------------------------------------------------------------------------------
DATABASES = {"default": env.db("DATABASE_URL")}
DATABASES["default"]["ATOMIC_REQUESTS"] = True  # noqa F405
DATABASES["default"]["CONN_MAX_AGE"] = env.int("CONN_MAX_AGE", default=60)  # noqa F405
# https://docs.djangoproject.com/en/stable/ref/settings/#std:setting-DEFAULT_AUTO_FIELD
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# SECURITY
# ------------------------------------------------------------------------------
# https://docs.djangoproject.com/en/dev/ref/settings/#secure-proxy-ssl-header
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
# https://docs.djangoproject.com/en/dev/ref/settings/#secure-ssl-redirect
SECURE_SSL_REDIRECT = env.bool("DJANGO_SECURE_SSL_REDIRECT", default=True)
# https://docs.djangoproject.com/en/dev/ref/settings/#session-cookie-secure
SESSION_COOKIE_SECURE = True
# https://docs.djangoproject.com/en/dev/ref/settings/#csrf-cookie-secure
CSRF_COOKIE_SECURE = True
# https://docs.djangoproject.com/en/dev/topics/security/#ssl-https
# https://docs.djangoproject.com/en/dev/ref/settings/#secure-hsts-seconds
# TODO: set this to 60 seconds first and then to 518400 once you prove the former works
SECURE_HSTS_SECONDS = 60
# https://docs.djangoproject.com/en/dev/ref/settings/#secure-hsts-include-subdomains
SECURE_HSTS_INCLUDE_SUBDOMAINS = env.bool(
    "DJANGO_SECURE_HSTS_INCLUDE_SUBDOMAINS", default=True
)
# https://docs.djangoproject.com/en/dev/ref/settings/#secure-hsts-preload
SECURE_HSTS_PRELOAD = env.bool("DJANGO_SECURE_HSTS_PRELOAD", default=True)
# https://docs.djangoproject.com/en/dev/ref/middleware/#x-content-type-options-nosniff
SECURE_CONTENT_TYPE_NOSNIFF = env.bool(
    "DJANGO_SECURE_CONTENT_TYPE_NOSNIFF", default=True
)

# # STORAGES
# # ------------------------------------------------------------------------------
# # https://django-storages.readthedocs.io/en/latest/#installation
# INSTALLED_APPS += ["storages"]  # noqa F405
# # https://django-storages.readthedocs.io/en/latest/backends/amazon-S3.html#settings
AWS_ACCESS_KEY_ID = env("DJANGO_AWS_ACCESS_KEY_ID")
# # https://django-storages.readthedocs.io/en/latest/backends/amazon-S3.html#settings
AWS_SECRET_ACCESS_KEY = env("DJANGO_AWS_SECRET_ACCESS_KEY")
# # https://django-storages.readthedocs.io/en/latest/backends/amazon-S3.html#settings
AWS_STORAGE_BUCKET_NAME_STATIC = env("DJANGO_AWS_STORAGE_BUCKET_NAME_STATIC")
AWS_STORAGE_BUCKET_NAME_USER_FEED = env("DJANGO_AWS_STORAGE_BUCKET_NAME_USERFEED")
# # https://django-storages.readthedocs.io/en/latest/backends/amazon-S3.html#settings
# AWS_QUERYSTRING_AUTH = False
# # DO NOT change these unless you know what you're doing.
_AWS_EXPIRY = 60 * 60 * 24 * 7
PRESIGNED_EXPIRATION_TIME = 60 * 60 * 24 * 7
# # https://django-storages.readthedocs.io/en/latest/backends/amazon-S3.html#settings
# AWS_S3_OBJECT_PARAMETERS = {
#     "CacheControl": f"max-age={_AWS_EXPIRY},"
#     f" s-maxage={_AWS_EXPIRY}, must-revalidate"
# }
# # https://django-storages.readthedocs.io/en/latest/backends/amazon-S3.html#settings
AWS_S3_REGION_NAME = env("DJANGO_AWS_S3_REGION_NAME", default=None)
# # https://django-storages.readthedocs.io/en/latest/backends/amazon-S3.html#cloudfront
# AWS_S3_CUSTOM_DOMAIN = env("DJANGO_AWS_S3_CUSTOM_DOMAIN", default=None)
# aws_s3_domain = AWS_S3_CUSTOM_DOMAIN or f"{AWS_STORAGE_BUCKET_NAME}.s3.amazonaws.com"
# # STATIC
# # ------------------------
STATICFILES_STORAGE = "YearbookGaming_app.utils.storages.StaticRootS3Boto3Storage"
# COLLECTFAST_STRATEGY = "collectfast.strategies.boto3.Boto3Strategy"
STATIC_URL = env("DJANGO_AWS_S3_CUSTOM_DOMAIN")
# # MEDIA
# # ------------------------------------------------------------------------------
DEFAULT_FILE_STORAGE = "YearbookGaming_app.utils.storages.MediaRootS3Boto3Storage"
# #MEDIA_URL = f"https://{aws_s3_domain}/media/"
# AWS_PRELOAD_METADATA = True
# AWS_S3_FILE_OVERWRITE = False
# AWS_DEFAULT_ACL = None
# AWS_S3_VERIFY = True

# EMAIL
# ------------------------------------------------------------------------------
# https://docs.djangoproject.com/en/dev/ref/settings/#default-from-email
# DEFAULT_FROM_EMAIL = env(
#     "DJANGO_DEFAULT_FROM_EMAIL",
#     default="YearbookGaming_app <noreply@YearbookGamingtoys.com>",
# )
# # https://docs.djangoproject.com/en/dev/ref/settings/#server-email
# SERVER_EMAIL = env("DJANGO_SERVER_EMAIL", default=DEFAULT_FROM_EMAIL)
# # https://docs.djangoproject.com/en/dev/ref/settings/#email-subject-prefix
# EMAIL_SUBJECT_PREFIX = env(
#     "DJANGO_EMAIL_SUBJECT_PREFIX",
#     default="[YearbookGaming_app]",
# )

EMAIL_BACKEND = env(
    "DJANGO_EMAIL_BACKEND",
    default="sgbackend.SendGridBackend",
)

# ADMIN
# ------------------------------------------------------------------------------
# Django Admin URL regex.
ADMIN_URL = env("DJANGO_ADMIN_URL")

# LOGGING
# ------------------------------------------------------------------------------
# https://docs.djangoproject.com/en/dev/ref/settings/#logging
# See https://docs.djangoproject.com/en/dev/topics/logging for
# more details on how to customize your logging configuration.

# Papertrail
PAPERTRAIL_LOGGER_URL = env("PAPERTRAIL_LOGGER_URL", default="logs6.papertrailapp.com")
PAPERTRAIL_PORT_NUMBER = env("PAPERTRAIL_PORT_NUMBER", default=17017)
LOGGING["formatters"] = {
    "simple": {
        "format": "%(asctime)s YearbookGamingwebtempprod-env_ YearbookGamingMODERATOR: %(message)s",
        "datefmt": "%Y-%m-%dT%H:%M:%S",
    },
}