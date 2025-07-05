from .base import *  # noqa


# GENERAL
# ------------------------------------------------------------------------------
# https://docs.djangoproject.com/en/dev/ref/settings/#debug
DEBUG = True
# https://docs.djangoproject.com/en/dev/ref/settings/#secret-key

SECRET_KEY = "DdOCFBJ6EAYYbS37IHQB6pGxl4BGErdP" "gaN069FzeqsDHxOXNLnfvEpWM0bLrU8S"

# https://docs.djangoproject.com/en/dev/ref/settings/#allowed-hosts
ALLOWED_HOSTS = [
    "localhost",
    "0.0.0.0",
    "127.0.0.1",
    "mtdeploy-env.eba-kz2bm5i6.us-west-2.elasticbeanstalk.com",
    "*",
    "Yearbook-social-django"
]

if env.str("ALLOWED_HOSTS", None):
    ALLOWED_HOSTS.extend(env.str("ALLOWED_HOSTS").split(","))

# CACHES
# ------------------------------------------------------------------------------
# https://docs.djangoproject.com/en/dev/ref/settings/#caches
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        "LOCATION": "",
    }
}

# EMAIL
# ------------------------------------------------------------------------------
# https://docs.djangoproject.com/en/dev/ref/settings/#email-backend
EMAIL_BACKEND = env(
    "DJANGO_EMAIL_BACKEND",
    default="sgbackend.SendGridBackend",
)

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
INTERNAL_IPS = ["127.0.0.1", "10.0.2.2", "*", "Yearbook-social-django",]
EXTERNAL_IPS = ["Yearbook-social-django",]
# django-extensions
# ------------------------------------------------------------------------------
# https://django-extensions.readthedocs.io/en/latest/installation_instructions.html#configuration
INSTALLED_APPS += ["django_extensions"]  # noqa F405

# Your stuff...
# ------------------------------------------------------------------------------
# DATABASES
# ------------------------------------------------------------------------------
# https://docs.djangoproject.com/en/dev/ref/settings/#databases

# https://docs.djangoproject.com/en/stable/ref/settings/#std:setting-DEFAULT_AUTO_FIELD
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# uploading files to s3    bucket_name = "websitestaticfile"
AWS_STORAGE_BUCKET_NAME_STATIC = env("DJANGO_AWS_STORAGE_BUCKET_NAME_STATIC", default="websitestaticfile")
AWS_STORAGE_BUCKET_NAME_USER_FEED = env("DJANGO_AWS_STORAGE_BUCKET_NAME_USERFEED", default="userfeedmedia")
STATIC_URL = "https://websitestaticfile.s3.amazonaws.com/Yearbook_admin/"
# STATICFILES_STORAGE = "Yearbook_app.utils.storages.StaticRootS3Boto3Storage"

PRESIGNED_EXPIRATION_TIME = 600
AWS_PRELOAD_METADATA = True
AWS_S3_FILE_OVERWRITE = False
AWS_DEFAULT_ACL = None
AWS_S3_VERIFY = True
# DEFAULT_FILE_STORAGE = "Yearbook_app.utils.storages.MediaRootS3Boto3Storage"
AWS_S3_OBJECT_PARAMETERS = {
    "CacheControl": "max-age=86400",
}

if LOGGING_ENABLED:
    LOGGING["formatters"] = {
        "simple": {
            "format": "%(asctime)s HOSTNAME APP_NAME: %(message)s",
            "datefmt": "%Y-%m-%dT%H:%M:%S",
        },
    }

PAGE_SIZE = 5

MAX_DEQUE_LIMIT = 5

S3_CLIENT = boto3.client('s3', 
                         aws_access_key_id=AWS_ACCESS_KEY_ID, 
                         aws_secret_access_key=AWS_SECRET_ACCESS_KEY)
AUTH_USER_MODEL = 'app_admin.YearbookUser'


USE_DUMMY_LOGIN = True

DELETED_REF_USER_ID = 0

# CELERY Settings
MY_CELERY_BROKER = os.environ.get('CELERY_BROKER', Cache.DEFAULT_BROKER)
MY_BROKER_PASSWORD = os.environ.get(f"{MY_CELERY_BROKER}_PASSWORD", Cache.DEFAULT_PASSWORD)
MY_BROKER_USER = os.environ.get(f"{MY_CELERY_BROKER}_USER", Cache.DEFAULT_USER)
MY_BROKER_SCHEME = os.environ.get(f"{MY_CELERY_BROKER}_SCHEME", Cache.DEFAULT_SCHEME)
MY_CELERY_BROKER_PORT = os.environ.get(f"{MY_CELERY_BROKER}_PORT", Cache.DEFAULT_PORT)
MY_CELERY_HOST = os.environ.get("CELERY_HOST_CONTAINER", Cache.DEFAULT_HOST)
MY_BROKER_SUFFIX = os.environ.get(f"{MY_CELERY_BROKER}_SUFFIX", Cache.DEFAULT_SUFFIX)

CELERY_BROKER_URL = f"{MY_BROKER_SCHEME}://{MY_BROKER_USER}:{MY_BROKER_PASSWORD}@{MY_CELERY_HOST}:{MY_CELERY_BROKER_PORT}/{MY_BROKER_SUFFIX}"
