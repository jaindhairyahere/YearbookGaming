from django.apps import AppConfig
from utils.choices import ChatPolicyChoices, FriendPolicyChoices

class AppAdminConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'app_admin'
    
    def ready(self) -> None:
        Policy = self.apps.get_model("app_admin", "Policy")
        policies = [(friend, chat) for friend in FriendPolicyChoices.choices for chat in ChatPolicyChoices.choices]
        try:
            existing_policies = Policy.objects.all().values_list("chat_policy", "friend_policy")
            Policy.objects.bulk_create([
                Policy(chat_policy=chat[0], friend_policy=friend[0]) 
                for friend, chat in policies
                if (chat[0], friend[0]) not in existing_policies])
        except:
            pass            