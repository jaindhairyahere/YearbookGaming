from django.contrib import admin
from app_admin.forms import TokenAuthenticationForm
from app_admin.models import YearbookGamingUser, Role
from utils.functions import convert_perm_crud_to_avcd
# Register your models here.

admin.autodiscover()

# Set a different login form and login template for admin portal
admin.site.login_form = TokenAuthenticationForm
admin.site.login_template = "./login.html"


class YearbookGamingUserAdmin(admin.ModelAdmin):
    """Custom Model Admin class so that we are able to customize the admin portal.
    This inherits from ModelAdmin and overrides the `get_model_perms` method. This was
    important because our Permission objects don't have an AVCD permission naming convention
    or model level permissions, and instead have CRUD style field level permissions
    """
    def get_model_perms(self, request):
        """Return if the user permission's as a dict of {perm_type: bool} denoting 
        if the user has AVCD permissions for the model `self.opts.model_name`. This is
        currently a fake implementation, because it assumes if user is able to {perm_action}
        any field of the model, then it must be able to do {perm_action} on the whole model. 
        Now such an assumption is True if we allow only application superusers (developers) to
        use the admin portal; but in general, this is a wrong/fake/buggy design/code.
        
        Args:
            request (Request): The DRF wrapped wsgi request object

        Returns:
            dict(str, bool): If user has AVCD permissions for the model `self.opts.model_name`
            
        ### TODO - Customize ModelAdmin and Admin Templates so that we don't have to do this fake implementation
        """
        # Get all permissions using the super class implementations
        original_perms = super().get_model_perms(request)
        # Get all Permission objects for the current model
        perms = request.user.role.group.permissions.filter(content_type__model = self.opts.model_name)
        # Go through all the permissions
        for perm in perms:
            # If user is able to {perm_action} any field of the model, 
            # then it must be able to do {perm_action} on the whole model
            ptype, model, field, perm_name = convert_perm_crud_to_avcd(perm.codename)
            original_perms[ptype] = True
        return original_perms

# Register the models using our custom ModelAdmin
admin.site.register(YearbookGamingUser, YearbookGamingUserAdmin)
# admin.site.register(YearbookGamingModerator, YearbookGamingUserAdmin)
# admin.site.register(YearbookGamingPlayer, YearbookGamingUserAdmin)
admin.site.register(Role, YearbookGamingUserAdmin)
# admin.site.register(ModerationTicket, YearbookGamingUserAdmin)