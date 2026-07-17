from rest_framework import serializers
from .models import AdmissionEnquiry


class AdmissionEnquirySerializer(serializers.ModelSerializer):
    """Public-facing serializer for admission enquiries."""

    class Meta:
        model = AdmissionEnquiry
        fields = [
            "id", "registration_number", "applicant_name", "date_of_birth",
            "gender", "target_class", "parent_name", "parent_phone",
            "parent_email", "address", "source_of_enquiry", "preferred_branch",
            "curriculum", "scholarship_applied", "id_proof_document",
            "status", "submitted_at",
        ]
        read_only_fields = ["id", "registration_number", "status", "submitted_at"]


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
