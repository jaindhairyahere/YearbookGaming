# Library Imports
from django.contrib.auth.backends import ModelBackend
from django.conf import settings

# Project Imports
from app_admin.models import YearbookGamingUser,Role, Group
from user_client.models import YearbookGamingModerator
from utils.dummy import get_dummy_data

class AuthenticationBackend(ModelBackend):
    """Custom authentication backend that supports authenticate method for YearbookGamingUser
    which is not a password based login, but a auth-token based login. This class will
    serve as the authentication backend for entire project

    """
    def login_into_auth_serivce(self, token):
        """Makes a token authentication request to the Auth Service 
            Recieves a JSON response from the auth service. 
            Response = {
                "success": True/False, # If true \n
                "YearbookGaming_id": <int: id>, \n
                "role_id": <int: role> \n
                "group_name": <str: group_name> \n
            }
        
        #### TODO - Implement a AUTH REQUEST. TBD after the Auth Service is written
        
        Args:
            token (str): the auth-token passed by the client

        Returns:
            dict: auth-response from the Auth service against the auth-token
        """
        # Dummy data
        if settings.USE_DUMMY_LOGIN:
            return get_dummy_data(token)

        # Returns Auth Service data {user_id, role} + {request.token}
        pass

    def authenticate(self, request, token=None, **kwargs):
        """Authenticates the incoming user from the request
        #### TODO - Add support for User/Moderator deleted | SOLVED - Add it in the Auth Service. Auth Service should send a "failure" status

        Args:
            request (Request): a drf wrapped wsgi request
            token (str, optional): Auth token sent by the client

        Returns:
            YearbookGamingUser (or None): Return the logged in user if success, otherwise return None 
        """
        if token is not None:
            # Send the auth token to auth service and try to authenticate
            response = self.login_into_auth_serivce(token)
            if response.pop('success', False) and response.get('role_id', None) != 3:
                # Login Successful
                
                # Get the user's group
                group, _ = Group.objects.get_or_create(name=response.get('group_name'))
                
                # Get/Create the user's role
                role_id = response.get('role_id')
                role = Role.objects.filter(role_id=role_id).first()
                if role is None:
                    role, _ = Role.objects.get_or_create(role_id=role_id, group = group)
                
                # Get the YearbookGaming_id from the response
                YearbookGaming_id = response.get('YearbookGaming_id')
                
                # If YearbookGaming_id passed in kwargs, check if it is same as what recieved from auth service #TODO - Depricate this
                if kwargs.get('YearbookGaming_id', None) is not None:
                    assert(YearbookGaming_id == kwargs.get('YearbookGaming_id'))
                
                # Get/Create the base user. So what is happening here is that We are assuming that only
                # the `YearbookGaming_id` of any user is fixed, and always unique. Hence, we should identify a user 
                # only using the `YearbookGaming_id` and not using anything else. As of now `username` is also unique
                # but a chance that we allow the user to change its username should be supported
                # Get the user with the returned `YearbookGaming_id`
                base_user = YearbookGamingUser.objects.filter(YearbookGaming_id=YearbookGaming_id).first()
                # Create the user (temporary) if doesn't exist
                if base_user is None:
                    base_user = YearbookGamingUser(YearbookGaming_id=YearbookGaming_id)
                # Update the username, email, role of the user
                base_user.username = response.get('username')
                base_user.email = response.get('email')
                base_user.role = role
                base_user.groups.add(group)
                # Save the user
                base_user.save()
                
                # Get the relevant user type model on basis of role_id and get/create a client_user
                client_user, _ = YearbookGamingModerator.objects.get_or_create(user=base_user)
                
                # Login Success: If base_user and client_user are not none and base_user is allowed to be active
                if base_user and client_user and self.user_can_authenticate(base_user):
                    return base_user        
                
        # Login Failed: Return None object
        return None
     
    def has_perm(self, user_obj, perm, obj=None):
        """Checks if the user `user_obj` has the permission `perm`

        Args:
            user_obj (YearbookGamingUser): The user object 
            perm (Permission): The permission to be checked, as an Permission object 
            ##### TODO - Support for when perm is a string
            obj (_type_, optional): _description_. Defaults to None.

        Returns:
            bool: True if the user `user_obj` has the permission `perm` else False
        """
        # Case where permission is a Permission instance. \
        # Simple list traversal to check if instance is in list of Permission objects 
        perms = user_obj.role.group.permissions.all()
        return perm in perms
         
    def has_module_perms(self, user_obj, app_label):
        """
        Return True if user_obj has any permissions in the given app_label and User is active (allowed to log-in).
        """
        return user_obj.is_active and user_obj.role.group.permissions.filter(content_type__app_label = app_label).count()
