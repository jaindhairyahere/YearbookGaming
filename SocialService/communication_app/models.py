from django.db import models
from utils.models import TimeStampedModel, ModerationBase, SeparatedValuesField
from utils.choices import RequestTypeChoices

# Create your models here.
class Channel(TimeStampedModel):
    """A single channel object.

    Fields:
        name: Name of the channel
        user_ids: Users associated with this channel
        is_moderated: Is the channel under moderation of the admin or is unassigned
    
    Reverse Fields:
        content_set: List of all the content objects where Foreign key is current channel object
        
    #TODO - Change the Channel Class to be inheriting from TimeStampModel
    """
    name = models.CharField(max_length=1000, unique=True)
    is_under_moderation = models.BooleanField(default=True)
    nickname = models.CharField(default="a new channel for chat", null=True, blank=False, max_length=100)
    admins = models.ManyToManyField("app_admin.YearbookGamingUser")
    
    def __str__(self):
        """String Representation of a Channel Object

        Returns:
            name (str): Name of the channel
        """
        return f"{self.nickname} ({self.name})"
    
class Subscription(TimeStampedModel):
    channel = models.ForeignKey(Channel, on_delete=models.CASCADE, related_name="subscriptions")
    user = models.ForeignKey("app_admin.YearbookGamingUser", on_delete=models.CASCADE, related_name="subscriptions")
    

class GameRequest(TimeStampedModel):
    is_accepted = models.BooleanField(default=False)
    sender = models.ForeignKey("app_admin.YearbookGamingUser", on_delete=models.CASCADE, related_name="requests_sent")
    receiver = models.ForeignKey("app_admin.YearbookGamingUser", on_delete=models.CASCADE, related_name="requests_received")
    type = models.IntegerField(choices=RequestTypeChoices.choices, default=RequestTypeChoices.FRIEND_REQUEST)
    channel = models.ForeignKey(Channel, on_delete=models.SET_NULL, null=True) # TODO - Remove this null=True

