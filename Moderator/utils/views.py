from collections import defaultdict
from rest_framework.decorators import APIView as BaseAPIView
from rest_framework.response import Response
from rest_framework.status import HTTP_200_OK
from utils.metadata import AdvancedMetaData
import utils.choices as choices

class APIView(BaseAPIView):
    metadata_class = AdvancedMetaData
    def get_view_description(self, html=False):
        """
        Given a view instance, return a textual description to represent the view.
        This name is used in the browsable API, and in OPTIONS responses.
        """
        # Description may be set by some Views, such as a ViewSet.
        description = getattr(self, 'description', None)
        if description is None:
            description = self.__class__.__doc__ or ''

        if html:
            return super().get_view_description(html)
        return description
    
class ChoicesView(APIView):
    def get(self, request):
        data = defaultdict(dict)
        for name, val in choices.__dict__.items():
            if name.endswith("Choices"):
                data[name] = { member:val[member] for member in val._member_names_}
        return Response(data=data, status=HTTP_200_OK)