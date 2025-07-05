# Library Imports
from django.contrib.auth.models import AnonymousUser
from django.test import TestCase, RequestFactory, Client
from django.urls import reverse
from faker import Faker
import pdb
import random
from rest_framework.status import *
from rest_framework.test import APITestCase, APIRequestFactory, APIClient, URLPatternsTestCase

# Project Imports
from app_admin.models import *
from app_admin.permissions import *
from app_admin.views import *
from user_client.urls import urlpatterns as user_client_urls

class UserClientViewsTest(URLPatternsTestCase):
    databases = ['default',]
    urlpatterns = user_client_urls
    def setUp(self):
        baseurl = f"api/v1/client/"
        self.view_all_moderators = reverse("moderator-profile")
        self.view_moderator_by_id = reverse("moderator-profile-by-id")
        self.ticket_feed = reverse("ticket-feed")
        self.get_all_tickets = reverse("ticket-api-all")
        self.get_tickets_by_moderator = reverse("ticket-api-by-moderator-id")
        self.get_ticket_by_id = reverse("ticket-api-by-ticket-id")
        
    def logout(self):
        logout_resp = self.client.get(self.logout_url, {}, format="json")
        self.assertEqual(logout_resp.status_code, HTTP_200_OK)
        self.assertEqual(logout_resp.data["status"], "success")
        return logout_resp
        
    def login(self, data):
        login_resp = self.client.post(self.login_url, data, format="json")
        # Validate response metadata
        self.assertEqual(login_resp.status_code, HTTP_200_OK)
        self.assertEqual(login_resp.data["status"], "success")
        # Validate if the object in the response already exists
        id = login_resp.data["data"].get("YearbookGaming_id")
        self.assertTrue(YearbookGamingUser.objects.filter(YearbookGaming_id=id).exists())
        return login_resp
    
    def test__fetch_tickets(self):
        count = random.randint(1, 4)
        self.login(data={"token": "token_by_simple_moderator"})
        resp = self.client.get(self.ticket_feed, data={"num_tickets": count})
        