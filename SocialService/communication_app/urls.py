"""Moderator URL Configuration. The `urlpatterns` list routes URLs to views"""

from django.urls import path
from rest_framework.urlpatterns import format_suffix_patterns

# from content_app.views import ContentView, ChannelView
from communication_app import views

# Declaring the app name
app_name = 'content_app'

urlpatterns = [
    # path('setup_channel/', ContentView.as_view(), name="moderator_Get"), # Handles content list view
    path('channels/', views.SubscriptionView.as_view()),
    path('requests/', views.RequestView.as_view()),
    path('friends/', views.FriendsListView.as_view(), name='get_all_friends'),
]

# Allow URLs to also respond to /url.json along with /url
urlpatterns = format_suffix_patterns(urlpatterns)