"""
WSGI config for Moderator project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/3.2/howto/deployment/wsgi/
"""

import os

from django.core.wsgi import get_wsgi_application

env = os.environ.get("Yearbook_ENV", "local")
settings_file = f"Moderator.settings.{env.lower()}"
os.environ.setdefault("DJANGO_SETTINGS_MODULE", settings_file)


# os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Moderator.settings')

application = get_wsgi_application()
