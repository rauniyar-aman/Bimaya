import secrets

from django.conf import settings
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
from django.db import models
from django.utils import timezone

from apps.core.models import TimeStampedModel

from .managers import UserManager


class User(AbstractBaseUser, PermissionsMixin):
    """Custom user: login by email, with a platform role for RBAC."""

    class Role(models.TextChoices):
        CUSTOMER = "CUSTOMER", "Customer"
        PROVIDER = "PROVIDER", "Insurance Provider"
        ADMIN = "ADMIN", "Administrator"

    email = models.EmailField(unique=True)
    phone = models.CharField(max_length=20, blank=True)
    full_name = models.CharField(max_length=150, blank=True)
    role = models.CharField(max_length=20, choices=Role.choices, default=Role.CUSTOMER)

    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    is_verified = models.BooleanField(
        default=False, help_text="Whether phone/email has been OTP-verified."
    )

    date_joined = models.DateTimeField(default=timezone.now)

    objects = UserManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []  # email + password are the only required fields

    class Meta:
        ordering = ["-date_joined"]

    def __str__(self):
        return self.email

    @property
    def is_customer(self):
        return self.role == self.Role.CUSTOMER

    @property
    def is_provider(self):
        return self.role == self.Role.PROVIDER

    @property
    def is_platform_admin(self):
        return self.role == self.Role.ADMIN


class OTP(TimeStampedModel):
    """One-time password for registration / login / password reset."""

    class Purpose(models.TextChoices):
        REGISTER = "REGISTER", "Registration"
        LOGIN = "LOGIN", "Login"
        RESET = "RESET", "Password reset"

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="otps")
    code = models.CharField(max_length=6)
    purpose = models.CharField(max_length=20, choices=Purpose.choices)
    expires_at = models.DateTimeField()
    is_used = models.BooleanField(default=False)
    attempts = models.PositiveSmallIntegerField(
        default=0, help_text="Failed verification attempts against this code."
    )

    class Meta(TimeStampedModel.Meta):
        indexes = [models.Index(fields=["user", "purpose", "is_used"])]

    @property
    def is_expired(self):
        return timezone.now() >= self.expires_at

    @property
    def is_locked(self):
        """True once too many wrong codes have been tried."""
        return self.attempts >= settings.OTP_MAX_ATTEMPTS

    def is_valid(self, code):
        if self.is_used or self.is_expired or self.is_locked:
            return False
        # Constant-time comparison so a wrong code cannot be found by timing.
        return secrets.compare_digest(str(self.code), str(code))

    def mark_used(self):
        self.is_used = True
        self.save(update_fields=["is_used", "updated_at"])

    def register_failed_attempt(self):
        self.attempts += 1
        self.save(update_fields=["attempts", "updated_at"])

    def __str__(self):
        return f"{self.user.email} · {self.get_purpose_display()}"
