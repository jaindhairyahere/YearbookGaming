from django.conf import settings
from SocialService.celery import app
from moderate_app.receivers import producer


@app.task(name="tasks.setup_connection", serializer="json")
def refresh_connection(*args, **kwargs):
    success = False, False
    if producer is not None:
        if producer._connection is not None and producer._connection.is_closed:
            producer.connect(settings.MESSAGE_QUEUE_URL)
            success = True, True
        else:
            print("Connection is None? ", producer._connection is None)
            print("Connection is Closed? ", producer._connection.is_closed)
            success = True, False
    return success

@app.task(name="tasks.setup_connection2", serializer="json")
def refresh_connection(*args, **kwargs):
    """Periodically reconnects the consumer instance so as to avoid connection reset error"""
    producer.connect()
