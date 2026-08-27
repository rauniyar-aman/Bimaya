"""Payment endpoints (``/api/v1/payments/``)."""

from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.generics import GenericAPIView
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.permissions import IsCustomer, IsVerified

from .gateways import esewa, khalti
from .models import Payment
from .serializers import PaymentInitiateSerializer

PAYMENT_TAG = ["payments"]

GATEWAYS = {
    Payment.Gateway.ESEWA: esewa,
    Payment.Gateway.KHALTI: khalti,
}


@extend_schema(tags=PAYMENT_TAG, summary="Start a payment for a purchase")
class PaymentInitiateView(GenericAPIView):
    permission_classes = [IsCustomer, IsVerified]
    serializer_class = PaymentInitiateSerializer

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        purchase = serializer.validated_data["policy_purchase"]
        gateway = serializer.validated_data["gateway"]

        payment = Payment.objects.create(
            policy_purchase=purchase, amount=purchase.policy.premium, gateway=gateway
        )
        result = GATEWAYS[gateway].initiate(payment)
        return Response(
            {"payment_id": payment.id, "gateway": gateway, **result},
            status=status.HTTP_201_CREATED,
        )


@extend_schema(
    tags=PAYMENT_TAG,
    summary="Gateway payment callback",
    description="Hit by the payment gateway (eSewa/Khalti) directly, not the browser.",
)
class PaymentCallbackView(APIView):
    permission_classes = [AllowAny]

    def post(self, request, gateway):
        return self._handle(gateway, request.data)

    def get(self, request, gateway):
        return self._handle(gateway, request.query_params)

    def _handle(self, gateway_code, payload):
        gateway_code = gateway_code.upper()
        module = GATEWAYS.get(gateway_code)
        if module is None:
            return Response({"detail": "Unknown gateway."}, status=status.HTTP_404_NOT_FOUND)

        payment_id = module.resolve_payment_id(payload)
        payment = (
            Payment.objects.filter(id=payment_id, gateway=gateway_code)
            .select_related("policy_purchase", "policy_purchase__policy")
            .first()
            if payment_id is not None
            else None
        )
        if payment is None:
            return Response({"detail": "Payment not found."}, status=status.HTTP_404_NOT_FOUND)

        if payment.status == Payment.Status.SUCCESS:
            return Response({"detail": "Already processed.", "status": payment.status})

        if module.verify(payload):
            transaction_id = (
                payload.get("transaction_code")
                or payload.get("ref_id")
                or payload.get("transaction_id")
                or payload.get("pidx")
                or f"{gateway_code}-{payment.id}"
            )
            payment.mark_success(transaction_id)
            return Response({"detail": "Payment confirmed.", "status": payment.status})

        payment.mark_failed()
        return Response({"detail": "Payment verification failed.", "status": payment.status})
