from celery import shared_task
from django.db import models
from utils.models import TimeStampedModel
from user_client.signals import *
from django.utils import timezone
from utils.choices import *
from utils.models import ModerationBase

class UploadObject(TimeStampedModel):
    """Model for storing all types of content
    
    Defined Fields:
        s3_object_key: String denoting the s3_object_key
        extension: String denoting the file extension
        meta: JSON Object containing meta-data of the file. Used only for reading, not for querying
        upload_complete: Boolean denoting if the file has been successfully uploaded
        content: ForeignKey to `user_client.Content` instance

    Inherited Fields:
        created_on (TimeStampedModel): Time when an instance is created on the server side
        updated_on (TimeStampedModel): Time when an instance is updated on the server side
        deleted_on (TimeStampedModel): Time when an instance is deleted on the server side
    """
    s3_object_key = models.CharField(
        max_length=500, unique=True,
        help_text='The unique key that identifies the media on S3'
    )
    extension = models.CharField(
        max_length=8, default="jpeg",
        help_text='Extension of the file to be uploaded'
    )
    meta = models.JSONField(default=dict,
        help_text='JSON Object containing meta-data of the file'
        'Used only for reading, not for querying'
    )
    upload_complete = models.BooleanField(
        default=False, 
        help_text='Boolean denoting if the file has been successfully uploaded'
    )    
    content = models.ForeignKey(
        "user_client.Content", on_delete=models.CASCADE, 
        null=True, related_name="medias",
        help_text=
        'ForeignKey Relationship field with `user_client.Content`'
        'Denotes the `content` object associated with the instance'
    )
    permission_fields = ["s3_object_key", "extension", "meta", "content"]

    
class Content(TimeStampedModel, ModerationBase):
    """Model for storing all types of content
    
    Defined Fields:
        user: Foreign Key to the `YearbookUser` who created the content
        content_type: Describes the type of content [Post, Comment, Chat, History]
        text: The text part of the content
        parent: Foreign Key to self (with null=True)
    
    Reverse Fields:
        medias: All the objects of `UploadContent` associated with this instance of `Content`
        tickets: All the objects of `ModerationTicket` associated with this instance of `Content` 
        feedbacks: All the objects of `FeedbackTags` that are associated with this instance of `Content` 
    
    Inherited Fields:
        created_on (TimeStampedModel): Time when an instance is created on the server side
        updated_on (TimeStampedModel): Time when an instance is updated on the server side
        deleted_on (TimeStampedModel): Time when an instance is deleted on the server side
        status (ModerationBase): Status of Moderation of the content    
    
    Property Methods:
        is_under_review : If the content is under reveiw
        is_approved: If the content is approved
        is_rejected: If the content is rejected
        is_deleted: If the content is deleted
        is_marked_spam: If the conent is marked spam
    """
    user = models.BigIntegerField(
        null=False,
        help_text='Foreign Key to the `YearbookUser` (of SocialService) who created the content'
    )
    content_type = models.IntegerField(
        default=ContentTypeChoices.POST, 
        choices=ContentTypeChoices.choices,
        help_text=
        'Integer denoting the `content_type` of the object'
        'Available choices are `ContentTypeChoices.choices`'
    )
    text = models.TextField(
        null=False, blank=True,
        help_text=
        'All the textual data of the post. May contain links as well'
    )
    parent = models.ForeignKey(
        "self", null=True, 
        on_delete=models.SET_NULL, related_name="children",
        help_text=
        'ForeignKey relationship to an object of the same class'
        'Used to implement parent-child relationsips. Eg- Post and its comments'
    )
    permission_fields = ['id', 'user', 'content_type', 'text', 'parent', 'medias', 'status']
    
    
    @property
    def is_under_review(self):
        """Property method returning if content is under review

        Returns:
            bool: Moderation Status
        """
        return self.status == ModerationStatesChoices.UNDER_REVIEW
    
    @property
    def is_approved(self):
        """Property method returning if content is approved

        Returns:
            bool: Moderation Status
        """
        return self.status == ModerationStatesChoices.APPROVED
    
    @property
    def is_rejected(self):
        """Property method returning if content is rejected

        Returns:
            bool: Moderation Status
        """
        return self.status == ModerationStatesChoices.REJECTED
    
    @property
    def is_deleted(self):
        """Property method returning if content is deleted

        Returns:
            bool: Deletion date is not None
        """
        return self.deleted_on is not None
    
    @property
    def is_marked_spam(self):
        """Property method returning if content is marked spam

        Returns:
            bool: Moderation Status
        """
        return self.status == ModerationStatesChoices.MARKED_SPAM
    
    class Meta:
        get_latest_by = "updated_on"
        ordering = (
            "-updated_on",
            "-created_on",
        )


