"""
Base settings to build other settings files upon.
"""
from datetime import timedelta
from pathlib import Path
from utils.defaults import MessageQueue, Cache, POSTGRES
import environ
import boto3

import os


ROOT_DIR = Path(__file__).resolve(strict=True).parent.parent.parent

env = environ.Env()

READ_DOT_ENV_FILE = env.bool("DJANGO_READ_DOT_ENV_FILE", default=False)

if READ_DOT_ENV_FILE:
    # OS environment variables take precedence over variables from .env
    env.read_env(str(ROOT_DIR / ".env"))

# GENERAL
# ------------------------------------------------------------------------------
# https://docs.djangoproject.com/en/dev/ref/settings/#debug
DEBUG = env.bool("DJANGO_DEBUG", False)

# Local time zone. Choices are
# http://en.wikipedia.org/wiki/List_of_tz_zones_by_name
# though not all of them may be available with every OS.
# In Windows, this must be set to your system time zone.
TIME_ZONE = "UTC"

# https://docs.djangoproject.com/en/dev/ref/settings/#language-code
LANGUAGE_CODE = "en-us"

# https://docs.djangoproject.com/en/dev/ref/settings/#site-id
SITE_ID = 1

# https://docs.djangoproject.com/en/dev/ref/settings/#use-i18n
USE_I18N = True

# https://docs.djangoproject.com/en/dev/ref/settings/#use-l10n
USE_L10N = True

# https://docs.djangoproject.com/en/dev/ref/settings/#use-tz
USE_TZ = True

# https://docs.djangoproject.com/en/dev/ref/settings/#locale-paths
LOCALE_PATHS = [str(ROOT_DIR / "locale")]

# DATABASES
# ------------------------------------------------------------------------------
# https://docs.djangoproject.com/en/dev/ref/settings/#databases
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql_psycopg2',
        'NAME': os.environ.get("POSTGRES_DB", POSTGRES.DEFAULT_DB),
        'USER': os.environ.get("POSTGRES_USERNAME", POSTGRES.DEFAULT_USER),
        'PASSWORD': os.environ.get("POSTGRES_PASSWORD", POSTGRES.DEFAULT_PASSWORD),
        'HOST': os.environ.get("POSTGRES_HOST", POSTGRES.DEFAULT_HOST),
        'PORT': os.environ.get("POSTGRES_PORT", POSTGRES.DEFAULT_PORT),
        'ATOMIC_REQUESTS': False
    },
    'sqlite': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': ROOT_DIR / 'db.sqlite3',
    }   
}
# https://docs.djangoproject.com/en/stable/ref/settings/#std:setting-DEFAULT_AUTO_FIELD
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# URLS
# ------------------------------------------------------------------------------
# https://docs.djangoproject.com/en/dev/ref/settings/#root-urlconf
ROOT_URLCONF = "Moderator.urls"
# https://docs.djangoproject.com/en/dev/ref/settings/#wsgi-application
WSGI_APPLICATION = "Moderator.wsgi.application"

# APPS
# ------------------------------------------------------------------------------
DJANGO_APPS = [
    # Default Apps
    # 'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
]
EXTERNAL_APPS = [
    # Libraries and Frameworks
    'rest_framework',
    'rest_framework_simplejwt',
    'drf_yasg',
    'rest_framework_swagger',
    'django_celery_results',
    'django_celery_beat',
]
PROJECT_APPS = [
    # Custom Apps -- Also Update NUM_APPS while adding custom apps
    'app_admin',
    'user_client',
]

# https://docs.djangoproject.com/en/dev/ref/settings/#installed-apps
INSTALLED_APPS = DJANGO_APPS + EXTERNAL_APPS + PROJECT_APPS

# JWT Settings
OLD_PASSWORD_FIELD_ENABLED = True
REST_USE_JWT = True
JWT_AUTH_COOKIE = "my-app-auth"
JWT_AUTH_REFRESH_COOKIE = "my-refresh-token"

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=30),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=15),
    "ROTATE_REFRESH_TOKENS": True,
}

# AUTHENTICATION
# ------------------------------------------------------------------------------
# https://docs.djangoproject.com/en/dev/ref/settings/#authentication-backends
AUTHENTICATION_BACKENDS = [
    'app_admin.backends.AuthenticationBackend',
]

# https://docs.djangoproject.com/en/dev/ref/settings/#auth-user-model
AUTH_USER_MODEL = 'app_admin.YearbookGamingUser'

