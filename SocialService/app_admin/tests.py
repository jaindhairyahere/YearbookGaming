from django.test import TestCase, RequestFactory
from app_admin.models import YearbookUser, YearbookPlayer
from django.contrib.auth.models import AnonymousUser
from rest_framework import status
from rest_framework.test import APIRequestFactory
from app_admin.views import LoginView, logout_view, MetaInfo
# Create your tests here.

class LoginFlowTest(TestCase):
    def setUp(self):
        self.django_factory = RequestFactory()
        self.factory = APIRequestFactory()
    
    def test_post_token_not_provided(self):
        django_request = self.django_factory.post(
            path='/app_admin/login', 
            data={
            })
        django_request.user = AnonymousUser()
        
        django_response = LoginView.as_view()(django_request)
        
        self.assertEqual(django_request.status_code, status.HTTP_400_BAD_REQUEST)
    
    def test_post_token_wrong_provided(self):
        django_request = self.django_factory.post(
            path='/app_admin/login', 
            data={
                "token": "token_is_a_wrong_token"
            })
        django_request.user = AnonymousUser()
        
        django_response = LoginView.as_view()(django_request)
        
        self.assertEqual(django_request.status_code, status.HTTP_400_BAD_REQUEST)