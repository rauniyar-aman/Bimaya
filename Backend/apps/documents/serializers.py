"""Serializers for customer KYC (personal details + identity document upload)
and provider KYC (a company's registration / tax / licensing documents)."""

import os

from rest_framework import serializers

from .models import CustomerKyc, ProviderKyc


class CustomerKycSerializer(serializers.ModelSerializer):
    """Read shape for a KYC record, with document image URLs."""

    class Meta:
        model = CustomerKyc
        fields = (
            "id",
            "is_self",
            "full_name",
            "email",
            "phone",
            "date_of_birth",
            "marital_status",
            "family_details",
            "temporary_address",
            "permanent_address",
            "document_type",
            "document_number",
            "document_front",
            "document_back",
            "status",
            "review_note",
            "created_at",
            "updated_at",
        )
        read_only_fields = fields


class CustomerKycWriteSerializer(serializers.ModelSerializer):
    """Create/update shape (multipart). ``customer``/``status`` are server-set.

    Enforces the per-document-type image rules that the model's ``clean`` also
    guards, so the API returns a friendly field error rather than a 500.
    """

    class Meta:
        model = CustomerKyc
        fields = (
            "id",
            "full_name",
            "email",
            "phone",
            "date_of_birth",
            "marital_status",
            "family_details",
            "temporary_address",
            "permanent_address",
            "document_type",
            "document_number",
            "document_front",
            "document_back",
        )

    def validate(self, attrs):
        document_type = attrs.get(
            "document_type", getattr(self.instance, "document_type", None)
        )
        # On a partial update the front image may already be on the instance.
        front = attrs.get("document_front", getattr(self.instance, "document_front", None))
        back = attrs.get("document_back", getattr(self.instance, "document_back", None))

        if not front:
            raise serializers.ValidationError(
                {"document_front": "An image of your document is required."}
            )
        if document_type == CustomerKyc.DocumentType.CITIZENSHIP and not back:
            raise serializers.ValidationError(
                {"document_back": "Both sides of the citizenship are required."}
            )
        return attrs


class ProviderKycSerializer(serializers.ModelSerializer):
    """Read shape for a provider KYC document.

    The file itself is **not** exposed as a URL — it is confidential company
    paperwork streamed only through the authenticated, scoped download endpoints
    (provider-side and admin-side). ``file_name`` is the original filename, for
    display; ``uploaded_by_email`` names the member who uploaded it.
    """

    document_type_display = serializers.CharField(
        source="get_document_type_display", read_only=True
    )
    status_display = serializers.CharField(
        source="get_status_display", read_only=True
    )
    file_name = serializers.SerializerMethodField()
    uploaded_by_email = serializers.SerializerMethodField()

    class Meta:
        model = ProviderKyc
        fields = (
            "id",
            "document_type",
            "document_type_display",
            "file_name",
            "status",
            "status_display",
            "review_note",
            "uploaded_by_email",
            "reviewed_at",
            "created_at",
            "updated_at",
        )
        read_only_fields = fields

    def get_file_name(self, obj) -> str:
        return os.path.basename(obj.file.name) if obj.file else ""

    def get_uploaded_by_email(self, obj) -> str | None:
        return obj.uploaded_by.email if obj.uploaded_by_id else None


class ProviderKycUploadSerializer(serializers.ModelSerializer):
    """Create shape (multipart) for a provider KYC document.

    ``provider``, ``status`` and ``uploaded_by`` are server-set in the view; the
    uploader only chooses the document type and the file.
    """

    class Meta:
        model = ProviderKyc
        fields = ("id", "document_type", "file")
