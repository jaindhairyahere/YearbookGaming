# Library Imports
from django.contrib.auth.backends import ModelBackend
from django.conf import settings

# Project Imports
from app_admin.models import YearbookPlayer, YearbookUser, Role, Group, Policy
from utils.dummy import get_dummy_data
from utils.functions import convert_perm_avcd_to_crud


class AuthenticationBackend(ModelBackend):
    """Custom authentication backend that supports authenticate method for YearbookUser
    which is not a password based login, but a auth-token based login. This class will
    serve as the authentication backend for entire project

    """
    def login_into_auth_serivce(self, token):
        """Makes a token authentication request to the Auth Service 
            Recieves a JSON response from the auth service. 
            Response = {
                "success": True/False, # If true
                "Yearbook_id": <int: id>,
                "role_id": <int: role>
                "group_name": <str: group_name>
            }
        Args:
            token (str): Auth token to be used to sign-in to auth service

        Returns:
            dict: auth-response from the Auth service against the auth-token
        """
        # pass , Returns Auth Service data {user_id, role} + {request.token}
        
        ### TODO - Implement a AUTH REQUEST. TBD after the Auth Service is written
        
        # Dummy data
        if settings.USE_DUMMY_LOGIN:
            return get_dummy_data(token)

    def authenticate(self, request, token=None, **kwargs):
        """Authenticates the incoming user from the request
        #### TODO - Add support for User/Moderator deleted. SOLVED - Add it in the Auth Service. Auth Service should send a "failure" status

        Args:
            request (Request): a drf wrapped wsgi request
            token (str, optional): Auth token sent by the client

        Returns:
            YearbookUser (or None): The logged in user if success, otherwise None 
        """
        chat_policy = request.data.get('chat_policy', 1)
        friend_policy = request.data.get('friend_policy', 1)
        if token is not None:
            # Send the auth token to auth service and try to authenticate
            response = self.login_into_auth_serivce(token)
            if response.pop('success', False):
                # Login Successful
                
                # Get the user's group
                group, _ = Group.objects.get_or_create(name=response.get('group_name'))
                
                # Get/Create the user's role
                role_id = response.get('role_id')
                role = Role.objects.filter(role_id=role_id).first()
                if role is None:
                    role, _ = Role.objects.get_or_create(role_id=role_id, group = group)
                
                # Get the Yearbook_id from the response
                Yearbook_id = response.get('Yearbook_id')
                
                # If Yearbook_id passed in kwargs, check if it is same as what recieved from auth service #TODO - Depricate this
                if kwargs.get('Yearbook_id', None) is not None:
                    assert(Yearbook_id == kwargs.get('Yearbook_id'))
                
               # Get/Create the base user. So what is happening here is that We are assuming that only
                # the `Yearbook_id` of any user is fixed, and always unique. Hence, we should identify a user 
                # only using the `Yearbook_id` and not using anything else. As of now `username` is also unique
                # but a chance that we allow the user to change its username should be supported
                # Get the user with the returned `Yearbook_id`
                base_user = YearbookUser.objects.filter(Yearbook_id=Yearbook_id).first()
                # Create the user (temporary) if doesn't exist
                if base_user is None:
                    base_user = YearbookUser(Yearbook_id=Yearbook_id)
                # Update the username, email, role of the user
                base_user.username = response.get('username')
                base_user.email = response.get('email')
                base_user.role = role
                # Save the user
                base_user.save()
                
                # Get the policy
                policy = Policy.objects.filter(chat_policy=chat_policy, friend_policy=friend_policy).first()
                if not policy:
                    policy = Policy.objects.create(chat_policy=chat_policy, friend_policy=friend_policy)

                # Get the relevant user type model on basis of role_id and get/create a client_user
                client_user, _ = YearbookPlayer.objects.get_or_create(user=base_user, policy=policy)
                
                # Login Success: If base_user and client_user are not none and base_user is allowed to be active
                if base_user and client_user and self.user_can_authenticate(base_user):
                    return base_user        
                
        # Login Failed: Return None object
        return None
     
    def has_perm(self, user_obj, perm, obj=None):
        """Checks if the user `user_obj` has the permission `perm`

        Args:
            user_obj (YearbookUser): The user object 
            perm (str or Permission): The permission to be checked, as a string or as an Permission object
            obj (_type_, optional): _description_. Defaults to None.

        Returns:
            bool: True if the user `user_obj` has the permission `perm` else False
        """
        if isinstance(perm, str):
            # Case where permission is a string
            # Dis-integrate the permission string into: app_label, perm_type, model_name, perm 
            app_label, perm_type, model_name, perm = convert_perm_avcd_to_crud(perm)
            if perm.find('__') == -1:
                # '__' will be found only in Field Level Permissions (codename = applabel_model.PType__FieldName)
                # Now check if the required perm_type is in the list of available perm_types
                perms = user_obj.role.group.permissions.filter(
                    content_type__app_label = app_label, content_type__model = model_name)
                ptypes = []
                for perm in perms:
                    ptypes.append(perm.codename.split('.')[1].split('__')[0].lower())
                return perm_type in ptypes
            return False
        else: 
            # Case where permission is a Permission instance. \
            # Simple list traversal to check if instance is in list of Permission objects 
            perms = user_obj.role.group.permissions.all()
            return perm in perms
         
    def has_module_perms(self, user_obj, app_label):
        """
        Return True if user_obj has any permissions in the given app_label and User is active (allowed to log-in).
        """
        return user_obj.is_active and user_obj.role.group.permissions.filter(content_type__app_label = app_label).count()
