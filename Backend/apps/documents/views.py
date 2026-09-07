"""Customer KYC endpoints (``/api/v1/kyc/``).

The self-KYC endpoint is an upsert modelled on ``providers.ProviderProfileView``:
``GET`` returns the record (or 404 so the frontend shows the setup form) and
``PUT``/``PATCH`` creates it on first save and updates it thereafter. Editing a
verified self-KYC returns it to ``PENDING`` for re-review.
"""

from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.generics import CreateAPIView, GenericAPIView
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.response import Response

from apps.core.permissions import IsCustomer, IsVerified

from .exceptions import SelfKycNotFound
from .models import CustomerKyc
from .serializers import CustomerKycSerializer, CustomerKycWriteSerializer

KYC_TAG = ["kyc"]


@extend_schema(tags=KYC_TAG, summary="Own reusable KYC")
class SelfKycView(GenericAPIView):
    """Retrieve or upsert the signed-in customer's own (``is_self``) KYC."""

    permission_classes = [IsCustomer, IsVerified]
    parser_classes = [MultiPartParser, FormParser]
    serializer_class = CustomerKycWriteSerializer

    def get_object(self):
        return CustomerKyc.objects.filter(
            customer=self.request.user, is_self=True
        ).first()

    def get(self, request):
        kyc = self.get_object()
        if kyc is None:
            raise SelfKycNotFound()
        return Response(CustomerKycSerializer(kyc).data)

    def put(self, request):
        return self._upsert(request, partial=False)

    def patch(self, request):
        return self._upsert(request, partial=True)

    def _upsert(self, request, partial):
        kyc = self.get_object()
        is_create = kyc is None
        serializer = self.get_serializer(
            kyc, data=request.data, partial=partial and not is_create
        )
        serializer.is_valid(raise_exception=True)
        # Any edit to an already-reviewed record sends it back for re-review.
        instance = serializer.save(
            customer=request.user,
            is_self=True,
            status=CustomerKyc.Status.PENDING,
            review_note="",
        )
        return Response(
            CustomerKycSerializer(instance).data,
            status=status.HTTP_201_CREATED if is_create else status.HTTP_200_OK,
        )


@extend_schema(tags=KYC_TAG, summary="Create a beneficiary KYC")
class BeneficiaryKycCreateView(CreateAPIView):
    """Create a fresh ``is_self=False`` KYC for buying on someone else's behalf."""

    permission_classes = [IsCustomer, IsVerified]
    parser_classes = [MultiPartParser, FormParser]
    serializer_class = CustomerKycWriteSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        instance = serializer.save(
            customer=request.user,
            is_self=False,
            status=CustomerKyc.Status.PENDING,
        )
        return Response(
            CustomerKycSerializer(instance).data, status=status.HTTP_201_CREATED
        )
