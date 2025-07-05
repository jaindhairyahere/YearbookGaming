# Library Imports
from django.contrib.auth.models import AnonymousUser
from django.utils.deprecation import MiddlewareMixin
from django.utils.functional import SimpleLazyObject
from rest_framework_simplejwt import authentication

# Project Imports
from utils.functions import get_set_user, get_set_token

class TokenAuthenticationMiddleware(MiddlewareMixin):
    """Middleware that processes the request to bind `user` and `token` attributes
    with the request. Earlier this was done collectively using the CSRFMiddleware, 
    SessionMiddleware, and the AuthenticationMiddleware. As we discontinue CSRF based
    logins and migrate towards JSoN Web Token based login, this middleware does the work
    of the above three middle wares.

    """
    def process_request(self, request, *args, **kwargs):
        """Preprocesses each request to bind `user` and `token` to it
        
        Args:
            request (HttpRequest): a wsgi request
        """
        # Create a new authentication instance
        authenticator = authentication.JWTAuthentication()
        try:
            # Try to authenticate the token, and get the (user, token) pair
            user, token = authenticator.authenticate(request)
        except Exception as e:
            # If token couldn't be authenticated, set user to be an instane of AnonymousUser
            user = AnonymousUser()
        # Bind the user with the request
        request.user = request._user = SimpleLazyObject(lambda: get_set_user(request, user))
        # Bind the token with the request
        request.token = SimpleLazyObject(lambda: get_set_token(request, token))