# PASSWORDS
# ------------------------------------------------------------------------------
# https://docs.djangoproject.com/en/dev/ref/settings/#password-hashers
PASSWORD_HASHERS = [
    # https://docs.djangoproject.com/en/dev/topics/auth/passwords/#using-argon2-with-django
    "django.contrib.auth.hashers.Argon2PasswordHasher",
    "django.contrib.auth.hashers.PBKDF2PasswordHasher",
    "django.contrib.auth.hashers.PBKDF2SHA1PasswordHasher",
    "django.contrib.auth.hashers.BCryptSHA256PasswordHasher",
]

# MIDDLEWARE
# ------------------------------------------------------------------------------
# https://docs.djangoproject.com/en/dev/ref/settings/#middleware
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    # "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.locale.LocaleMiddleware",
    "django.middleware.common.CommonMiddleware",
    # "django.middleware.csrf.CsrfViewMiddleware",
    # "django.contrib.auth.middleware.AuthenticationMiddleware",
    # "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.common.BrokenLinkEmailsMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    # "utility.request_response_middleware.RequestResponseMiddleware",
    "app_admin.middleware.TokenAuthenticationMiddleware",
    'user_client.middleware.UserLoginEventMiddleware',
]

RAISE_ROLLBAR = env.bool("RAISE_ROLLBAR", False)
YearbookGaming_ENV = env.str("YearbookGaming_ENV", "dev")

if RAISE_ROLLBAR:
    MIDDLEWARE.append("rollbar.contrib.django.middleware.RollbarNotifierMiddleware")
    """
    ROLLBAR CONFIGURATION
    """

    ROLLBAR = {
        "access_token": "<YourRollbarAccessToken>",  # Replace with your actual Rollbar access token
        "environment": YearbookGaming_ENV,
        "root": ROOT_DIR,
    }

# STATIC
# ------------------------------------------------------------------------------
# https://docs.djangoproject.com/en/dev/ref/settings/#static-root
STATIC_ROOT = str(ROOT_DIR / "staticfiles")
# https://docs.djangoproject.com/en/dev/ref/settings/#static-url
# STATIC_URL = "/static/"
# https://docs.djangoproject.com/en/dev/ref/contrib/staticfiles/#std:setting-STATICFILES_DIRS
STATICFILES_DIRS = [str(ROOT_DIR / "static")]
# https://docs.djangoproject.com/en/dev/ref/contrib/staticfiles/#staticfiles-finders
STATICFILES_FINDERS = [
    "django.contrib.staticfiles.finders.FileSystemFinder",
    "django.contrib.staticfiles.finders.AppDirectoriesFinder",
]

# MEDIA
# ------------------------------------------------------------------------------
# https://docs.djangoproject.com/en/dev/ref/settings/#media-root
MEDIA_ROOT = str(ROOT_DIR / "media")
# https://docs.djangoproject.com/en/dev/ref/settings/#media-url
MEDIA_URL = "/media/"

# TEMPLATES
# ------------------------------------------------------------------------------
# https://docs.djangoproject.com/en/dev/ref/settings/#templates
TEMPLATES = [
    {
        # https://docs.djangoproject.com/en/dev/ref/settings/#std:setting-TEMPLATES-BACKEND
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        # https://docs.djangoproject.com/en/dev/ref/settings/#dirs
        "DIRS": [],
        # https://docs.djangoproject.com/en/dev/ref/settings/#app-dirs
        "APP_DIRS": True,
        "OPTIONS": {
            # https://docs.djangoproject.com/en/dev/ref/settings/#template-context-processors
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.template.context_processors.i18n",
                "django.template.context_processors.media",
                "django.template.context_processors.static",
                "django.template.context_processors.tz",
                "django.contrib.messages.context_processors.messages",
            ],
            'libraries' : {
                'staticfiles': 'django.templatetags.static', 
            }
        },
    }
]

# https://docs.djangoproject.com/en/dev/ref/settings/#form-renderer
FORM_RENDERER = "django.forms.renderers.TemplatesSetting"

# http://django-crispy-forms.readthedocs.io/en/latest/install.html#template-packs
CRISPY_TEMPLATE_PACK = "bootstrap5"
CRISPY_ALLOWED_WEDTEMPLATE_PACKS = "bootstrap5"

