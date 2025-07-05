"""Moderator URL Configuration. The `urlpatterns` list routes URLs to views"""

from django.urls import path
from rest_framework.urlpatterns import format_suffix_patterns
from . import views

# Declaring the app name
app_name = 'app_admin'

urlpatterns = [
    path('moderators/', views.ProfileView.as_view(), name="moderator-profile"),
    path('moderators/<int:pk>', views.ProfileView.as_view(), name="moderator-profile-by-id"),
    path('ticket_feed/', views.TicketFeedAPI.as_view(), name="ticket-feed"),
    path('tickets/', views.TicketHistoryAPI.as_view(), name="ticket-api-all"),
    path('tickets/moderator/<int:pk>', views.TicketHistoryAPI.as_view(), name="ticket-api-by-moderator-id"),
    path('tickets/id/<int:pk>', views.TicketViewAPI.as_view(), name="ticket-api-by-ticket-id"),
]

# Allow URLs to also respond to /url.json along with /url
# urlpatterns = format_suffix_patterns(urlpatterns)