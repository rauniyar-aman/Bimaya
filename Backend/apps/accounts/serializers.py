"""Serializers for registration, verification, login and profile management."""

import re

from django.contrib.auth import get_user_model, password_validation
from django.db import transaction
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework_simplejwt.token_blacklist.models import (
    BlacklistedToken,
    OutstandingToken,
)
from rest_framework_simplejwt.tokens import RefreshToken

from .exceptions import AccountNotVerified
from .models import OTP
from .services import OTPError, consume_otp, issue_otp

User = get_user_model()

# Ceiling for uploaded profile pictures; mirrored by the frontend file picker.
AVATAR_MAX_BYTES = 5 * 1024 * 1024  # 5 MB


def _phone_taken(phone, *, exclude_pk=None):
    """Whether ``phone`` already belongs to another (non-blank) account."""
    others = User.objects.filter(phone=phone)
    if exclude_pk is not None:
        others = others.exclude(pk=exclude_pk)
    return others.exists()


class UserSerializer(serializers.ModelSerializer):
    """The authenticated user's own record (``/auth/me``).

    ``permissions`` and ``staff_roles`` are derived, read-only fields: they let
    the frontend render permission-aware navigation without an extra call. They
    are empty for customers and providers, and are never client-settable. The
    backend still authorises every request on its own — these are for display.
    """

    permissions = serializers.SerializerMethodField()
    staff_roles = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = (
            "id",
            "email",
            "full_name",
            "phone",
            "avatar",
            "role",
            "is_verified",
            "date_joined",
            "permissions",
            "staff_roles",
        )
        read_only_fields = (
            "id",
            "email",
            "avatar",
            "role",
            "is_verified",
            "date_joined",
        )

    def get_permissions(self, obj):
        # Imported here to avoid a circular import (staff imports accounts' User).
        from apps.staff.services import staff_permissions

        return sorted(staff_permissions(obj))

    def get_staff_roles(self, obj):
        from apps.staff.services import staff_role_values

        return staff_role_values(obj)


class ProfileUpdateSerializer(serializers.ModelSerializer):
    """Editable profile fields. Email and role are deliberately immutable here."""

    # ``allow_null`` lets the client clear the picture with ``{"avatar": null}``;
    # a multipart upload replaces it. The 5 MB ceiling matches the frontend
    # picker — the backend enforces it too, since that is the real boundary.
    avatar = serializers.ImageField(required=False, allow_null=True)

    class Meta:
        model = User
        fields = ("full_name", "phone", "avatar")

    def validate_avatar(self, image):
        if image is not None and image.size > AVATAR_MAX_BYTES:
            raise serializers.ValidationError(
                "That image is over 5 MB. Please choose a smaller file."
            )
        return image

    def validate_phone(self, value):
        # A phone number is unique per account. Clearing it is allowed (stored
        # as "", which the unique constraint exempts); a non-empty number must
        # not already belong to a *different* account.
        phone = value.strip()
        if phone and _phone_taken(phone, exclude_pk=self.instance.pk):
            raise serializers.ValidationError(
                "An account with this mobile number already exists."
            )
        return phone


class RegisterSerializer(serializers.ModelSerializer):
    """Create an account. The user must then confirm an OTP before signing in."""

    password = serializers.CharField(write_only=True, style={"input_type": "password"})
    confirm_password = serializers.CharField(
        write_only=True, style={"input_type": "password"}
    )
    # A mobile number is mandatory at registration and unique to the account —
    # it is how we reach customers for OTPs and policy updates. (Declared here,
    # rather than left to the model, so it is required and not blank.)
    phone = serializers.CharField(max_length=20)

    class Meta:
        model = User
        # Public registration only ever creates a customer. Providers are
        # onboarded by an administrator (see apps.leads), and administrators are
        # created internally — so ``role`` is deliberately not client-supplied.
        fields = (
            "email",
            "full_name",
            "phone",
            "password",
            "confirm_password",
        )

    def validate_email(self, value):
        email = User.objects.normalize_email(value).lower()
        if User.objects.filter(email__iexact=email).exists():
            raise serializers.ValidationError(
                "An account with this email already exists."
            )
        return email

    def validate_phone(self, value):
        phone = value.strip()
        # Light sanity check — reject obvious non-numbers without being strict
        # about formatting (users may include a country code, spaces or dashes).
        if len(re.sub(r"\D", "", phone)) < 7:
            raise serializers.ValidationError("Enter a valid mobile number.")
        if _phone_taken(phone):
            raise serializers.ValidationError(
                "An account with this mobile number already exists."
            )
        return phone

    def validate(self, attrs):
        if attrs["password"] != attrs["confirm_password"]:
            raise serializers.ValidationError(
                {"confirm_password": "The two passwords do not match."}
            )
        # Run Django's validators against a throw-away instance so rules like
        # "too similar to your email" can be applied.
        password_validation.validate_password(
            attrs["password"],
            User(
                email=attrs.get("email", ""),
                full_name=attrs.get("full_name", ""),
            ),
        )
        return attrs

    @transaction.atomic
    def create(self, validated_data):
        validated_data.pop("confirm_password")
        password = validated_data.pop("password")
        user = User.objects.create_user(password=password, **validated_data)
        self.otp = issue_otp(user, OTP.Purpose.REGISTER)
        return user


