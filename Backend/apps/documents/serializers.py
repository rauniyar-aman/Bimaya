"""Serializers for customer KYC (personal details + identity document upload)."""

from rest_framework import serializers

from .models import CustomerKyc


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
