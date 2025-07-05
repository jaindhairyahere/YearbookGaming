from rest_framework import serializers
from user_client.models import ModerationTicket, YearbookGamingModerator, Content, UploadObject, TicketBoard
from utils.serializers import PermissionModelSerializer, \
    SerializerMethodField, ExcludeFieldModelSerializer
from utils.functions import create_presigned_url_download, create_presigned_url_upload

class MediaSerializer(PermissionModelSerializer):
    """Model Serializer for the django model `UploadObject`."""
    class Meta:
        model = UploadObject
        fields = ("s3_object_key", "extension", "meta", "upload_complete")

    def to_representation(self, instance):
        ret = super().to_representation(instance)
        purpose = self.context.get("purpose", "")
        if purpose=='upload':
            ret.pop('s3_object_key')
            ret["presigned_url"] = create_presigned_url_upload(instance.s3_object_key)
        elif purpose=='download':
            ret.pop('s3_object_key')
            ret["presigned_url"] = create_presigned_url_download(instance.s3_object_key)
        elif purpose=='internal':
            ret['s3_object_key'] = instance.s3_object_key
        return ret
        
class ContentSerializer(PermissionModelSerializer):
    """Model Serializer for the django model `Content`."""
    medias = MediaSerializer(many=True, read_only=True)
    class Meta:
        model = Content
        fields = ['id', 'user', 'content_type', 'text', 'parent', 'medias', 'status']
        
class ModerationTicketSerializer(PermissionModelSerializer, ExcludeFieldModelSerializer):
    """Model Serializer for the django model `ModerationTicket`."""
    content = ContentSerializer()
    class Meta:
        model = ModerationTicket
        fields = ("__all__")
        depth = 2   

class TicketBoardSerializer(PermissionModelSerializer):
    class Meta:
        model = TicketBoard
        fields = ("__all__")

class YearbookGamingModeratorSerializer(PermissionModelSerializer, ExcludeFieldModelSerializer):
    """Model Serializer for the django model `YearbookGamingUser`."""
    tickets = SerializerMethodField()
    last_logout = serializers.ReadOnlyField()
    board = SerializerMethodField()
    
    def get_board(self, instance, **kwargs):
        board = instance.user.board
        serializer = TicketBoardSerializer(board)
        return serializer.data
        
    def get_tickets(self, instance, **kwargs):
        tickets = instance.user.tickets
        serializer = ModerationTicketSerializer(tickets, context=self.context, many=True)
        return serializer.data
        
    class Meta:
        model = YearbookGamingModerator
        fields = ("user", "is_mod_available", "last_login", "last_logout", "board", "tickets", )
        depth = 3

