from drf_spectacular.utils import extend_schema
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from .serializers import HealthSerializer


@extend_schema(
    tags=["system"], summary="Health check", auth=[], responses=HealthSerializer
)
@api_view(["GET"])
@permission_classes([AllowAny])
def health(request):
    """Liveness probe. The frontend calls this to confirm API connectivity."""
    return Response({"status": "ok", "service": "bimaya-api", "version": "1.0.0"})
