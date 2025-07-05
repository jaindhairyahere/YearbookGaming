from django.apps import AppConfig, apps
from utils.management import create_permissions, add_permissions_to_group

class UserClientConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'user_client'
    permission_models = ["Content", "UploadObject"]
    actions = ["view", "add", "delete", "change"]
    
    def ready(self):
        create_permissions(self, apps=apps)
        add_permissions_to_group(self, apps=apps)
        