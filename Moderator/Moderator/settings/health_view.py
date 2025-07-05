from rest_framework.permissions import AllowAny
from rest_framework.views import APIView
from rest_framework.response import Response


class HealthCheckView(APIView):
    """
    Health check view
    """

    permission_classes = [
        AllowAny,
    ]

    def get(self, request):
        return Response({"message": "Healthy like Thor !!"})
