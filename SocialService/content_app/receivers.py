from content_app.models import Content
from django.dispatch import receiver
# from django.db.models.signals import post_save
from content_app.signals import content_send_to_moderation
from moderate_app.models import ReportingTicket

@receiver(content_send_to_moderation, sender=Content)
def content_changed_or_created(sender, instance, **kwargs):
    """Function which initiates different actions based on how the 
    "content" instance will be changed depending on the "post_save" signal.
    Send ticket to moderation service
    """
    if not instance.medias.count() or instance.deleted_on is not None:
        return
    for media in instance.medias.all():
        if media.deleted_on is None:
            ReportingTicket.objects.create(content=instance, user=instance.user)