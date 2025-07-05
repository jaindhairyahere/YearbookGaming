# Library Imports
from django.contrib.contenttypes.models import  ContentType
from rest_framework import serializers

# Project Imports
from app_admin.models import Group, YearbookUser, Permission, Role, YearbookPlayer, Policy
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
        
class YearbookUserSerializer(RemoveDeletedModelSerializer):
    """Model Serializer for the django model `YearbookUser`."""
    role = RoleSerializer()
    class Meta:
        model = YearbookUser
        exclude = ("is_superuser", "username", "is_active", "is_staff", "groups", "user_permissions", )
        depth = 3

class PolicySerializer(RemoveDeletedModelSerializer):
    """Model Serializer for the django model `Policy`."""
    
    class Meta:
        model = Policy
        fields = ("__all__")
        

class YearbookPlayerSerializer(RemoveDeletedModelSerializer):
    """Model Serializer for the django model `YearbookPlayer`."""
    user = YearbookUserSerializer()
    policy = PolicySerializer()
    
    class Meta:
        model = YearbookPlayer
        fields = ("id", "user", "policy")
        depth = 2