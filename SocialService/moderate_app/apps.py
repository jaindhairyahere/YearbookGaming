from django.apps import AppConfig


class ModerateAppConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'moderate_app'

    def ready(self):
        from moderate_app import receivers
    
