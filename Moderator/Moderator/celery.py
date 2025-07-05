import os
from celery import Celery

env = os.environ.get("Yearbook_ENV", "local")
settings_file = f"Moderator.settings.{env.lower()}"
os.environ.setdefault("DJANGO_SETTINGS_MODULE", settings_file)

app = Celery('Moderator')
app.conf = app.config_from_object("django.conf:settings", namespace="CELERY")

# Celery Beat Settings
app.conf.beat_schedule = {
    'periodically-expire-tickets': {
        'task': 'tasks.periodic_check_expired',
        'schedule': os.environ.get("MODERATOR_LOGOUT_TIME", 10*60)/5,
        'args': ()
    },
    'periodically-reconnect': {
        'task': 'tasks.setup_connection',
        'schedule': os.environ.get("MESSAGE_QUEUE_REFRESH_TIME", 1*60),
        'args': ()
    }
}
# app.register_task("tasks.shared_save")
app.autodiscover_tasks(["user_client"])