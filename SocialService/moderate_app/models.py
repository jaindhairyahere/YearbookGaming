from django.db import models
from utils.models import TimeStampedModel
# Create your models here.

class ReportingTicket(TimeStampedModel):
    content = models.ForeignKey("content_app.Content", on_delete=models.CASCADE)
    user = models.ForeignKey("app_admin.YearbookUser", on_delete=models.SET_NULL, null=True)
