import requests
import json
from django.conf import settings

class SocialService:
    """REST-API to interact with the Social Service"""
    def __init__(self, urlpatterns):
        self._headers = None
        self.urlpatterns = urlpatterns
        
    @classmethod
    def update_moderation_status(cls, request, content, new_status):
        user = request.user

        url = settings.SOCIAL_SERVICE_URL
        url = url + "moderate_app/update_moderation_status/"
        
        payload = json.dumps({
            "user":{
                "role":{
                    "role_id": user.role.role_id
                }
            },
            "content": {
                "id": content.id,
                "status": new_status
            }
        })
        headers = {
            'Content-Type': 'application/json',
            'Cookie': 'csrftoken=zqEQKH9ODuW04Z3Qn54rPw9R8XaRTaQ9NnioqmEdoqaxiV4T781ommWqji3QQLGF',
            'HTTP_HOST': 'YearbookGaming_social_django'
        }

        response = requests.request("GET", url, headers=headers, data=payload)
        return json.loads(response.text) if (response is not None and response.text is not None) else None