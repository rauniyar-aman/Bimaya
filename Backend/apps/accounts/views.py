"""Authentication and account API endpoints (``/api/v1/auth/``)."""

from django.conf import settings
from django.contrib.auth import get_user_model
from drf_spectacular.utils import OpenApiExample, OpenApiResponse, extend_schema
from rest_framework import status
from rest_framework.generics import GenericAPIView, RetrieveUpdateAPIView
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework_simplejwt.views import TokenRefreshView, TokenVerifyView

from .models import OTP
from .serializers import (
    ChangePasswordSerializer,
    EmailSerializer,
    LoginSerializer,
    LogoutSerializer,
    OTPVerifySerializer,
    PasswordResetConfirmSerializer,
    ProfileUpdateSerializer,
    RegisterSerializer,
    UserSerializer,
)
from .services import issue_otp

User = get_user_model()

AUTH_TAG = ["auth"]


def _tokens_for(user):
    """Issue a fresh access/refresh pair plus the serialised user."""
    refresh = LoginSerializer.get_token(user)
    return {
        "access": str(refresh.access_token),
        "refresh": str(refresh),
        "user": UserSerializer(user).data,
    }


def _with_dev_code(payload, otp):
    """Expose the OTP in the response during development only.

    There is no SMS gateway wired up in dev, so without this the signup flow
    could not be completed locally. ``OTP_RETURN_IN_RESPONSE`` defaults to
    ``DEBUG`` and must be false in production.
    """
    if otp is not None and settings.OTP_RETURN_IN_RESPONSE:
        payload["dev_otp"] = otp.code
    return payload


@extend_schema(
    tags=AUTH_TAG,
    summary="Register an account",
    description=(
        "Creates a customer or provider account and emails a verification code. "
        "The account cannot sign in until the code is confirmed."
    ),
    auth=[],
    responses={
        201: OpenApiResponse(
            description="Account created; verification code sent.",
            examples=[
                OpenApiExample(
                    "Created",
                    value={
                        "detail": "Account created. Enter the code we sent to verify it.",
                        "email": "sita@example.com",
                    },
                )
            ],
        )
    },
)
class RegisterView(GenericAPIView):
    serializer_class = RegisterSerializer
    permission_classes = [AllowAny]
    throttle_scope = "otp"

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        payload = {
            "detail": "Account created. Enter the code we sent to verify it.",
            "email": user.email,
        }
        return Response(
            _with_dev_code(payload, getattr(serializer, "otp", None)),
            status=status.HTTP_201_CREATED,
        )


@extend_schema(
    tags=AUTH_TAG,
    summary="Verify an account with its code",
    description="Confirms a registration code and signs the user straight in.",
    auth=[],
)
class VerifyOTPView(GenericAPIView):
    serializer_class = OTPVerifySerializer
    permission_classes = [AllowAny]
    throttle_scope = "otp"

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        return Response(
            {"detail": "Your account is verified. Welcome to Bimaya.", **_tokens_for(user)}
        )


@extend_schema(
    tags=AUTH_TAG,
    summary="Resend a verification code",
    description=(
        "Sends a fresh registration code. Always returns 200 so the endpoint "
        "cannot be used to discover which emails are registered."
    ),
    auth=[],
)
class ResendOTPView(GenericAPIView):
    serializer_class = EmailSerializer
    permission_classes = [AllowAny]
    throttle_scope = "otp"

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = User.objects.filter(email__iexact=serializer.validated_email()).first()
        otp = None
        if user is not None and not user.is_verified:
            otp = issue_otp(user, OTP.Purpose.REGISTER)

        payload = {"detail": "If that account needs verifying, a new code is on its way."}
        return Response(_with_dev_code(payload, otp))


@extend_schema(
    tags=AUTH_TAG,
    summary="Sign in",
    description="Exchanges email and password for an access/refresh token pair.",
    auth=[],
)
class LoginView(GenericAPIView):
    serializer_class = LoginSerializer
    permission_classes = [AllowAny]
    throttle_scope = "login"

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        return Response(serializer.validated_data)


@extend_schema(
    tags=AUTH_TAG,
    summary="Sign out",
    description="Blacklists the supplied refresh token so it can no longer be used.",
)
class LogoutView(GenericAPIView):
    serializer_class = LogoutSerializer
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response({"detail": "Signed out."}, status=status.HTTP_205_RESET_CONTENT)


@extend_schema(tags=AUTH_TAG, summary="Current user")
class MeView(RetrieveUpdateAPIView):
    """Read the signed-in user, or update their editable profile fields."""

    permission_classes = [IsAuthenticated]

    def get_object(self):
        return self.request.user

    def get_serializer_class(self):
        if self.request.method in ("PUT", "PATCH"):
            return ProfileUpdateSerializer
        return UserSerializer

    def update(self, request, *args, **kwargs):
        super().update(request, *args, **kwargs)
        # Always answer with the full user record so the client can refresh state.
        return Response(UserSerializer(request.user).data)


@extend_schema(
    tags=AUTH_TAG,
    summary="Change password",
    description="Changes the password of the signed-in user.",
)
class ChangePasswordView(GenericAPIView):
    serializer_class = ChangePasswordSerializer
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response({"detail": "Your password has been changed."})


@extend_schema(
    tags=AUTH_TAG,
    summary="Request a password reset code",
    description=(
        "Emails a reset code. Always returns 200 so the endpoint cannot be used "
        "to discover which emails are registered."
    ),
    auth=[],
)
class PasswordResetRequestView(GenericAPIView):
    serializer_class = EmailSerializer
    permission_classes = [AllowAny]
    throttle_scope = "otp"

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = User.objects.filter(email__iexact=serializer.validated_email()).first()
        otp = issue_otp(user, OTP.Purpose.RESET) if user is not None else None

        payload = {"detail": "If that account exists, a reset code is on its way."}
        return Response(_with_dev_code(payload, otp))


@extend_schema(
    tags=AUTH_TAG,
    summary="Set a new password with a reset code",
    auth=[],
)
class PasswordResetConfirmView(GenericAPIView):
    serializer_class = PasswordResetConfirmSerializer
    permission_classes = [AllowAny]
    throttle_scope = "otp"

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(
            {"detail": "Your password has been reset. You can now sign in."}
        )


@extend_schema(tags=AUTH_TAG, summary="Refresh an access token", auth=[])
class RefreshView(TokenRefreshView):
    """Rotates the refresh token (old one is blacklisted) and returns a new access token."""

    throttle_scope = "login"


@extend_schema(tags=AUTH_TAG, summary="Check whether a token is still valid", auth=[])
class VerifyTokenView(TokenVerifyView):
    pass
