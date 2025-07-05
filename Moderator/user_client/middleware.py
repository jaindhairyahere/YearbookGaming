from user_client.models import YearbookModerator
from user_client.signals import user_is_active

class UserLoginEventMiddleware:
    """Middleware class which marks a user logged-in whenever there is a
    request from the user's client. Upon verifying the user as a moderator, 
    this middleware triggers the `user_is_active` signal, which then
    does some preprocessing on the backend.
    """
    def __init__(self, get_response):
        self.get_response = get_response
        # One-time configuration and initialization.

    def __call__(self, request):
        # Code to be executed for each request before
        # the view (and later middleware) are called.
        if request.user.is_authenticated:
            pre_request_auth = True
            
        response = self.get_response(request)

        # Send a `user_is_active` signal if the user is authenticated even after the request
        if request.user.is_authenticated:
            # the sender is set to be the current middleware class
            user_is_active.send_robust(sender=self.__class__, 
                                       moderator_id=request.user.moderator.id)
        
        return response