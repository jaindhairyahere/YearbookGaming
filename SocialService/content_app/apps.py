from django.apps import AppConfig


class ContentAppConfig(AppConfig):
    """App Config. Created the config object for the current django-application
    """
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'content_app'
    
    def ready(self):
        from content_app import receivers
    