class YearbookModerator(TimeStampedModel):
    """Stores a reference to User from the 'Auth Service'.

    Fields:
        user: User associated with this moderator
        is_mod_available: Boolean if the moderator is currently available to recieve content
        last_logout: Boolean if the moderator is not currently available to recieve content
        
    Inherited Fields:
        created_on (TimeStampedModel): Time when an instance is created on the server side
        updated_on (TimeStampedModel): Time when an instance is updated on the server side
        deleted_on (TimeStampedModel): Time when an instance is deleted on the server side
    
    """
    user = models.OneToOneField(
        "app_admin.YearbookUser", on_delete=models.CASCADE, 
        related_name="moderator", help_text=
        'Foreign key to `YearbookUser` used to authenticate this moderator'
    )
    is_mod_available = models.BooleanField(
        'logged_in', 
        default=False,
        help_text='Designates whether this user is currently available. '
    )
    last_logout = models.DateTimeField(
        help_text='Last logout date-time of the moderator'
    )
    
    @property
    def last_login(self):
        return self.modified_on
    
    @staticmethod
    def get_moderator():
        mod = YearbookModerator.objects.filter(is_mod_available=True).first()
        return mod if mod else None

    def set_active(self, shared=True):
        self.is_mod_available = True
        self.save(shared=shared)

    def set_inactive(self, shared=True):
        self.is_mod_available = False
        self.save(shared=shared)


class ModerationTicket(TimeStampedModel, ModerationBase):
    """Model for storing Moderation Tickets
    
    Defined Fields:
        user: `YearbookUser` associated with the ticket, CAN BE NULL
        content: The content associated with the ticket, can't be null
        pulled_on: Time when the ticket is pulled by the moderator. Default is False
        completed_on: Time when the ticket is marked complete by the moderator
            either by approving, or rejecting it. Default is False
    
    Inherited Fields:
        created_on (TimeStampedModel): Time when an instance is created on the server side
        updated_on (TimeStampedModel): Time when an instance is updated on the server side
        deleted_on (TimeStampedModel): Time when an instance is deleted on the server side
        status (ModerationBase): Status of Moderation of this ticket. Now note that a ticket's status
            has its own importance. Assume that content's status is the final of all the ticket status 
            , for the tickets that involved a `content`    
    
    Property Methods:
        moderator: Return the `YearbookModerator` associated 
    """
    user = models.ForeignKey(
        "app_admin.YearbookUser", null=True, 
        on_delete=models.SET_NULL, related_name="tickets",
        help_text="`YearbookUser` associated with the ticket, CAN BE NULL"
    )
    content = models.ForeignKey(
        "user_client.Content", on_delete=models.CASCADE, related_name="tickets",
        help_text="The content associated with the ticket"
    )
    pulled_on = models.DateTimeField(
        null=True,
        help_text="Time when the ticket is pulled by the moderator. Default is False"
    )
    completed_on = models.DateTimeField(
        null=True,
        help_text="Time when the ticket is marked complete by the moderator"
                "either by approving, or rejecting it. Default is False"
    )
    permission_fields = ["content", "pulled_on", "completed_on", "status"]
    
    @property
    def moderator(self):
        return self.user.moderator
    
    
class FeedbackTags(models.Model):
    """Model for storing feedback tags
    
    Defined Fields:
        name: Name of the tag
        contents: The contents associated with a tag
    
    """
    name = models.CharField(
        max_length=100, unique=True,
        help_text='Name of the tag'
    )
    contents = models.ManyToManyField(
        "user_client.Content", related_name="feedbacks",
        help_text='The contents associated with a tag'
    )
    
    
class TicketBoard(TimeStampedModel):
    """Model for storing all types of performance statistics of an user/moderator
    
    Defined Fields:
        user: Foreign Key to the `YearbookUser` to whom this board belongs
        escalated: Number of escalated tickets
        rejected: Number of rejected tickets
        approved: Number of approved tickets
        total: Total number of tickets
        times_abandoned: Number of times this user has been stale/idle/abandoned the system
        posts_abandoned: Number of posts that had to be re-queued because this moderator abandoned
        average_response_time: Average response time of the moderator in seconds
        total_logged_in_time: Total time in minutes for which the moderator was logged in the system
    
    Inherited Fields:
        created_on (TimeStampedModel): Time when an instance is created on the server side
        updated_on (TimeStampedModel): Time when an instance is updated on the server side
        deleted_on (TimeStampedModel): Time when an instance is deleted on the server side
        
    Working and Invariants:
        1. Total through PATCH requests = Escalated + Rejected + Approved
        2. Total through logout event = None
        3. Total through celery rescheduling = Posts Abandoned
        4. Total = Total through PATCH + logout + rescheduling
        
    ##### TODO - Descriptive statistics about the board, like calculating percentages etc. Should be done on client side
    """
    user = models.OneToOneField(
        "app_admin.YearbookUser", on_delete=models.CASCADE, 
        related_name="board", help_text=
        'Foreign key to `YearbookUser` used to authenticate this moderator'
    )
    escalated = models.IntegerField(
        default=0,
        help_text='Number of tickets escalated'
    )
    rejected = models.IntegerField(
        default=0,
        help_text='Number of tickets rejected'
    )
    approved = models.IntegerField(
        default=0,
        help_text='Number of tickets approved'
    )
    total = models.IntegerField(
        default=0,
        help_text='Number of tickets assigned'
    )
    times_abandoned = models.IntegerField(
        default=0,
        help_text='Number of times this moderator has abandoned the system'
                  'Abandoned by sitting idle and not log-outing'
    )
    posts_abandoned = models.IntegerField(
        default=0,
        help_text='Number of posts that had to be re-queued because this moderator abandoned'
    )
    average_response_time = models.BigIntegerField(
        default=10,
        help_text='Average response time of the moderator in seconds. Defaults to 10'
    )
    total_logged_in_time = models.IntegerField(
        default=0,
        help_text='Total time in minutes for which the moderator was logged in the system'
    )