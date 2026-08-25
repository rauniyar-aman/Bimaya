from django.contrib.auth.forms import BaseUserCreationForm
from django.contrib.auth.forms import UserChangeForm as DjangoUserChangeForm

from .models import User


class UserCreationForm(BaseUserCreationForm):
    """Admin 'add user' form for the email-based custom user."""

    class Meta(BaseUserCreationForm.Meta):
        model = User
        fields = ("email", "full_name", "phone", "role")


class UserChangeForm(DjangoUserChangeForm):
    """Admin 'change user' form."""

    class Meta(DjangoUserChangeForm.Meta):
        model = User
        fields = "__all__"
