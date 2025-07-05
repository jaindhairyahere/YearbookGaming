from django.db import models
from utils.choices import ModerationStatesChoices
from celery import shared_task, group
# from celery import current_app as app

class ModelBase(models.Model):
    """####TODO - This base should provide support for shared_save using celery worker"""
    # @app.task(name="tasks.shared_save", serializer="pickle") 
    # def shared_save(self, *args, **kwargs):
    #     return super(self).save(*args, **kwargs)

    def save(self, *args, **kwargs):
        kwargs.pop('shared', False)
        super().save(*args, **kwargs)
    #     if not kwargs.pop('shared', False):
    #         return super().save(*args, **kwargs)
    #     else:
    
    #         self.kwargs.pop("serializer_class", None)
    #         t = [self.shared_save.s(*args, **kwargs)]
    #         group(t)()
    class Meta:
        abstract = True


class SeparatedValuesField(models.TextField):
    """Custom field type for handling list type fields"""
    __metaclass__ = models.Field

    def __init__(self, *args, **kwargs):
        self.token = kwargs.pop('token', ',')
        super(SeparatedValuesField, self).__init__(*args, **kwargs)

    def to_python(self, value):
        if not value: return
        if isinstance(value, list):
            return value
        return value.split(self.token)

    def get_db_prep_value(self, value, connection, prepared):
        if not value: return
        if isinstance(value, str):
            value = eval(value)
        assert(isinstance(value, list) or isinstance(value, tuple))
        return self.token.join(value)

    def value_to_string(self, obj):
        value = self._get_val_from_obj(obj)
        return self.get_db_prep_value(value)


class TimeStampedModel(ModelBase):
    """TimeStampedModel
    An abstract base class model that provides self-managed "created" and
    "modified" fields.
    """

    created_on = models.DateTimeField(
        auto_now_add=True, 
        db_column="created_on",
        help_text="DateTime of when the object was created")
    updated_on = models.DateTimeField(
        auto_now=True, 
        db_column="updated_on",
        help_text="DateTime of when the object was last updated")
    deleted_on = models.DateTimeField(
        null=True, 
        default=None,
        help_text="DateTime of when the object was deleted"
                  "None if object is not deleted yet"
        )

    class Meta:
        get_latest_by = "updated_on"
        ordering = (
            "-updated_on",
            "-created_on",
        )
        abstract = True


class ModerationBase(ModelBase):
    """ModerationBase
    An abstract base class model that provides the "status" fields.
    """

    status = models.PositiveSmallIntegerField(
        default=ModerationStatesChoices.UNDER_REVIEW,
        choices=ModerationStatesChoices.choices,
        help_text="Status of any object in the database in the context of moderation"
    )

    class Meta:
        abstract = True

