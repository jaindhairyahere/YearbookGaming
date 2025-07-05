from django.apps import AppConfig, apps
from utils.management import create_permissions, add_permissions_to_group

class AppAdminConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'app_admin'
    permission_models = []
    
    def ready(self) -> None:
        create_permissions(self, apps)
        add_permissions_to_group(self, apps)