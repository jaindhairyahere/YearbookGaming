from utils.serializers import RemoveDeletedModelSerializer

from content_app.models import Content, UploadObject
from app_admin.serializers import YearbookGamingUserSerializer
from utils.functions import create_presigned_url_download, create_presigned_url_upload

class MediaSerializer(RemoveDeletedModelSerializer):
    class Meta:
        model = UploadObject
        fields = ("extension", "meta", "upload_complete")

    def to_representation(self, instance):
        ret = super().to_representation(instance)
        purpose = self.context["purpose"]
        if purpose=='upload':
            ret["presigned_url"] = create_presigned_url_upload(instance.s3_object_key)
        elif purpose=='download':
            ret["presigned_url"] = create_presigned_url_download(instance.s3_object_key)
        elif purpose=="internal":
            ret["s3_object_key"] = instance.s3_object_key
        return ret
        
class ContentSerializer(RemoveDeletedModelSerializer):
    """Serializer Class for Content Model"""
    medias = MediaSerializer(many=True)
    class Meta:
        model = Content
        fields = ['id', 'user', 'content_type', 'text', 'parent', 'medias', 'status']