# FIXTURES
# ------------------------------------------------------------------------------
# https://docs.djangoproject.com/en/dev/ref/settings/#fixture-dirs
FIXTURE_DIRS = (str(ROOT_DIR / "fixtures"),)

# SECURITY
# ------------------------------------------------------------------------------
# https://docs.djangoproject.com/en/dev/ref/settings/#session-cookie-httponly
SESSION_COOKIE_HTTPONLY = True
# https://docs.djangoproject.com/en/dev/ref/settings/#csrf-cookie-httponly
CSRF_COOKIE_HTTPONLY = True
# https://docs.djangoproject.com/en/dev/ref/settings/#secure-browser-xss-filter
SECURE_BROWSER_XSS_FILTER = True
# https://docs.djangoproject.com/en/dev/ref/settings/#x-frame-options
X_FRAME_OPTIONS = "DENY"

# EMAIL
# ------------------------------------------------------------------------------
# https://docs.djangoproject.com/en/dev/ref/settings/#email-backend
EMAIL_BACKEND = env(
    "DJANGO_EMAIL_BACKEND", default="django.core.mail.backends.console.EmailBackend"
)
# https://docs.djangoproject.com/en/dev/ref/settings/#email-timeout
EMAIL_TIMEOUT = 5

# ADMIN
# ------------------------------------------------------------------------------
# Django Admin URL.
ADMIN_URL = env("ADMIN_URL", default="YearbookGaming_admin/")
# https://docs.djangoproject.com/en/dev/ref/settings/#admins
ADMINS = [("""YearbookGaming Jain""", "YearbookGaming.jain@website.com")]
# https://docs.djangoproject.com/en/dev/ref/settings/#managers
MANAGERS = ADMINS

# LOGGING
LOGGING_ENABLED = os.environ.get("LOGGING_ENABLED", False)
# ------------------------------------------------------------------------------
# https://docs.djangoproject.com/en/dev/ref/settings/#logging
# See https://docs.djangoproject.com/en/dev/topics/logging for
# more details on how to customize your logging configuration.
if LOGGING_ENABLED:
    LOGGING = {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "verbose": {
                "format": "%(levelname)s %(asctime)s %(module)s "
                "%(process)d %(thread)d %(message)s"
            }
        },
        "handlers": {
            "console": {
                "level": "DEBUG",
                "class": "logging.StreamHandler",
                "formatter": "verbose",
            }
        },
        "root": {"level": "INFO", "handlers": ["console"]},
    }

# Email sendgrid
SENDGRID_API_KEY = (
    "<YourSendgridApiKey>"  # Replace with your actual Sendgrid API Key
)
# Sendgrid Host settings
EMAIL_HOST = "smtp.sendgrid.net"
EMAIL_HOST_USER = "apikey"  # this is exactly the value 'apikey'
EMAIL_HOST_PASSWORD = SENDGRID_API_KEY
EMAIL_PORT = 587
EMAIL_USE_TLS = True
DEFAULT_FROM_EMAIL = "developer@website.com"
SENDGRID_RESET_PASSWORD_TEMPLATE_ID = "<YourSendgridResetPasswordTemplateId>"
JWT_EXPIRE_TIME = 15
# rest framework
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        # 'rest_framework_simplejwt.authentication.JWTAuthentication',
    ],
    'DEFAULT_SCHEMA_CLASS': 'rest_framework.schemas.coreapi.AutoSchema',
    'DEFAULT_METADATA_CLASS': 'rest_framework.metadata.SimpleMetadata'
}

TOKEN_SALT_KEY = env.str("TOKEN_SALT", default="HAIL YearbookGaming !!")

INTERNAL_SERVICE_TIMEOUT = 50000000
IS_CRON = env.bool("RUN_CRON", False)
CREATE_USER_CRON_MINUTES = int(env.str("CREATE_USER_CRON_MINUTES", "720")) # 12 hours == 720 minutes


# MESSAGE QUEUE SETTINGS
PAGE_SIZE = 5

MAX_DEQUE_LIMIT = 5

QUEUE_BROKER = os.environ.get("MESSAGE_QUEUE_BROKER", MessageQueue.DEFAULT_BROKER)
QUEUE_SCHEME = os.environ.get("MESSAGE_QUEUE_SCHEME", MessageQueue.DEFAULT_SCHEME)
QUEUE_HOST = os.environ.get("MESSAGE_QUEUE_HOST")
QUEUE_PORT = os.environ.get(f"{QUEUE_BROKER}_PORT") # 5672
QUEUE_USER = os.environ.get(f"{QUEUE_BROKER}_USER") # "YearbookGamingadmin"
QUEUE_PASSWORD = os.environ.get(f"{QUEUE_BROKER}_PASSWORD") # "admin1234"