class EmailSerializer(serializers.Serializer):
    """Just an email — used to request a new code or a password reset."""

    email = serializers.EmailField()

    def validated_email(self):
        return self.validated_data["email"].strip().lower()


class OTPVerifySerializer(serializers.Serializer):
    """Confirm a registration code and activate the account."""

    email = serializers.EmailField()
    code = serializers.CharField(min_length=4, max_length=8)

    def validate(self, attrs):
        user = User.objects.filter(email__iexact=attrs["email"].strip()).first()
        if user is None:
            raise serializers.ValidationError(
                {"email": "No account was found for this email."}
            )
        try:
            consume_otp(user, attrs["code"], OTP.Purpose.REGISTER)
        except OTPError as error:
            raise serializers.ValidationError({"code": error.message}) from error

        attrs["user"] = user
        return attrs

    def save(self, **kwargs):
        user = self.validated_data["user"]
        if not user.is_verified:
            user.is_verified = True
            user.save(update_fields=["is_verified"])
        return user


class LoginSerializer(TokenObtainPairSerializer):
    """Email + password → access/refresh pair, with the user record attached."""

    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        # Handy claims so the frontend can render role-aware UI without an
        # extra round-trip. Never trust these for authorisation server-side.
        token["email"] = user.email
        token["role"] = user.role
        token["is_verified"] = user.is_verified
        return token

    def validate(self, attrs):
        data = super().validate(attrs)
        if not self.user.is_verified:
            raise AccountNotVerified()
        # Pass the request through so any avatar URL comes back absolute.
        data["user"] = UserSerializer(self.user, context=self.context).data
        return data


class LogoutSerializer(serializers.Serializer):
    """Blacklist a refresh token so it can no longer be rotated."""

    refresh = serializers.CharField()

    def validate_refresh(self, value):
        try:
            self.token = RefreshToken(value)
        except Exception as error:  # noqa: BLE001 — any decode failure is the same to callers
            raise serializers.ValidationError(
                "This refresh token is invalid or has already expired."
            ) from error
        return value

    def save(self, **kwargs):
        self.token.blacklist()


class ChangePasswordSerializer(serializers.Serializer):
    """Change the password of the signed-in user."""

    current_password = serializers.CharField(
        write_only=True, style={"input_type": "password"}
    )
    new_password = serializers.CharField(
        write_only=True, style={"input_type": "password"}
    )
    confirm_password = serializers.CharField(
        write_only=True, style={"input_type": "password"}
    )

    def validate_current_password(self, value):
        user = self.context["request"].user
        if not user.check_password(value):
            raise serializers.ValidationError("Your current password is not correct.")
        return value

    def validate(self, attrs):
        if attrs["new_password"] != attrs["confirm_password"]:
            raise serializers.ValidationError(
                {"confirm_password": "The two passwords do not match."}
            )
        password_validation.validate_password(
            attrs["new_password"], self.context["request"].user
        )
        return attrs

    def save(self, **kwargs):
        user = self.context["request"].user
        user.set_password(self.validated_data["new_password"])
        user.save(update_fields=["password"])
        return user


class PasswordResetConfirmSerializer(serializers.Serializer):
    """Set a new password using the code sent to the account's email."""

    email = serializers.EmailField()
    code = serializers.CharField(min_length=4, max_length=8)
    new_password = serializers.CharField(
        write_only=True, style={"input_type": "password"}
    )
    confirm_password = serializers.CharField(
        write_only=True, style={"input_type": "password"}
    )

    def validate(self, attrs):
        if attrs["new_password"] != attrs["confirm_password"]:
            raise serializers.ValidationError(
                {"confirm_password": "The two passwords do not match."}
            )

        user = User.objects.filter(email__iexact=attrs["email"].strip()).first()
        if user is None:
            raise serializers.ValidationError(
                {"code": "This reset code is not valid. Please request a new one."}
            )
        try:
            consume_otp(user, attrs["code"], OTP.Purpose.RESET)
        except OTPError as error:
            raise serializers.ValidationError({"code": error.message}) from error

        password_validation.validate_password(attrs["new_password"], user)
        attrs["user"] = user
        return attrs

    @transaction.atomic
    def save(self, **kwargs):
        user = self.validated_data["user"]
        user.set_password(self.validated_data["new_password"])
        # A password reset also proves control of the mailbox.
        user.is_verified = True
        user.save(update_fields=["password", "is_verified"])

        # Any session started with an old refresh token is no longer trusted.
        for token in OutstandingToken.objects.filter(user=user):
            BlacklistedToken.objects.get_or_create(token=token)
        return user
