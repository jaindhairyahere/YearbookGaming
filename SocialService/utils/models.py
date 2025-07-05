from django.db import models
from utils.choices import ModerationStatesChoices


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


class TimeStampedModel(models.Model):
    """TimeStampedModel
    An abstract base class model that provides self-managed "created" and
    "modified" fields.
    """

    created_on = models.DateTimeField(auto_now_add=True, db_column="created_on")
    updated_on = models.DateTimeField(auto_now=True, db_column="updated_on")
    deleted_on = models.DateTimeField(null=True, db_column="deleted_on", default=None)    
    
    class Meta:
        get_latest_by = "updated_on"
        ordering = (
            "-updated_on",
            "-created_on",
        )
        abstract = True


class ModerationBase(models.Model):
    """ModerationBase
    An abstract base class model that provides self-managed "status" fields.
    """

    status = models.IntegerField(
        choices=ModerationStatesChoices.choices,
        default=ModerationStatesChoices.UNDER_REVIEW,
    )

    class Meta:
        abstract = True

