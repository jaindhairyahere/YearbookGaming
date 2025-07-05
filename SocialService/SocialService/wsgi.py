"""
WSGI config for SocialService project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/3.2/howto/deployment/wsgi/
"""

import os

from django.core.wsgi import get_wsgi_application

env = os.environ.get("Yearbook_ENV", "local")
settings_file = f"SocialService.settings.{env.lower()}"
os.environ.setdefault("DJANGO_SETTINGS_MODULE", settings_file)


# os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'SocialService.settings')

application = get_wsgi_application()
