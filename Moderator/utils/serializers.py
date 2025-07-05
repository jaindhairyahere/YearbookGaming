from collections import defaultdict
from rest_framework.serializers import ModelSerializer, SerializerMethodField
from rest_framework.fields import empty
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError


class SerializerMethodField(SerializerMethodField):
    """An Advanced Serializer Method Field that also serves custom parameters to the method
    
    For example:

    class ExampleSerializer(self):
        extra_info = SerializerMethodField(
            method_name='get_extra_info_personalized',
            func_kwargs={
                "email": "Hello",
                "delimitter": "__$__"
            }
        )

        def get_extra_info_personalized(self, instance, **kwargs):
            context = self.context
            company = context.get("company", "YearbookGamingtoys")
            email = kwargs.get("email", None)
            delimitter = kwargs.get("delimitter", "|")
            return f"{instance.username}{delimitter}{email}@{company}.com"
    
    serializer = ExampleSerializer(instance, context={"company":"YearbookGaminginnovations"})
    """
    def __init__(self, method_name=None, **kwargs):
        self.func_kwargs = kwargs.pop('func_kwargs', {})
        super().__init__(method_name, **kwargs)

    def to_representation(self, value):
        method = getattr(self.parent, self.method_name)
        return method(value, **self.func_kwargs)
    
class ExcludeFieldModelSerializer(ModelSerializer):
    """Base Serializer that doesn't serialize an object if it's deleted"""
    def recursive_pop(self, data, exclude):
        """Recursively removes the `exclude` fields from the serialized data `data`
        and returns the modified object. 

        Args:
            data (dict): an object's serialized representation
            exclude (list[str/tuple]): List of fields as str to be excluded. If exclusion is 
                nested, then use (field, [subfields]) instead of str. 
                `subfields` is similar to `exclude` in structure

        Returns:
            dict: the modified version  of serialized data
        """
        if isinstance(data, list):
            return [self.recursive_pop(_data, exclude) for _data in data]
        for field in exclude:
            if isinstance(field, str) and field in data:
                data.pop(field)
            elif isinstance(field, list) or isinstance(field, tuple) and field[0] in data:
                field_name = field[0]
                field_subfields = field[1]
                data[field_name] = self.recursive_pop(data[field_name], field_subfields)
        return data

    def to_representation(self, instance):
        """Modifies how the serialization happens"""
        # Call the base class' to_representation() method to get the serialized 
        # representation of the instance
        data = super().to_representation(instance)
        # Exclude any fields if specified
        return self.recursive_pop(data, self.context.get('exclude', []))

class RemoveDeletedModelSerializer(ModelSerializer):
    """Base Serializer that doesn't serialize an object if it's deleted"""
    def to_representation(self, instance):
        """Modifies how the serialization happens"""
        if instance.deleted_on is not None:
            # Return an empty dictionary if the object has been deleted already
            return {}
        # Call the base class' to_representation() method to get the serialized 
        # representation of the instance
        return super().to_representation(instance)
    

class PermissionModelSerializer(RemoveDeletedModelSerializer):
    """Base Serializer that removes the fields that the user doesn't have permission of. 
    Permissions are allowed to be field level (codename={model}|{action}|{field}).
    """
    def __init__(self, instance=None, data=empty, 
                 assume_all_model_perms_dne=True, 
                 assume_all_no_request=True, **kwargs):
        """
        Args: Two extra arguments can be optionally supplied in the serializer
            1. assume_all_model_perms_dne (bool): Assume all permissions when no permissions 
                                        have been defined for that model. Defaults to True
            2. assume_all_no_request (bool): Assume all permissions when the request is not 
                                        passed in the context dictionary. Defaults to True
        """
        self.assume_all_model_perms_dne = assume_all_model_perms_dne
        self.assume_all_no_request = assume_all_no_request
        super().__init__(instance, data, **kwargs)
        
    def filter_using_permissions(self, data, action, app_label, action_alt=None):
        """Function to filter the `data` based on user's permission to do
        `action` on the `self.Meta.model` from `app_label`
        
        Args:
            self (PermissionModelSerializer): the serializer instance
            data (dict): the instance data in a dictionary format
            action (str): the action to be performed on the data
            app_label (str): the label of the app this model is from
            action_alt (str, Optional): an alternate name of the action. Defaults to None
        
        Returns:
            dict: The filtered data dictionary
        """
        if action_alt is None:
            action_alt = action
        
        # Initialize the errors
        errors = defaultdict(list)
        
        # Get the model name using the serializer instance
        model = self.Meta.model.__name__
        
        # Get the request from the serializer instance's context
        request = self.context.get("request", None)
        if request is None:
            # If no request is passed, user is not accessible, nor its permissions
            # hence, no filtering could be done. Return the unfiltered/No `data`
            return data if self.assume_all_no_request else {}, errors
        
        # Get the `ContentType` object using the model and app_label. Every permission
        # object is associated with a `ContentType` object. If this object doesn't exist,
        # then no permission has been set on this model. Hence return the unfiltered/No data
        contenttype = ContentType.objects.filter(model=model.lower(), app_label=app_label).first()
        if contenttype is None:
            return data if self.assume_all_no_request else {}, errors
        
        # Get the user from the request
        user = request.user
        
        # Check if any Model level permissions exist for the given action. If yes, directly return the data
        permission = contenttype.permission_set.filter(codename__istartswith=action).exists()
        if permission:
            return data, errors
        
        # Iterate through all the fields
        for field, value in dict(data).items():
            # Get the permission from the codename
            codename = f"{model}|"+f"{action}|{field}".lower()
            permission = contenttype.permission_set.filter(codename=codename).first()
            # Remove the field from the data if user doesn't have the permission
            if not user.has_perm(permission):
                data.pop(field)
                errors[field].append(f"User doesn't have the permissions to {action} this field")
        
        # Returned the filtered data dictionary, and errors
        return data, errors
        
    def to_representation(self, instance):
        """Get the dictionary (serialized) representation of the instance

        Args:
            instance (object): the instance to be serialized

        Returns:
            dict: the serialized instance, filterd with user permissions
        """
        # Get the app label from the instance
        app_label = instance._meta.app_label
        # Get the original representation of the instance
        data = super().to_representation(instance)
        # Filter the serialized data to get filtered data and errors (if any)
        data, errors = self.filter_using_permissions(data, "view", app_label, "retrieve")
        # Do Nothing if errors, because it's GET method
        if errors:
            pass
        # Return the filtered data
        return data
        
    def to_internal_value(self, data):
        """Get the dictionary (serialized) representation of the instance

        Args:
            instance (object): the instance to be serialized

        Returns:
            dict: the serialized instance, filterd with user permissions
        """
        # Get the app label from the serializer's meta attributes
        app_label = self.Meta.model._meta.app_label
        # Filter the serialized data to get filtered data and errors (if any)
        data, errors = self.filter_using_permissions(data, "change", app_label, "update")
        # Raise Validation error, because it's POST/PUT/PATCH method
        if errors:
            raise ValidationError(errors)
        # Update the instance with the data and return it
        return super().to_internal_value(data)