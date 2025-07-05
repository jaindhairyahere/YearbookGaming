# Library Imports
from rest_framework.permissions import BasePermission


class LoggedInPermission(BasePermission):
    """
    Ensure user is LoggedIn
    """
    message = "User is not logged in"
    
    def has_permission(self, request, *args, **kwargs):
        """Check if the request.user is active (active means allowed to login)
        and is authenticated (logged in)

        Args:
            request (Request): The request object

        Returns:
            bool: If the user is logged in.
        """
        return  request.user.is_active and request.user.is_authenticated
    
    
class HasGroupPermission(BasePermission):
    """
    Ensure user is in required groups. These are view level permissions.
    """
    message = """You do not have enough permissions to perform this action. Try with a different action
    or account"""

    def has_permission(self, request, view):
        """Checks if the request.user object has permissions to access the given view
        by checking user's allowed groups against the required_groups attribute of the
        class based view. If user belongs to a group that is in the required groups, 
        then user is allowed to access the view. However, there will be cases when we
        want a user to be in a group called "SELF", where it could access the view only
        if the view is called with a key (primary_key of a model) belonging to that 
        particular user.
        In this app, this scenario is displayed by ADMIN_MODERATORS, and SIMPLE_MODERATORS,
        where admins could view what each individual simple moderator could view, all 
        combined together.

        Args:
            request (Request): a drf wrapped wsgi request
            view (APIView): the view which calls this permission
        
        Returns:
            bool: If the user's group is in required group
        """
        # Check if the user is logged in
        if not LoggedInPermission().has_permission(request):
            return False
            
        # Get a mapping of methods -> required group.
        required_groups_mapping = getattr(view, "required_groups", {})
        
        # Get the pk_class if any, and the pk from the request
        pk_class = getattr(view, "pk_class", None)
        pk = request.parser_context['kwargs'].get('pk', None)
        
        # Determine the required groups for this particular request method.
        required_groups = required_groups_mapping.get(request.method, [])
        if "*" in required_groups or request.method == "OPTIONS":
            return True

        # Get the user from the request
        moderating_user = request.user

        # Get the User's Group object from the user
        user_group = moderating_user.role.group
                
        # Check if the same user is requesting its profile
        allowed = False
        
        if "SELF" in required_groups and pk_class is not None and pk is not None:
            # Check if the object exists
            obj = pk_class.objects.filter(pk=pk).first()
            
            # Check if object's user and the request user are same
            allowed = obj is not None and ( obj.user == moderating_user)
        
        if pk is not None:
            allowed = allowed or (user_group.name in required_groups 
                                   or moderating_user.is_superuser 
                                   or user_group.name == "ADMIN_MODERATOR")
        else:
            allowed = allowed or (user_group.name in required_groups or moderating_user.is_superuser)
        # Return True if the user is in any of the required groups    
        return allowed