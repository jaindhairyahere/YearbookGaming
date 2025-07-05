"""Moderator URL Configuration. The `urlpatterns` list routes URLs to views"""

from django.urls import path
from rest_framework.urlpatterns import format_suffix_patterns

from . import views

# Declaring the app name
app_name = 'app_admin'

urlpatterns = [
    path('login/', views.LoginView.as_view(), name="login"),
    path('logout/', views.LogoutView.as_view(), name="logout"),
]

# # Allow URLs to also respond to /url.json along with /url
# urlpatterns = format_suffix_patterns(urlpatterns)
