# Library Imports
from django.db import models
from django.conf import settings

# Project Imports
from utils.choices import ModerationStatesChoices, ReactionChoices, ContentTypeChoices
from utils.models import TimeStampedModel, ModerationBase, SeparatedValuesField

class UploadObject(TimeStampedModel):
    """Model for storing all types of content
    
    Defined Fields:
        s3_object_key: String denoting the s3_object_key
        extension: String denoting the file extension
        meta: JSON Object containing meta-data of the file. Used only for reading, not for querying
        upload_complete: Boolean denoting if the file has been successfully uploaded
        content: ForeignKey to `content_app.Content` instance

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
        "content_app.Content", on_delete=models.CASCADE, 
        null=True, related_name="medias",
        help_text=
        'ForeignKey Relationship field with `content_app.Content`'
        'Denotes the `content` object associated with the instance'
    )
    
class Content(TimeStampedModel, ModerationBase):
    """Model for storing all types of content
    
    Defined Fields:
        user: Foreign Key to the `YearbookGamingUser` who created the content
        content_type: Describes the type of content [Post, Comment, Chat, History]
        text: The text part of the content
        parent: Foreign Key to self (with null=True)
    
    Reverse Fields:
        medias: All the objects of `UploadContent` associated with this instance of `Content`
    
    Inherited Fields:
        created_on (TimeStampedModel): Time when an instance is created on the server side
        updated_on (TimeStampedModel): Time when an instance is updated on the server side
        deleted_on (TimeStampedModel): Time when an instance is deleted on the server side
        status (Moderation Base): Status of Moderation    
    
    Property Methods:
        is_under_review : If the content is under reveiw
        is_approved: If the content is approved
        is_rejected: If the content is rejected
        is_deleted: If the content is deleted
        is_marked_spam: If the conent is marked spam
    """
    user = models.ForeignKey(
        "app_admin.YearbookGamingUser",
        related_name="created_contents",
        on_delete=models.CASCADE,
        help_text=
        'Foreign Key to the `YearbookGamingUser` who created the content'
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
            bool: Moderation Status
        """
        return self.status == ModerationStatesChoices.DELETED
    
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
        
class React(TimeStampedModel):
    """Model for storing all types of reacts
    
    Defined Fields:
        user: ForeignKey to `app_admin.YearbookGamingUser` who created the reaction 
        content: ForeignKey to `content_app.Content` on which the reaction is based
        reaction: The type of Reaction (like, haha, cry, etc...)
    
    Inherited Fields:
        created_on (TimeStampedModel): Time when an instance is created on the server side
        updated_on (TimeStampedModel): Time when an instance is updated on the server side
    """
    user = models.ForeignKey("app_admin.YearbookGamingUser", on_delete=models.CASCADE, related_name="reations")
    content = models.ForeignKey("content_app.Content", on_delete=models.CASCADE, related_name="reactions")
    reaction = models.IntegerField(default=ReactionChoices.LIKE, choices=ReactionChoices.choices)
    
