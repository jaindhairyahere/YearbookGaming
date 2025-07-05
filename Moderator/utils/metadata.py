"""
The metadata API is used to allow customization of how `OPTIONS` requests
are handled. We currently provide a single default implementation that returns
some fairly ad-hoc information about the view.

Future implementations might use JSON schema or other definitions in order
to return this information in a more standardized way.
"""
from collections import OrderedDict

from rest_framework.metadata import SimpleMetadata
from django.core.exceptions import PermissionDenied
from django.http import Http404

from rest_framework import exceptions
from rest_framework.request import clone_request

class AdvancedMetaData(SimpleMetadata):
    """
    This is an advanced metadata implementation.
    It returns an ad-hoc set of information about the view.
    There are not any formalized standards for `OPTIONS` responses
    for us to base this on.
    """
    def determine_metadata(self, request, view):
        metadata = OrderedDict()
        metadata['name'] = view.get_view_name()
        metadata['description'] = view.get_view_description()
        metadata['renders'] = [renderer.media_type for renderer in view.renderer_classes]
        metadata['parses'] = [parser.media_type for parser in view.parser_classes]
        actions = self.determine_actions(request, view)
        if actions:
            metadata['actions'] = actions
        return metadata

    def determine_actions(self, request, view):
        """
        For generic class based views we return information about
        the fields that are accepted for all the allowed methods.
        """
        actions = {}
        for method in set(view.allowed_methods):
            view.request = clone_request(request, method)
            try:
                # Test global permissions
                if hasattr(view, 'check_permissions'):
                    view.check_permissions(view.request)
                # Test object permissions
                if method == 'PUT' and hasattr(view, 'get_object'):
                    view.get_object()
            except (exceptions.APIException, PermissionDenied, Http404):
                pass
            else:
                # If user has appropriate permissions for the view, include
                # appropriate metadata about the fields that should be supplied.
                doc = getattr(view, method.lower()).__doc__
                actions[method] = {}
                actions[method]["description"] = doc
                if hasattr(view, "get_serializer"):
                    serializer = view.get_serializer()
                    actions[method]["data"] = self.get_serializer_info(serializer)
            finally:
                view.request = request

        return actions