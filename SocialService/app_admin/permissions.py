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
        then user is allowed to access the view

        Args:
            request (Request): The request object

        Returns:
            bool: If the user's group is in required group
        """
        # Get a mapping of methods -> required group.
        required_groups_mapping = getattr(view, "required_groups", {})

        # Determine the required groups for this particular request method.
        required_groups = required_groups_mapping.get(request.method, [])
        if "*" in required_groups:
            return True

        # Get the user from the request
        moderating_user = request.user

        # Get the User's Group object from the user
        user_group = moderating_user.role.group
                
        # Return True if the user is in any of the required groups
        return user_group.name in required_groups or moderating_user.is_superuser or moderating_user.is_staff


