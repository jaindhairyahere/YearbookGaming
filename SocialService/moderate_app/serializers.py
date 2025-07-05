from rest_framework.serializers import ModelSerializer
from utils.serializers import RemoveDeletedModelSerializer
from content_app.serializers import YearbookUserSerializer, ContentSerializer
from moderate_app.models import ReportingTicket

class ReportingTicketSerializer(RemoveDeletedModelSerializer):
    user = YearbookUserSerializer()
    content = ContentSerializer()
    class Meta:
        model = ReportingTicket
        fields = ("content", "user")