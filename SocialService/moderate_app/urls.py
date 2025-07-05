"""Moderator URL Configuration. The `urlpatterns` list routes URLs to views"""

from django.urls import path
from rest_framework.urlpatterns import format_suffix_patterns

from moderate_app import views
# Declaring the app name
app_name = 'moderate_app'

urlpatterns = [
    path('report_user/<int:user_id>/', views.report_user, name="report_user_using_id"), # Reports another user by its id
    path('block_user/<int:user_id>/', views.block_user, name="block_user_using_id"), # Handles content retrieve, update
    path('update_moderation_status/', views.update_moderation_status, name="update_moderation_status"),
]

# Allow URLs to also respond to /url.json along with /url
urlpatterns = format_suffix_patterns(urlpatterns)