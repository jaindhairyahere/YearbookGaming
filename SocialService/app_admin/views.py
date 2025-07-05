# Library Imports
from django.contrib.auth import authenticate, login, logout
from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import APIView
from rest_framework.response import Response

# Project Imports
from app_admin import login, logout
from app_admin.serializers import  YearbookUserSerializer
from utils.functions import generate_access_token


class LoginView(APIView):
    """Class based View for Login and Authentication.
    
    Supported Methods:
        get: If user is authenticated, return its details; else message not logged-in
        post: Authenticate and login user using the auth token
        
    URLs: 
        - /login/
    """

    def get(self, request):
        """Returns user details if user is logged in
        
        Args:
            request (Request): the drf wrapped wsgi request
                query_params: {}
                
        URLs:
            GET /login/
        """
        if request.user.is_authenticated:
            # If user is logged in, serialize the user instance
            serializer = YearbookUserSerializer(instance=request.user)
            return Response(
                data={
                    "status": "success",
                    "message": "Fetched user details successfully",
                    "data": serializer.data
                },
                status=status.HTTP_200_OK)
        else:
            # Return empty response if user is not logged in
            return Response(
                data={
                    "status": "failure", 
                    "message": "You are not logged in"
                },
                status=status.HTTP_401_UNAUTHORIZED)

    def post(self, request):
        """Logs the user in the backend using a token. 
        
        Verifies the token by REST API call to the auth service
        If the user corrosponding to the token already exists, then simple login
        otherwise creates the related YearbookUser, YearbookPlayer, Role, Group objects
    
        Args:
            request (Request): the drf wrapped wsgi request
                data: {
                    'token' (string): The auth-token received from the auth-service,
                    'force' (boolean) : Should the login be forced over previous login, //(Optional)
                }
                
        URLs:
            POST /login/
        """
        # Check if user is already logged in
        if request.user.is_authenticated:
            if request.data.pop('force', False):
                ##### TODO - Depricate this (Very rare use). Also will have to handle model signalling. In use only for development maybe
                # If the user wants to over-ride existing login 
                # Set the user to be inactive
                request.user.set_inactive()
                # Log the user out. 
                logout(request)
            else:
                serializer = YearbookUserSerializer(request.user)
                return Response(
                    data={
                        "status": "success",
                        "message": "A user is already logged in. Logout first or add force==True in request body",
                        "data": serializer.data
                    },
                    status=status.HTTP_200_OK
                )
                
        # Fetch the login token from the request
        token = request.data.get('token')
        
        # Authenticate the user using the token
        user = authenticate(request, token=token)
        
        # If authentication failed, return failure
        if not user or not user.is_authenticated:
            return Response(
                data={
                    "status": "failure", 
                    "message":"Incorrect Token"
                    }, 
                status=status.HTTP_401_UNAUTHORIZED
                )
            
        # Mark the user to be logged in, if authenticated
        login(request, user)
        
        # Create the Json Web Token using user's id, expiry time, current time
        token = generate_access_token(user)
        
        # Create a response and set 'jwt' `token` in its cookie; Return the response
        response = Response(
            data={
                "status": "success", 
                "message": "User Logged in successfully",
                "data": YearbookUserSerializer(user).data
            }, 
            status=status.HTTP_200_OK
        )
        response.set_cookie(key='jwt', value=token, httponly=True)
        return response

        
class LogoutView(APIView):
    """Class based View for Login and Authentication.
    
    Supported Methods:
        get: Logs out the user
        delete: Soft delete the user
        
    URLs: 
        - /logout/
    """
    def get(self, request):
        """Logs out the user and flushes the session
        
        Args:
            request (Request): the drf wrapped wsgi request
                query_params: {}
                
        URLs:
            - GET /logout/
        """
        # Boolean storing logged in state
        logged_in = False
        
        # If the user is logged in, send the user_logout signal
        if request.user.is_authenticated:
            logged_in = True
        
        # Logout and return the response
        logout(request)
        
        # Generate logout token
        token = generate_access_token(None, intent="logout")
        
        # Create a response and set 'jwt' `token` in its cookie; Return the response
        response = Response(
            data={
                "status": "success", 
                "message": "Logout Successful" if logged_in else "User is not logged in"
            }, 
            status=status.HTTP_200_OK
        )
        response.set_cookie(key='jwt', value=token, httponly=True)
        
        return response
    
    def delete(self, request):
        """Soft deletes the user if logged in. 
        Sets is_active to false, and deleted_on to current time. 
        This is followed by logging the user out (by redirecting).
        
        #### TODO - Depricate this. See `app_admin.backends.AuthenticationBackends.authenticate`. Use AuthService to do user deletion tasks

        Args:
            request (Request): the drf wrapped wsgi request
                query_params: {}
                
        URLs:
            - DELETE /logout/
        """
        # Get the user
        user = request.user
        
        if not user.is_authenticated:
            # If user is not logged in
            return Response(
                data={
                    "status": "failure",
                    "message": "You are not logged in"
                    },
                status=status.HTTP_401_UNAUTHORIZED
                )
        
        # Set is_active to False, deleted_on to timezone.now()
        user.deleted_on = timezone.now()
        user.save()
        return self.get(request)