MESSAGE_QUEUE_URL = f"{QUEUE_SCHEME}://{QUEUE_USER}:{QUEUE_PASSWORD}@{QUEUE_HOST}:{QUEUE_PORT}"

# CELERY Settings
CELERY_BROKER = os.environ.get('CELERY_BROKER', Cache.DEFAULT_BROKER)
BROKER_PASSWORD = os.environ.get(f"{CELERY_BROKER}_PASSWORD", Cache.DEFAULT_PASSWORD)
BROKER_USER = os.environ.get(f"{CELERY_BROKER}_USER", Cache.DEFAULT_USER)
BROKER_SCHEME = os.environ.get(f"{CELERY_BROKER}_SCHEME", Cache.DEFAULT_SCHEME)
CELERY_BROKER_PORT = os.environ.get(f"{CELERY_BROKER}_PORT", Cache.DEFAULT_PORT)
CELERY_HOST = os.environ.get("CELERY_HOST_CONTAINER", Cache.DEFAULT_HOST)
BROKER_SUFFIX = os.environ.get(f"{CELERY_BROKER}_SUFFIX", Cache.DEFAULT_SUFFIX)
CELERY_BROKER_URL = f"{BROKER_SCHEME}://{BROKER_USER}:{BROKER_PASSWORD}@{CELERY_HOST}:{CELERY_BROKER_PORT}/{BROKER_SUFFIX}"

# Celery Beat Settings
accept_content = ["application/json",]
result_serializer = "json"
task_serializer = "json"
timezone = "Asia/Kolkata"
result_backend = "django-db"

MODERATOR_LOGOUT_TIME = os.environ.get("MODERATOR_LOGOUT_TIME", 10*60)

# Social Service URLs
SOCIAL_SERVICE_URL = os.environ.get("SOCIAL_SERVICE_URL")


# S3 Settings
AWS_ACCESS_KEY_ID = os.environ.get("AWS_ACCESS_KEY_ID")  # s3_media_user
AWS_SECRET_ACCESS_KEY = os.environ.get("AWS_SECRET_ACCESS_KEY")  # s3_media_user
BUCKET_NAME = os.environ.get("S3_BUCKET_NAME", "YearbookGaming_dev") #'YearbookGaming_dev'
AWS_S3_REGION_NAME = "us-east-1"


PAGE_SIZE = 5

MAX_QUEUE_SIZE = int(os.environ.get("MAX_QUEUE_SIZE", 500))
MAX_DEQUE_LIMIT = int(os.environ.get("MAX_DEQUE_LIMIT", 2))

S3_CLIENT = boto3.client('s3', 
                         aws_access_key_id=AWS_ACCESS_KEY_ID, 
                         aws_secret_access_key=AWS_SECRET_ACCESS_KEY)

# Papertrail
if LOGGING_ENABLED:
    PAPERTRAIL_LOGGER_URL = env("PAPERTRAIL_LOGGER_URL", default="logs6.papertrailapp.com")
    PAPERTRAIL_PORT_NUMBER = env("PAPERTRAIL_PORT_NUMBER", default=17017)
    LOGGING = {
        "version": 1,
        "disable_existing_loggers": False,
        "handlers": {
            "SysLog": {
                "level": "INFO",
                "class": "logging.handlers.SysLogHandler",
                "formatter": "simple",
                "address": (PAPERTRAIL_LOGGER_URL, PAPERTRAIL_PORT_NUMBER),
            },
            "file": {
                "level": "WARNING",
                "class": "logging.handlers.SysLogHandler",
                "formatter": "simple",
                "address": (PAPERTRAIL_LOGGER_URL, PAPERTRAIL_PORT_NUMBER),
            },
        },
        "loggers": {
            "django": {
                "handlers": ["SysLog"],
                "level": "INFO",
                "propagate": True,
            },
            "app-logger": {
                "handlers": ["SysLog"],
                "level": "CRITICAL",
                "propagate": True,
            },
            "file-logger": {
                "handlers": ["file", "SysLog"],
                "level": "WARNING",
                "propagate": True,
            },
        },
    }
