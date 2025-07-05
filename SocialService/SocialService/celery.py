# from __future__ import absolute_import, unicode_literals
import os
from celery import Celery

env = os.environ.get("Yearbook_ENV", "local")
settings_file = f"SocialService.settings.{env.lower()}"
os.environ.setdefault("DJANGO_SETTINGS_MODULE", settings_file)

app = Celery('SocialService')
app.conf = app.config_from_object("django.conf:settings", namespace="CELERY")

# Celery Beat Settings
app.conf.beat_schedule = {
    'periodically-reconnect': {
        'task': 'tasks.setup_connection2',
        'schedule': os.environ.get("MESSAGE_QUEUE_REFRESH_TIME", 1*60),
    }
}

app.autodiscover_tasks(['moderate_app'])