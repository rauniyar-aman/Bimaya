"""Serializers shared across apps."""

from rest_framework import serializers


class HealthSerializer(serializers.Serializer):
    """Shape of the ``/health/`` response."""

    status = serializers.CharField()
    service = serializers.CharField()
    version = serializers.CharField()
