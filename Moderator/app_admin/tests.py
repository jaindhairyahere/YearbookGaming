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
from app_admin.urls import urlpatterns as app_admin_urls


class AppAdminViewsTest(URLPatternsTestCase):
    databases = ['default',]
    urlpatterns = app_admin_urls
    def setUp(self):
        baseurl = f"api/v1/auth/"
        self.login_url = reverse("login")
        self.logout_url = reverse("logout")
        self.meta_url = reverse("meta")
        
    def test__get_auth_details_unauthorized(self):
        # Unauthorized Login
        data = {}
        response = self.client.get(self.login_url, data, format="json")
        self.assertEqual(response.status_code, HTTP_401_UNAUTHORIZED)
        self.assertEqual(response.data["status"], "failure")
    
    def test__login_wrong_token(self):
        # Try logging in using a simple moderator
        data = {
            "token": "token_by_wrong_token"
        }
        response = self.client.post(self.login_url, data, format="json")
        # Validate response metadata
        self.assertEqual(response.status_code, HTTP_401_UNAUTHORIZED)
        self.assertEqual(response.data["status"], "failure")
        # Validate if the object in the response already exists
        self.logout()
    
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
        id = login_resp.data["data"].get("Yearbook_id")
        self.assertTrue(YearbookUser.objects.filter(Yearbook_id=id).exists())
        return login_resp
    
    def test__get_auth_details_authorized(self):
        # Authorized login
        pass
    
    def test__login_simple_moderator(self):
        # Try logging in using a simple moderator
        self.login({"token":"token_by_simple_moderator"})
        self.logout()
    
    def test__soft_delete_user(self):
        resp = self.client.delete(self.login_url)
        self.assertEqual(resp.status_code, HTTP_401_UNAUTHORIZED)
        self.assertEqual(resp.data["status"], "failure")
        login_resp = self.login({"token":"token_by_simple_moderator"})
        id = login_resp.data["data"].get("Yearbook_id")
        user_pre = YearbookUser.objects.get(Yearbook_id=id)
        self.assertTrue(user_pre.is_active)
        resp = self.client.delete(self.login_url)
        user_post = YearbookUser.objects.get(Yearbook_id=id)
        self.assertEqual(resp.status_code, HTTP_200_OK)
        self.assertEqual(resp.data["status"], "success")
        self.assertFalse(user_post.is_active)
        self.assertIsNotNone(user_post.deleted_on)
        self.logout()


    def test__login_admin_moderator(self):
        # Try logging in using a admin moderator
        self.login({"token":"token_by_admin_moderator"})
        self.logout()
    
    def test__multiple_logins(self):
        login1 = self.login({"token":"token_by_simple_moderator"})
        login2 = self.login({"token":"token_by_admin_moderator"})
        self.assertEqual(
            login2.data["message"], 
            "A user is already logged in. Logout first or add force==True in request body")
        self.assertEqual(
            login1.data["data"].get("Yearbook_id"), login2.data["data"].get("Yearbook_id")
        )
        login2 = self.login({"token":"token_by_admin_moderator", "force": True})
        # self.assertEqual(login2.data.get("message"), "User Logged in successfully")
        self.assertNotEqual(
            login1.data["data"].get("Yearbook_id"), login2.data["data"].get("Yearbook_id")
        )
        
    def test__unallowed_requests_login(self):
        resp = self.client.patch(self.login_url)
        self.assertEqual(resp.status_code, HTTP_405_METHOD_NOT_ALLOWED)
        resp = self.client.put(self.login_url)
        self.assertEqual(resp.status_code, HTTP_405_METHOD_NOT_ALLOWED)
        resp = self.client.trace(self.login_url)
        self.assertEqual(resp.status_code, HTTP_405_METHOD_NOT_ALLOWED)
    
    def test__unallowed_requests_logout(self):
        resp = self.client.post(self.logout_url)
        self.assertEqual(resp.status_code, HTTP_405_METHOD_NOT_ALLOWED)
        resp = self.client.patch(self.logout_url)
        self.assertEqual(resp.status_code, HTTP_405_METHOD_NOT_ALLOWED)
        resp = self.client.put(self.logout_url)
        self.assertEqual(resp.status_code, HTTP_405_METHOD_NOT_ALLOWED)
        resp = self.client.delete(self.logout_url)
        self.assertEqual(resp.status_code, HTTP_405_METHOD_NOT_ALLOWED)
        resp = self.client.trace(self.logout_url)
        self.assertEqual(resp.status_code, HTTP_405_METHOD_NOT_ALLOWED)

