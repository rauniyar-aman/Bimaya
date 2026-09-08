"""Provider-facing API endpoints (``/api/v1/provider/``)."""

from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.generics import GenericAPIView
from rest_framework.response import Response

from .access import IsProviderTeamMember, provider_for
from .analytics import build_provider_analytics
from .exceptions import ProviderProfileNotFound
from .models import ProviderRole
from .serializers import ProviderProfileSerializer

PROVIDER_TAG = ["provider"]


@extend_schema(tags=PROVIDER_TAG, summary="Own provider profile")
class ProviderProfileView(GenericAPIView):
    """Retrieve or upsert the acting user's provider company profile.

    ``GET`` returns the organisation's profile to any of its members (owner,
    staff or viewer), or 404 (``provider_profile_missing``) when the owner has
    not created one yet — the frontend uses that to show the setup form.
    ``PUT``/``PATCH`` is owner-only: it creates the profile on first save and
    updates it thereafter, with the owning user taken from the request.
    """

    serializer_class = ProviderProfileSerializer
    permission_classes = [IsProviderTeamMember]
    # Only the organisation owner may create or edit the company profile; staff
    # and viewers can read it but not change it.
    write_roles = (ProviderRole.OWNER,)

    def get_object(self):
        return provider_for(self.request.user)

    def get(self, request):
        provider = self.get_object()
        if provider is None:
            raise ProviderProfileNotFound()
        return Response(self.get_serializer(provider).data)

    def put(self, request):
        return self._upsert(request, partial=False)

    def patch(self, request):
        return self._upsert(request, partial=True)

    def _upsert(self, request, partial):
        provider = self.get_object()
        is_create = provider is None
        serializer = self.get_serializer(
            provider, data=request.data, partial=partial and not is_create
        )
        serializer.is_valid(raise_exception=True)
        serializer.save(user=request.user)
        return Response(
            serializer.data,
            status=status.HTTP_201_CREATED if is_create else status.HTTP_200_OK,
        )


@extend_schema(
    tags=["analytics"],
    summary="Own provider analytics",
    responses=OpenApiTypes.OBJECT,
)
class ProviderAnalyticsView(GenericAPIView):
    """Analytics scoped to the signed-in provider's own policies.

    Totals, status breakdowns and a recent monthly trend, all filtered to the
    provider's book of business. 404 (``provider_profile_missing``) when the
    provider has not created a profile yet, mirroring the profile endpoint.
    """

    permission_classes = [IsProviderTeamMember]

    def get(self, request):
        provider = provider_for(request.user)
        if provider is None:
            raise ProviderProfileNotFound()
        return Response(build_provider_analytics(provider))
