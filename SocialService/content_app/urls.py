"""Moderator URL Configuration. The `urlpatterns` list routes URLs to views"""

from django.urls import path
from rest_framework.urlpatterns import format_suffix_patterns

from content_app import views

# Declaring the app name
app_name = 'content_app'

urlpatterns = [
    path('content/', views.ContentAPI.as_view(), name="content_view"),
]

# Allow URLs to also respond to /url.json along with /url
urlpatterns = format_suffix_patterns(urlpatterns)