class PermissionsTest(URLPatternsTestCase):
    databases = ['default',]
    urlpatterns = app_admin_urls

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
        id = login_resp.data["data"].get("Yearbook_id")
        self.assertTrue(YearbookUser.objects.filter(Yearbook_id=id).exists())
        return login_resp
          
    def populate__YearbookUser(self, objects, offset=3):
        roles = ["simple_moderator", "admin_moderator"]
        role_choices = random.choices(roles, weights=[0.8, 0.2], k=objects)
        for _n in range(offset, objects+offset):
            username = self.faker.unique.name()
            self.login({"token": f"{username}_token_by_{role_choices[_n-offset]}_{_n}"})
            self.logout()
            
    def populate(self, model, objects, **kwargs):
        getattr(self, f"populate__{model.__name__}")(objects, **kwargs)
    
    
    class View:
        def __init__(self, required_groups, pk_class):
            self.required_groups = required_groups
            self.pk_class = pk_class

    def setUp(self):
        self.login_url = reverse("login")
        self.logout_url = reverse("logout")
        self.meta_url = reverse("meta")
        self.faker = Faker()
        self.logged_in = LoggedInPermission()
        self.group = HasGroupPermission()
        self.factory = APIRequestFactory()
        YearbookUser.objects.all().delete()
        self.populate(YearbookUser, 5)
        
    def test__LoggedInPermission(self):
        request = self.factory.get(self.login_url)
        request.user = AnonymousUser()
        self.assertFalse(self.logged_in.has_permission(request))
        request.user = YearbookUser.objects.first()
        self.assertTrue(self.logged_in.has_permission(request))
        
    def test__HasGroupPermission(self):
        def _get_permission_request(method, path, mod_type, pk=None):
            req = getattr(self.factory, method)(path)
            req.user = YearbookUser.objects.filter(role__group__name=mod_type).first()
            req.parser_context = {"kwargs":{}}
            if pk is not None:
                req.parser_context["kwargs"]["pk"] = pk
            return req
        
        request = _get_permission_request("get", self.login_url, "SIMPLE_MODERATOR")
        view = self.View({
            "GET": ["*"],
            "POST": ["ADMIN_MODERATOR"],
        }, None)
        self.assertTrue(self.group.has_permission(request, view))

        request = _get_permission_request("get", self.login_url, "SIMPLE_MODERATOR")
        view = self.View({
            "GET": ["*"],
            "POST": ["ADMIN_MODERATOR"],
        }, None)
        self.assertTrue(self.group.has_permission(request, view))

        request = _get_permission_request("get", self.login_url, "ADMIN_MODERATOR")
        view = self.View({
            "GET": ["*"],
            "POST": ["ADMIN_MODERATOR"],
        }, None)
        self.assertTrue(self.group.has_permission(request, view))

        request = _get_permission_request("post", self.login_url, "SIMPLE_MODERATOR")
        view = self.View({
            "GET": ["*"],
            "POST": ["ADMIN_MODERATOR"],
        }, None)
        self.assertFalse(self.group.has_permission(request, view))

        request = _get_permission_request("post", self.login_url, "ADMIN_MODERATOR")
        view = self.View({
            "GET": ["*"],
            "POST": ["ADMIN_MODERATOR"],
        }, None)
        self.assertTrue(self.group.has_permission(request, view))