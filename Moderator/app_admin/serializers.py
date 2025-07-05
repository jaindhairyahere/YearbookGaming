# Library imports
from django.contrib.contenttypes.models import  ContentType
from rest_framework import serializers

# Project imports
from app_admin.models import Group, YearbookGamingUser, Permission, Role
from utils.serializers import (
    RemoveDeletedModelSerializer, PermissionModelSerializer, 
    SerializerMethodField
)


class ContentTypeSerializer(serializers.ModelSerializer):
    """Model Serializer for the internal django model `ContentType`.
    Useful when serializing `app_admin.Permission` objects which indeed 
    have a reference to `ContentType` objects"""
    class Meta:
        model = ContentType
        exclude = ("id", )

        
class PermissionSerializer(serializers.ModelSerializer):
    """Model Serializer for the proxy django model `Permission`.
    Useful when serializing `app_admin.Group` objects which indeed 
    have a many-to-many relationship with `Permission` objects"""
    content_type = ContentTypeSerializer()
    class Meta:
        model = Permission
        exclude = ("id", "codename", )


class GroupSerializer(serializers.ModelSerializer):
    """Model Serializer for the proxy django model `Group`.
    Useful when serializing `app_admin.Role` objects which indeed 
    have a one-to-one relationship with `Group` objects"""
    permissions = PermissionSerializer(many=True)
    class Meta:
        model = Group
        exclude = ("id", )
        depth = 1
        
        
class RoleSerializer(RemoveDeletedModelSerializer):
    """Model Serializer for the django model `Role`."""
    group = GroupSerializer()
    class Meta:
        model = Role
        fields = ("group",) 
        
        
class YearbookGamingUserSerializer(RemoveDeletedModelSerializer):
    """Model Serializer for the django model `YearbookGamingUser`."""
    role = RoleSerializer()
    moderator_id = SerializerMethodField()
    
    def get_moderator_id(self, user, **kwargs):
        return user.moderator.id
    class Meta:
        model = YearbookGamingUser
        exclude = ("id", "is_superuser", "is_active", "is_staff", "groups", "user_permissions")
        depth = 3