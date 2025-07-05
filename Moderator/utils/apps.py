from django.apps import AppConfig as BaseAppConfig, apps
from utils.management import create_permissions

class AppConfig(BaseAppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    
    def ready(self):
        create_permissions(self, apps=apps)
        