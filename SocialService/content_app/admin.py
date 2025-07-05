# Library Imports
from django.contrib import admin

# Project Imports
from content_app.models import React, Content, UploadObject


# Register your models here.
admin.site.register(React)
admin.site.register(Content)
admin.site.register(UploadObject)
