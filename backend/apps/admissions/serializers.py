from django.db import models
from rest_framework import serializers
from .models import AdmissionEnquiry


class AdmissionEnquirySerializer(serializers.ModelSerializer):
    """Public-facing serializer for admission enquiries."""
    parent_name = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    parent_phone = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    parent_email = serializers.EmailField(required=False, allow_null=True, allow_blank=True)

    class Meta:
        model = AdmissionEnquiry
        fields = "__all__"
        read_only_fields = ["id", "registration_number", "status", "submitted_at"]

    def create(self, validated_data):
        # Auto-fill empty strings for non-nullable char/text/email fields to prevent Postgres NOT NULL constraint errors
        for field in self.Meta.model._meta.fields:
            if isinstance(field, (models.CharField, models.TextField, models.EmailField)):
                if not field.null and field.name not in validated_data:
                    validated_data[field.name] = ""
        return super().create(validated_data)

    def update(self, instance, validated_data):
        for field in self.Meta.model._meta.fields:
            if isinstance(field, (models.CharField, models.TextField, models.EmailField)):
                if not field.null and field.name not in validated_data:
                    validated_data[field.name] = getattr(instance, field.name, "")
        return super().update(instance, validated_data)


class AdmissionEnquiryDetailSerializer(serializers.ModelSerializer):
    """Detailed serializer for admin view with all workflow fields."""

    documents_count = serializers.SerializerMethodField()
    interview_count = serializers.SerializerMethodField()

    class Meta:
        model = AdmissionEnquiry
        fields = "__all__"

    def get_documents_count(self, obj):
        return obj.documents.count() if hasattr(obj, 'documents') else 0

    def get_interview_count(self, obj):
        return obj.interviews.count() if hasattr(obj, 'interviews') else 0
