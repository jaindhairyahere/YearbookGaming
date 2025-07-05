# Library Imports
from django.conf import settings
from django.dispatch import receiver
from django.db.models.signals import post_save
import json

# Project Imports
from moderate_app.models import ReportingTicket
from moderate_app.serializers import ReportingTicketSerializer
from utils.producer import TicketProducer as TicketProducer

producer = TicketProducer(settings.MESSAGE_QUEUE_URL)
producer.connect()


@receiver(post_save, sender=ReportingTicket)
def content_changed_or_created(sender, instance, **kwargs):
    """Function which initiates different actions based on how the 
    "content" instance will be changed depending on the "post_save" signal.
    Send ticket to moderation service
    """
    serializer = ReportingTicketSerializer(instance, context={'purpose':'internal'})
    payload = json.dumps(serializer.data)
    producer.publish_message(payload)
    print("Message Published")
    