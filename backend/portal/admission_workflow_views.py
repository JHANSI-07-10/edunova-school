"""
Complete Admission Workflow Views
Covers all 18 phases of the admission process.
"""
import json
from datetime import date, datetime, timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.db import connection, transaction
from django.utils import timezone
from django.utils.crypto import get_random_string
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.admissions.models import (
    AdmissionEnquiry, AdmissionDocument, AdmissionInterview,
    AdmissionFee, AdmissionAllocation, AdmissionNotification,
)
from .roles import IsAdmin, get_role, log_action
from .views import row, rows, serialise, table_exists

User = get_user_model()


class AdmissionWorkflowMixin:
    """Shared helper for all admission workflow views."""
    permission_classes = [IsAdmin]

    def _get_enquiry(self, registration_number):
        try:
            return AdmissionEnquiry.objects.get(registration_number=registration_number)
        except AdmissionEnquiry.DoesNotExist:
            return None

    def _notify(self, enquiry, recipient_type, notification_type, title, message, channel="in_app"):
        """Create a notification record for the admission workflow."""
        try:
            AdmissionNotification.objects.create(
                enquiry=enquiry,
                recipient_type=recipient_type,
                notification_type=notification_type,
                title=title,
                message=message,
                channel=channel,
                is_sent=(channel != "in_app"),
                sent_at=timezone.now() if channel != "in_app" else None,
            )
        except Exception:
            pass

    def _send_email_notification(self, enquiry, notification_type, title, message):
        """Send email notification (best-effort, logs failure)."""
        try:
            from portal.services.email_service import send_status_email
            send_status_email(
                to_email=enquiry.parent_email,
                subject=title,
                body=message,
                template_name="account_status",
            )
            self._notify(enquiry, "Parent", notification_type, title, message, "email")
        except Exception:
            self._notify(enquiry, "Parent", notification_type, title, message, "in_app")

    def _log(self, user, action, reg_no, details=None):
        log_action(user, action, "admission", reg_no, details or {})


# ---------------------------------------------------------------------------
# Phase 1: Admission Enquiry Management (Admin view)
# ---------------------------------------------------------------------------
class AdmissionEnquiryAdminView(AdmissionWorkflowMixin, APIView):
    """GET: List all enquiries with filters. POST: Create enquiry from admin."""

    def get(self, request):
        qs = AdmissionEnquiry.objects.all().order_by("-submitted_at")
        
        status_filter = request.query_params.get("status")
        if status_filter:
            qs = qs.filter(status=status_filter)
        
        source_filter = request.query_params.get("source")
        if source_filter:
            qs = qs.filter(source_of_enquiry=source_filter)
        
        curriculum_filter = request.query_params.get("curriculum")
        if curriculum_filter:
            qs = qs.filter(curriculum=curriculum_filter)
        
        class_filter = request.query_params.get("target_class")
        if class_filter:
            qs = qs.filter(target_class=class_filter)
        
        search = request.query_params.get("search")
        if search:
            from django.db.models import Q
            qs = qs.filter(
                Q(applicant_name__icontains=search) |
                Q(parent_name__icontains=search) |
                Q(registration_number__icontains=search) |
                Q(parent_email__icontains=search)
            )
        
        data = list(qs.values(
            "registration_number", "applicant_name", "date_of_birth", "gender",
            "target_class", "parent_name", "parent_phone", "parent_email",
            "address", "source_of_enquiry", "preferred_branch", "curriculum",
            "scholarship_applied", "status", "counselling_status",
            "is_eligible", "interview_required", "interview_result",
            "seat_allocated", "allocated_class", "allocated_section",
            "fee_paid", "student_user_id", "parent_user_id",
            "rejection_reason", "submitted_at", "updated_at",
        ))
        return Response(serialise(data))

    def post(self, request):
        d = request.data
        reg_num = f"ADM-{get_random_string(8).upper()}"
        enquiry = AdmissionEnquiry.objects.create(
            registration_number=reg_num,
            applicant_name=d.get("applicant_name", ""),
            date_of_birth=d.get("date_of_birth", date.today()),
            gender=d.get("gender", ""),
            target_class=d.get("target_class", ""),
            parent_name=d.get("parent_name", ""),
            parent_phone=d.get("parent_phone", ""),
            parent_email=d.get("parent_email", ""),
            address=d.get("address", ""),
            source_of_enquiry=d.get("source_of_enquiry", "Walk-in"),
            preferred_branch=d.get("preferred_branch", ""),
            curriculum=d.get("curriculum", "CBSE"),
            scholarship_applied=d.get("scholarship_applied", False),
            status="Registered",
        )
        self._log(request.user, "admission.created", reg_num)
        return Response({"detail": "Admission enquiry created.", "registration_number": reg_num})


# ---------------------------------------------------------------------------
# Phase 2: Counselling Management
# ---------------------------------------------------------------------------
class AdmissionCounsellingView(AdmissionWorkflowMixin, APIView):
    """POST: Assign counsellor, schedule counselling, complete counselling."""

    def post(self, request, registration_number):
        enquiry = self._get_enquiry(registration_number)
        if not enquiry:
            return Response({"detail": "Application not found."}, status=404)
        
        action = request.data.get("action")
        
        if action == "assign_counsellor":
            counsellor_id = request.data.get("counsellor_id")
            enquiry.counsellor_id = counsellor_id
            enquiry.counselling_status = "Scheduled"
            enquiry.counselling_date = request.data.get("counselling_date")
            enquiry.counselling_notes = request.data.get("notes", "")
            enquiry.save(update_fields=[
                "counsellor_id", "counselling_status", "counselling_date",
                "counselling_notes", "updated_at"
            ])
            self._log(request.user, "admission.counsellor_assigned", registration_number, {
                "counsellor_id": counsellor_id
            })
            return Response(serialise({"status": "Counsellor assigned", "counselling_status": enquiry.counselling_status}))
        
        elif action == "complete_counselling":
            enquiry.counselling_status = "Completed"
            enquiry.counselling_notes = request.data.get("notes", enquiry.counselling_notes)
            enquiry.status = "Counselling_Done"
            enquiry.save(update_fields=["counselling_status", "counselling_notes", "status", "updated_at"])
            self._log(request.user, "admission.counselling_completed", registration_number)
            self._notify(enquiry, "Parent", "counselling_completed",
                        "Counselling Session Completed",
                        f"Counselling session for {enquiry.applicant_name} has been completed. Proceeding to next steps.")
            return Response(serialise({"status": "Counselling completed", "counselling_status": "Completed"}))
        
        elif action == "convert":
            enquiry.counselling_status = "Converted"
            enquiry.status = "Registered"
            enquiry.counselling_notes = request.data.get("notes", enquiry.counselling_notes)
            enquiry.save(update_fields=["counselling_status", "counselling_notes", "status", "updated_at"])
            self._log(request.user, "admission.counselling_converted", registration_number)
            return Response(serialise({"status": "Enquiry converted to application"}))
        
        return Response({"detail": "Unknown action. Use assign_counsellor, complete_counselling, or convert."}, status=400)

    def get(self, request, registration_number):
        """Get counselling details for an application."""
        enquiry = self._get_enquiry(registration_number)
        if not enquiry:
            return Response({"detail": "Application not found."}, status=404)
        
        counsellor_name = ""
        if enquiry.counsellor_id:
            counsellor = User.objects.filter(id=enquiry.counsellor_id).first()
            counsellor_name = counsellor.get_full_name() if counsellor else ""
        
        return Response(serialise({
            "registration_number": enquiry.registration_number,
            "counselling_status": enquiry.counselling_status,
            "counsellor_id": enquiry.counsellor_id,
            "counsellor_name": counsellor_name,
            "counselling_date": enquiry.counselling_date,
            "counselling_notes": enquiry.counselling_notes,
        }))


# ---------------------------------------------------------------------------
# Phase 4: Application Form Details
# ---------------------------------------------------------------------------
class AdmissionApplicationDetailView(AdmissionWorkflowMixin, APIView):
    """GET: Get full application details. POST/PUT: Save application form data."""

    def get(self, request, registration_number):
        enquiry = self._get_enquiry(registration_number)
        if not enquiry:
            return Response({"detail": "Application not found."}, status=404)
        
        result = serialise({
            "registration_number": enquiry.registration_number,
            "applicant_name": enquiry.applicant_name,
            "date_of_birth": str(enquiry.date_of_birth),
            "gender": enquiry.gender,
            "target_class": enquiry.target_class,
            "parent_name": enquiry.parent_name,
            "parent_phone": enquiry.parent_phone,
            "parent_email": enquiry.parent_email,
            "address": enquiry.address,
            "source_of_enquiry": enquiry.source_of_enquiry,
            "preferred_branch": enquiry.preferred_branch,
            "curriculum": enquiry.curriculum,
            "scholarship_applied": enquiry.scholarship_applied,
            "status": enquiry.status,
            "submitted_at": str(enquiry.submitted_at),
        })
        
        # Get extended application details from raw SQL
        if table_exists("portal_admission_application"):
            app_data = row(
                "SELECT * FROM portal_admission_application WHERE enquiry_id = %s",
                [enquiry.id]
            )
            if app_data:
                result["application"] = serialise(dict(app_data))
        
        # Get documents
        docs = list(AdmissionDocument.objects.filter(enquiry=enquiry).values(
            "id", "document_type", "document_name", "file_url",
            "is_verified", "uploaded_at"
        ))
        result["documents"] = serialise(docs)
        
        # Get interview
        interviews = list(AdmissionInterview.objects.filter(enquiry=enquiry).values(
            "id", "interview_date", "interview_type", "status",
            "marks_obtained", "max_marks", "recommendation", "remarks"
        ))
        result["interviews"] = serialise(interviews)
        
        # Get fee record
        fee = AdmissionFee.objects.filter(enquiry=enquiry).first()
        if fee:
            result["fee"] = serialise({
                "total_amount": str(fee.total_amount),
                "scholarship_discount": str(fee.scholarship_discount),
                "net_amount": str(fee.net_amount),
                "is_paid": fee.is_paid,
                "invoice_number": fee.invoice_number,
            })
        
        # Get allocation
        alloc = AdmissionAllocation.objects.filter(enquiry=enquiry).first()
        if alloc:
            result["allocation"] = serialise({
                "class_id": alloc.class_id,
                "section": alloc.section,
                "house": alloc.house,
                "roll_number": alloc.roll_number,
                "academic_year": alloc.academic_year,
            })
        
        return Response(result)

    def post(self, request, registration_number):
        """Save extended application form details (Phase 4)."""
        enquiry = self._get_enquiry(registration_number)
        if not enquiry:
            return Response({"detail": "Application not found."}, status=404)
        
        d = request.data
        
        # Update base enquiry fields
        if "applicant_name" in d:
            enquiry.applicant_name = d["applicant_name"]
        if "gender" in d:
            enquiry.gender = d["gender"]
        if "source_of_enquiry" in d:
            enquiry.source_of_enquiry = d["source_of_enquiry"]
        if "preferred_branch" in d:
            enquiry.preferred_branch = d["preferred_branch"]
        if "curriculum" in d:
            enquiry.curriculum = d["curriculum"]
        
        enquiry.status = "Verification"
        enquiry.reviewed_by = request.user.get_full_name() or request.user.username
        enquiry.save()
        
        # Save extended application data to raw SQL table
        if table_exists("portal_admission_application"):
            with connection.cursor() as cursor:
                cursor.execute("""
                    INSERT INTO portal_admission_application (
                        enquiry_id, blood_group, aadhaar_number, nationality,
                        religion, category, student_photo_url,
                        father_name, father_occupation, father_company, father_income,
                        father_phone, father_email,
                        mother_name, mother_occupation, mother_company,
                        mother_phone, mother_email,
                        guardian_name, guardian_relationship, guardian_phone, guardian_address,
                        permanent_address, communication_address, pin_code, state, district,
                        previous_school, board, previous_class, percentage,
                        transfer_certificate_url, reason_for_leaving,
                        allergies, medical_conditions,
                        emergency_contact_name, emergency_contact_phone, emergency_contact_relation
                    ) VALUES (
                        %s,%s,%s,%s,%s,%s,%s,
                        %s,%s,%s,%s,%s,%s,
                        %s,%s,%s,%s,%s,
                        %s,%s,%s,%s,%s,
                        %s,%s,%s,%s,%s,%s,
                        %s,%s,%s,%s,%s,%s,
                        %s,%s,%s,%s,%s
                    ) ON CONFLICT (enquiry_id) DO UPDATE SET
                        blood_group=EXCLUDED.blood_group, aadhaar_number=EXCLUDED.aadhaar_number,
                        nationality=EXCLUDED.nationality, religion=EXCLUDED.religion,
                        category=EXCLUDED.category, student_photo_url=EXCLUDED.student_photo_url,
                        father_name=EXCLUDED.father_name, father_occupation=EXCLUDED.father_occupation,
                        father_company=EXCLUDED.father_company, father_income=EXCLUDED.father_income,
                        father_phone=EXCLUDED.father_phone, father_email=EXCLUDED.father_email,
                        mother_name=EXCLUDED.mother_name, mother_occupation=EXCLUDED.mother_occupation,
                        mother_company=EXCLUDED.mother_company, mother_phone=EXCLUDED.mother_phone,
                        mother_email=EXCLUDED.mother_email,
                        guardian_name=EXCLUDED.guardian_name, guardian_relationship=EXCLUDED.guardian_relationship,
                        guardian_phone=EXCLUDED.guardian_phone, guardian_address=EXCLUDED.guardian_address,
                        permanent_address=EXCLUDED.permanent_address, communication_address=EXCLUDED.communication_address,
                        pin_code=EXCLUDED.pin_code, state=EXCLUDED.state, district=EXCLUDED.district,
                        previous_school=EXCLUDED.previous_school, board=EXCLUDED.board,
                        previous_class=EXCLUDED.previous_class, percentage=EXCLUDED.percentage,
                        transfer_certificate_url=EXCLUDED.transfer_certificate_url,
                        reason_for_leaving=EXCLUDED.reason_for_leaving,
                        allergies=EXCLUDED.allergies, medical_conditions=EXCLUDED.medical_conditions,
                        emergency_contact_name=EXCLUDED.emergency_contact_name,
                        emergency_contact_phone=EXCLUDED.emergency_contact_phone,
                        emergency_contact_relation=EXCLUDED.emergency_contact_relation,
                        updated_at=now()
                """, [
                    enquiry.id,
                    d.get("blood_group", ""), d.get("aadhaar_number", ""),
                    d.get("nationality", "Indian"), d.get("religion", ""),
                    d.get("category", "General"), d.get("student_photo_url", ""),
                    d.get("father_name", ""), d.get("father_occupation", ""),
                    d.get("father_company", ""), d.get("father_income", 0),
                    d.get("father_phone", ""), d.get("father_email", ""),
                    d.get("mother_name", ""), d.get("mother_occupation", ""),
                    d.get("mother_company", ""), d.get("mother_phone", ""),
                    d.get("mother_email", ""),
                    d.get("guardian_name", ""), d.get("guardian_relationship", ""),
                    d.get("guardian_phone", ""), d.get("guardian_address", ""),
                    d.get("permanent_address", ""), d.get("communication_address", ""),
                    d.get("pin_code", ""), d.get("state", ""), d.get("district", ""),
                    d.get("previous_school", ""), d.get("board", ""),
                    d.get("previous_class", ""), d.get("percentage", 0),
                    d.get("transfer_certificate_url", ""), d.get("reason_for_leaving", ""),
                    d.get("allergies", ""), d.get("medical_conditions", ""),
                    d.get("emergency_contact_name", ""), d.get("emergency_contact_phone", ""),
                    d.get("emergency_contact_relation", ""),
                ])
        
        self._log(request.user, "admission.application_submitted", registration_number)
        self._notify(enquiry, "Admission Team", "application_submitted",
                    "New Application Submitted",
                    f"Application {registration_number} from {enquiry.applicant_name} has been submitted for review.")
        
        return Response(serialise({"detail": "Application details saved.", "status": enquiry.status}))


# ---------------------------------------------------------------------------
# Phase 5: Document Upload & Verification
# ---------------------------------------------------------------------------
class AdmissionDocumentView(AdmissionWorkflowMixin, APIView):
    """GET: List documents. POST: Upload document. PATCH: Verify document."""

    def get(self, request, registration_number):
        enquiry = self._get_enquiry(registration_number)
        if not enquiry:
            return Response({"detail": "Application not found."}, status=404)
        
        docs = list(AdmissionDocument.objects.filter(enquiry=enquiry).values(
            "id", "document_type", "document_name", "file_url",
            "file_size", "file_type", "is_verified", "verification_notes",
            "uploaded_at", "verified_at"
        ))
        return Response(serialise(docs))

    def post(self, request, registration_number):
        enquiry = self._get_enquiry(registration_number)
        if not enquiry:
            return Response({"detail": "Application not found."}, status=404)
        
        d = request.data
        doc = AdmissionDocument.objects.create(
            enquiry=enquiry,
            document_type=d.get("document_type", "Other"),
            document_name=d.get("document_name", ""),
            file_url=d.get("file_url", ""),
            file_size=d.get("file_size", 0),
            file_type=d.get("file_type", ""),
        )
        
        if enquiry.status == "Registered":
            enquiry.status = "Verification"
            enquiry.save(update_fields=["status", "updated_at"])
        
        self._log(request.user, "admission.document_uploaded", registration_number, {
            "document_type": doc.document_type
        })
        return Response(serialise({"detail": "Document uploaded.", "id": doc.id}))

    def patch(self, request, registration_number, document_id):
        enquiry = self._get_enquiry(registration_number)
        if not enquiry:
            return Response({"detail": "Application not found."}, status=404)
        
        try:
            doc = AdmissionDocument.objects.get(id=document_id, enquiry=enquiry)
        except AdmissionDocument.DoesNotExist:
            return Response({"detail": "Document not found."}, status=404)
        
        d = request.data
        if "is_verified" in d:
            doc.is_verified = d["is_verified"]
            doc.verified_by = request.user.id
            doc.verification_notes = d.get("verification_notes", "")
            doc.verified_at = timezone.now()
            doc.save()
        
        self._log(request.user, "admission.document_verified", registration_number, {
            "document_type": doc.document_type, "is_verified": doc.is_verified
        })
        return Response(serialise({"detail": "Document updated.", "is_verified": doc.is_verified}))


# ---------------------------------------------------------------------------
# Phase 6: Eligibility Validation
# ---------------------------------------------------------------------------
class AdmissionEligibilityView(AdmissionWorkflowMixin, APIView):
    """POST: Validate eligibility. GET: Get eligibility status."""

    def post(self, request, registration_number):
        enquiry = self._get_enquiry(registration_number)
        if not enquiry:
            return Response({"detail": "Application not found."}, status=404)
        
        # Age validation
        today = date.today()
        age = today.year - enquiry.date_of_birth.year - (
            (today.month, today.day) < (enquiry.date_of_birth.month, enquiry.date_of_birth.day)
        )
        age_eligible = age >= 3
        age_reason = f"Age: {age} years. {'Eligible' if age_eligible else 'Minimum age is 3 years.'}"
        
        # Academic eligibility (check if previous class exists and percentage is valid)
        academic_eligible = True
        academic_reason = "No previous academic data provided."
        
        if table_exists("portal_admission_application"):
            app_data = row(
                "SELECT previous_class, percentage FROM portal_admission_application WHERE enquiry_id = %s",
                [enquiry.id]
            )
            if app_data and app_data.get("previous_class"):
                pct = app_data.get("percentage", 0) or 0
                academic_eligible = pct >= 35 or app_data["previous_class"] in ["Nursery", "LKG", "UKG", "Class 1"]
                academic_reason = f"Previous class: {app_data['previous_class']}, Percentage: {pct}%. {'Eligible' if academic_eligible else 'Minimum 35% required.'}"
        
        # Document eligibility
        doc_count = AdmissionDocument.objects.filter(enquiry=enquiry).count()
        docs_eligible = doc_count >= 2
        docs_reason = f"{doc_count} documents uploaded. {'Eligible' if docs_eligible else 'Minimum 2 documents required.'}"
        
        # Duplicate admission check
        duplicate_check = AdmissionEnquiry.objects.filter(
            parent_phone=enquiry.parent_phone,
            target_class=enquiry.target_class
        ).exclude(id=enquiry.id).exists()
        
        overall = age_eligible and academic_eligible and docs_eligible and not duplicate_check
        
        # Save eligibility result
        if table_exists("portal_admission_eligibility"):
            with connection.cursor() as cursor:
                cursor.execute("""
                    INSERT INTO portal_admission_eligibility (
                        enquiry_id, age_eligible, academic_eligible,
                        documents_eligible, overall_eligible,
                        age_reason, academic_reason, document_reason
                    ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s)
                    ON CONFLICT (enquiry_id) DO UPDATE SET
                        age_eligible=EXCLUDED.age_eligible, academic_eligible=EXCLUDED.academic_eligible,
                        documents_eligible=EXCLUDED.documents_eligible, overall_eligible=EXCLUDED.overall_eligible,
                        age_reason=EXCLUDED.age_reason, academic_reason=EXCLUDED.academic_reason,
                        document_reason=EXCLUDED.document_reason, validated_at=now()
                """, [
                    enquiry.id, age_eligible, academic_eligible,
                    docs_eligible, overall,
                    age_reason, academic_reason, docs_reason
                ])
        
        enquiry.is_eligible = overall
        enquiry.eligibility_notes = f"Age: {age_reason} | Academic: {academic_reason} | Docs: {docs_reason}"
        if overall:
            enquiry.status = "Eligibility_Check"
        enquiry.save(update_fields=["is_eligible", "eligibility_notes", "status", "updated_at"])
        
        self._log(request.user, "admission.eligibility_checked", registration_number, {
            "eligible": overall
        })
        
        return Response(serialise({
            "age_eligible": age_eligible,
            "age_reason": age_reason,
            "academic_eligible": academic_eligible,
            "academic_reason": academic_reason,
            "documents_eligible": docs_eligible,
            "documents_reason": docs_reason,
            "duplicate_check": duplicate_check,
            "overall_eligible": overall,
        }))

    def get(self, request, registration_number):
        enquiry = self._get_enquiry(registration_number)
        if not enquiry:
            return Response({"detail": "Application not found."}, status=404)
        
        result = {
            "is_eligible": enquiry.is_eligible,
            "eligibility_notes": enquiry.eligibility_notes,
        }
        
        if table_exists("portal_admission_eligibility"):
            elig = row("SELECT * FROM portal_admission_eligibility WHERE enquiry_id = %s", [enquiry.id])
            if elig:
                result.update(serialise(dict(elig)))
        
        return Response(serialise(result))


# ---------------------------------------------------------------------------
# Phase 7: Application Review
# ---------------------------------------------------------------------------
class AdmissionReviewView(AdmissionWorkflowMixin, APIView):
    """POST: Review application and update status."""

    REVIEW_STATUS_MAP = {
        "approve": "Screening",
        "require_interview": "Interview_Pending",
        "reject": "Rejected",
        "document_pending": "Verification",
    }

    def post(self, request, registration_number):
        enquiry = self._get_enquiry(registration_number)
        if not enquiry:
            return Response({"detail": "Application not found."}, status=404)
        
        action = request.data.get("action")
        new_status = self.REVIEW_STATUS_MAP.get(action)
        
        if not new_status:
            return Response({"detail": "Unknown action. Use approve, require_interview, reject, or document_pending."}, status=400)
        
        if action == "reject":
            enquiry.rejection_reason = request.data.get("reason", "")
        
        if action == "require_interview":
            interview_date = request.data.get("interview_date")
            if interview_date:
                AdmissionInterview.objects.create(
                    enquiry=enquiry,
                    interview_date=interview_date,
                    interview_type=request.data.get("interview_type", "Interview"),
                    status="Scheduled",
                )
                enquiry.interview_required = True
                enquiry.interview_scheduled = True
                enquiry.interview_date = interview_date
        
        enquiry.status = new_status
        enquiry.reviewed_by = request.user.get_full_name() or request.user.username
        enquiry.save()
        
        self._log(request.user, f"admission.review.{action}", registration_number)
        
        # Notify parent
        status_messages = {
            "approve": f"Your application {registration_number} has been approved and is moving to screening.",
            "require_interview": f"Your application {registration_number} requires an interview. Date: {request.data.get('interview_date', 'TBD')}",
            "reject": f"Your application {registration_number} has been rejected. Reason: {enquiry.rejection_reason}",
            "document_pending": f"Your application {registration_number} requires additional documents.",
        }
        self._send_email_notification(enquiry, f"application_{action}",
            f"Application {action.title()}", status_messages.get(action, ""))
        
        return Response(serialise({"status": enquiry.status, "action": action}))


# ---------------------------------------------------------------------------
# Phase 8: Interview / Assessment
# ---------------------------------------------------------------------------
class AdmissionInterviewView(AdmissionWorkflowMixin, APIView):
    """GET: List interviews. POST: Schedule/complete interview."""

    def get(self, request, registration_number):
        enquiry = self._get_enquiry(registration_number)
        if not enquiry:
            return Response({"detail": "Application not found."}, status=404)
        
        interviews = list(AdmissionInterview.objects.filter(enquiry=enquiry).values(
            "id", "interview_date", "interview_type", "status",
            "marks_obtained", "max_marks", "recommendation", "remarks",
            "parent_notified", "created_at"
        ))
        return Response(serialise(interviews))

    def post(self, request, registration_number):
        enquiry = self._get_enquiry(registration_number)
        if not enquiry:
            return Response({"detail": "Application not found."}, status=404)
        
        action = request.data.get("action")
        
        if action == "schedule":
            interview = AdmissionInterview.objects.create(
                enquiry=enquiry,
                interviewer_id=request.user.id,
                interview_date=request.data.get("interview_date"),
                interview_type=request.data.get("interview_type", "Interview"),
                status="Scheduled",
            )
            enquiry.interview_required = True
            enquiry.interview_scheduled = True
            enquiry.interview_date = request.data.get("interview_date")
            enquiry.status = "Interview_Pending"
            enquiry.save(update_fields=["interview_required", "interview_scheduled", "interview_date", "status", "updated_at"])
            
            self._send_email_notification(enquiry, "interview_scheduled",
                "Interview Scheduled",
                f"An interview for {enquiry.applicant_name} has been scheduled on {request.data.get('interview_date', 'TBD')}.")
            
            return Response(serialise({"detail": "Interview scheduled.", "interview_id": interview.id}))
        
        elif action == "complete":
            interview_id = request.data.get("interview_id")
            try:
                interview = AdmissionInterview.objects.get(id=interview_id, enquiry=enquiry)
            except AdmissionInterview.DoesNotExist:
                return Response({"detail": "Interview not found."}, status=404)
            
            interview.status = "Completed"
            interview.marks_obtained = request.data.get("marks_obtained", 0)
            interview.max_marks = request.data.get("max_marks", 100)
            interview.recommendation = request.data.get("recommendation", "")
            interview.remarks = request.data.get("remarks", "")
            interview.save()
            
            enquiry.interview_result = interview.recommendation
            enquiry.status = "Interview_Done"
            enquiry.save(update_fields=["interview_result", "status", "updated_at"])
            
            self._log(request.user, "admission.interview_completed", registration_number, {
                "recommendation": interview.recommendation
            })
            
            self._send_email_notification(enquiry, "interview_completed",
                "Interview Completed",
                f"Interview for {enquiry.applicant_name} completed. Result: {interview.recommendation}.")
            
            return Response(serialise({
                "detail": "Interview completed.",
                "recommendation": interview.recommendation,
                "marks": str(interview.marks_obtained),
            }))
        
        return Response({"detail": "Unknown action. Use schedule or complete."}, status=400)


# ---------------------------------------------------------------------------
# Phase 9: Seat Allocation
# ---------------------------------------------------------------------------
class AdmissionSeatAllocationView(AdmissionWorkflowMixin, APIView):
    """POST: Allocate seat. GET: Check availability."""

    def get(self, request, registration_number):
        """Get seat allocation status."""
        enquiry = self._get_enquiry(registration_number)
        if not enquiry:
            return Response({"detail": "Application not found."}, status=404)
        
        # Check seat availability for the target class
        target_class = enquiry.target_class
        available = True
        total_seats = 40
        occupied_seats = 0
        
        if table_exists("portal_student_enrollment") and table_exists("portal_class"):
            row_data = row("""
                SELECT COUNT(*)::int AS occupied
                FROM portal_student_enrollment se
                JOIN portal_class pc ON se.class_id = pc.id
                WHERE pc.name = %s AND se.academic_year = %s
            """, [target_class, str(date.today().year)])
            if row_data:
                occupied_seats = row_data.get("occupied", 0)
            available = occupied_seats < total_seats
        
        return Response(serialise({
            "target_class": target_class,
            "total_seats": total_seats,
            "occupied_seats": occupied_seats,
            "available": available,
            "seat_allocated": enquiry.seat_allocated,
            "allocated_class": enquiry.allocated_class,
            "allocated_section": enquiry.allocated_section,
            "is_waitlisted": enquiry.is_waitlisted,
            "waitlist_position": enquiry.waitlist_position,
        }))

    def post(self, request, registration_number):
        enquiry = self._get_enquiry(registration_number)
        if not enquiry:
            return Response({"detail": "Application not found."}, status=404)
        
        action = request.data.get("action")
        
        if action == "allocate":
            section = request.data.get("section", "A")
            target_class = enquiry.target_class
            
            # Check seat availability
            target_class = enquiry.target_class
            occupied = 0
            if table_exists("portal_student_enrollment") and table_exists("portal_class"):
                r = row("""
                    SELECT COUNT(*)::int AS occupied
                    FROM portal_student_enrollment se
                    JOIN portal_class pc ON se.class_id = pc.id
                    WHERE pc.name = %s AND se.academic_year = %s
                """, [target_class, str(date.today().year)])
                if r:
                    occupied = r.get("occupied", 0)
            
            if occupied >= 40:
                # Waitlist
                waitlist_count = AdmissionEnquiry.objects.filter(
                    is_waitlisted=True, target_class=target_class
                ).count()
                enquiry.is_waitlisted = True
                enquiry.waitlist_position = waitlist_count + 1
                enquiry.status = "Seat_Waitlisted"
                enquiry.save(update_fields=["is_waitlisted", "waitlist_position", "status", "updated_at"])
                
                self._notify(enquiry, "Parent", "seat_waitlisted",
                    "Seat Waitlisted",
                    f"Unfortunately, all seats for {target_class} are full. Your application has been placed on the waitlist at position {enquiry.waitlist_position}.")
                
                return Response(serialise({
                    "detail": "All seats full. Application waitlisted.",
                    "waitlist_position": enquiry.waitlist_position
                }))
            
            # Allocate seat
            enquiry.seat_allocated = True
            enquiry.allocated_class = target_class
            enquiry.allocated_section = section
            enquiry.is_waitlisted = False
            enquiry.status = "Seat_Available"
            enquiry.save(update_fields=[
                "seat_allocated", "allocated_class", "allocated_section",
                "is_waitlisted", "status", "updated_at"
            ])
            
            # Create allocation record
            AdmissionAllocation.objects.update_or_create(
                enquiry=enquiry,
                defaults={
                    "class_id": request.data.get("class_id"),
                    "section": section,
                    "academic_year": str(date.today().year),
                }
            )
            
            self._log(request.user, "admission.seat_allocated", registration_number, {
                "class": target_class, "section": section
            })
            
            self._send_email_notification(enquiry, "seat_allocated",
                "Seat Allocated",
                f"A seat has been allocated for {enquiry.applicant_name} in {target_class} - Section {section}.")
            
            return Response(serialise({
                "detail": "Seat allocated successfully.",
                "class": target_class, "section": section
            }))
        
        elif action == "waitlist":
            waitlist_count = AdmissionEnquiry.objects.filter(
                is_waitlisted=True, target_class=enquiry.target_class
            ).count()
            enquiry.is_waitlisted = True
            enquiry.waitlist_position = waitlist_count + 1
            enquiry.status = "Seat_Waitlisted"
            enquiry.save(update_fields=["is_waitlisted", "waitlist_position", "status", "updated_at"])
            return Response(serialise({"detail": "Application waitlisted.", "position": enquiry.waitlist_position}))
        
        return Response({"detail": "Unknown action."}, status=400)


# ---------------------------------------------------------------------------
# Phase 10: Admission Decision (Advance/Reject)
# ---------------------------------------------------------------------------
class AdmissionDecisionView(AdmissionWorkflowMixin, APIView):
    """POST: Make admission decision (approve, reject, waitlist)."""

    def post(self, request, registration_number):
        enquiry = self._get_enquiry(registration_number)
        if not enquiry:
            return Response({"detail": "Application not found."}, status=404)
        
        action = request.data.get("action")
        
        if action == "approve":
            enquiry.status = "Fee_Pending"
            enquiry.reviewed_by = request.user.get_full_name() or request.user.username
            enquiry.save(update_fields=["status", "reviewed_by", "updated_at"])
            
            # Generate fee structure
            fee_amount = request.data.get("fee_amount", 0)
            scholarship = request.data.get("scholarship_discount", 0)
            net = Decimal(str(fee_amount)) - Decimal(str(scholarship))
            
            AdmissionFee.objects.update_or_create(
                enquiry=enquiry,
                defaults={
                    "total_amount": fee_amount,
                    "scholarship_discount": scholarship,
                    "net_amount": net,
                    "fee_type": "Admission_Fee",
                    "invoice_number": f"INV-{get_random_string(6).upper()}",
                }
            )
            enquiry.fee_amount = fee_amount
            enquiry.scholarship_discount = scholarship
            enquiry.net_fee = net
            enquiry.save(update_fields=["fee_amount", "scholarship_discount", "net_fee", "updated_at"])
            
            self._log(request.user, "admission.approved", registration_number, {"fee": str(net)})
            self._send_email_notification(enquiry, "admission_approved",
                "Admission Approved!",
                f"Congratulations! Admission for {enquiry.applicant_name} has been approved. Fee: {net}. Please complete payment.")
            
            return Response(serialise({
                "status": "Fee_Pending",
                "fee_amount": str(fee_amount),
                "scholarship_discount": str(scholarship),
                "net_fee": str(net),
            }))
        
        elif action == "reject":
            enquiry.status = "Rejected"
            enquiry.rejection_reason = request.data.get("reason", "")
            enquiry.reviewed_by = request.user.get_full_name() or request.user.username
            enquiry.save()
            self._log(request.user, "admission.rejected", registration_number, {"reason": enquiry.rejection_reason})
            self._send_email_notification(enquiry, "admission_rejected",
                "Application Not Approved",
                f"We regret to inform you that the application for {enquiry.applicant_name} was not approved. Reason: {enquiry.rejection_reason}")
            return Response(serialise({"status": "Rejected"}))
        
        elif action == "waitlist":
            enquiry.status = "Seat_Waitlisted"
            enquiry.is_waitlisted = True
            enquiry.save(update_fields=["status", "is_waitlisted", "updated_at"])
            return Response(serialise({"status": "Seat_Waitlisted"}))
        
        return Response({"detail": "Unknown action."}, status=400)


# ---------------------------------------------------------------------------
# Phase 11: Fee Payment
# ---------------------------------------------------------------------------
class AdmissionFeePaymentView(AdmissionWorkflowMixin, APIView):
    """GET: Get fee details. POST: Process payment."""

    def get(self, request, registration_number):
        enquiry = self._get_enquiry(registration_number)
        if not enquiry:
            return Response({"detail": "Application not found."}, status=404)
        
        fee = AdmissionFee.objects.filter(enquiry=enquiry).first()
        if not fee:
            return Response({"detail": "No fee record found."}, status=404)
        
        return Response(serialise({
            "fee_type": fee.fee_type,
            "total_amount": str(fee.total_amount),
            "scholarship_discount": str(fee.scholarship_discount),
            "net_amount": str(fee.net_amount),
            "is_paid": fee.is_paid,
            "transaction_id": fee.transaction_id,
            "payment_method": fee.payment_method,
            "payment_date": str(fee.payment_date) if fee.payment_date else None,
            "invoice_number": fee.invoice_number,
        }))

    def post(self, request, registration_number):
        """Process fee payment."""
        enquiry = self._get_enquiry(registration_number)
        if not enquiry:
            return Response({"detail": "Application not found."}, status=404)
        
        fee = AdmissionFee.objects.filter(enquiry=enquiry).first()
        if not fee:
            return Response({"detail": "No fee record found."}, status=404)
        
        if fee.is_paid:
            return Response({"detail": "Fee already paid."}, status=400)
        
        d = request.data
        fee.is_paid = True
        fee.transaction_id = d.get("transaction_id", f"TXN-{get_random_string(12).upper()}")
        fee.payment_method = d.get("payment_method", "Online")
        fee.payment_date = timezone.now()
        fee.save(update_fields=["is_paid", "transaction_id", "payment_method", "payment_date"])
        
        enquiry.fee_paid = True
        enquiry.fee_transaction_id = fee.transaction_id
        enquiry.status = "Approved"
        enquiry.save(update_fields=["fee_paid", "fee_transaction_id", "status", "updated_at"])
        
        self._log(request.user, "admission.fee_paid", registration_number, {
            "amount": str(fee.net_amount),
            "transaction_id": fee.transaction_id
        })
        
        self._send_email_notification(enquiry, "fee_paid",
            "Fee Payment Received",
            f"Fee payment of {fee.net_amount} received for {enquiry.applicant_name}. Transaction ID: {fee.transaction_id}.")
        
        return Response(serialise({
            "detail": "Payment processed successfully.",
            "status": "Approved",
            "transaction_id": fee.transaction_id,
        }))


# ---------------------------------------------------------------------------
# Phase 12: Admission Confirmation & Account Generation
# ---------------------------------------------------------------------------
class AdmissionConfirmView(AdmissionWorkflowMixin, APIView):
    """POST: Confirm admission and generate student/parent accounts."""

    def post(self, request, registration_number):
        enquiry = self._get_enquiry(registration_number)
        if not enquiry:
            return Response({"detail": "Application not found."}, status=404)
        
        if enquiry.status not in ("Approved", "Fee_Pending"):
            return Response({"detail": f"Cannot confirm from status '{enquiry.status}'."}, status=400)
        
        # Check if already confirmed
        if enquiry.student_user_id:
            return Response({"detail": "Admission already confirmed.", "student_user_id": enquiry.student_user_id}, status=400)
        
        # Generate accounts
        from portal.admin_views import _generate_credentials
        student, parent, credentials = _generate_credentials(enquiry)
        
        enquiry.status = "Confirmed"
        enquiry.save(update_fields=["status", "updated_at"])
        
        # Generate roll number
        roll_num = f"R{str(enquiry.id).zfill(4)}"
        enquiry.student_roll_number = roll_num
        enquiry.save(update_fields=["student_roll_number", "updated_at"])
        
        self._log(request.user, "admission.confirmed", registration_number, {
            "student_user_id": student.id if student else None,
        })
        
        # Create notifications
        self._send_email_notification(enquiry, "admission_confirmed",
            "Admission Confirmed!",
            f"Admission for {enquiry.applicant_name} has been confirmed. Student username: {credentials.get('student_username', '')}.")
        
        # Create student notification
        AdmissionNotification.objects.create(
            enquiry=enquiry,
            recipient_type="Student",
            recipient_user_id=student.id if student else None,
            notification_type="welcome",
            title="Welcome to EduNova!",
            message=f"Welcome {enquiry.applicant_name}! Your admission has been confirmed.",
            channel="email",
            is_sent=True,
            sent_at=timezone.now(),
        )
        
        # Create parent notification
        AdmissionNotification.objects.create(
            enquiry=enquiry,
            recipient_type="Parent",
            recipient_user_id=parent.id if parent else None,
            notification_type="admission_confirmed",
            title="Admission Confirmed",
            message=f"Admission for {enquiry.applicant_name} has been confirmed. Login credentials have been sent to your email.",
            channel="email",
            is_sent=True,
            sent_at=timezone.now(),
        )
        
        return Response(serialise({
            "detail": "Admission confirmed successfully.",
            "status": "Confirmed",
            "credentials": credentials,
        }))


# ---------------------------------------------------------------------------
# Phase 14: Academic Allocation
# ---------------------------------------------------------------------------
class AdmissionAcademicAllocationView(AdmissionWorkflowMixin, APIView):
    """POST: Allocate class, section, house, subjects."""

    def get(self, request, registration_number):
        enquiry = self._get_enquiry(registration_number)
        if not enquiry:
            return Response({"detail": "Application not found."}, status=404)
        
        alloc = AdmissionAllocation.objects.filter(enquiry=enquiry).first()
        if not alloc:
            return Response(serialise({"allocated": False}))
        
        return Response(serialise({
            "allocated": True,
            "class_id": alloc.class_id,
            "section": alloc.section,
            "house": alloc.house,
            "class_teacher_id": alloc.class_teacher_id,
            "roll_number": alloc.roll_number,
            "academic_year": alloc.academic_year,
        }))

    def post(self, request, registration_number):
        enquiry = self._get_enquiry(registration_number)
        if not enquiry:
            return Response({"detail": "Application not found."}, status=404)
        
        d = request.data
        alloc, _ = AdmissionAllocation.objects.update_or_create(
            enquiry=enquiry,
            defaults={
                "student_user_id": enquiry.student_user_id,
                "class_id": d.get("class_id"),
                "section": d.get("section", "A"),
                "house": d.get("house", ""),
                "class_teacher_id": d.get("class_teacher_id"),
                "roll_number": d.get("roll_number"),
                "academic_year": d.get("academic_year", str(date.today().year)),
            }
        )
        
        enquiry.allocated_class = d.get("section", "A")
        enquiry.allocated_section = d.get("section", "A")
        enquiry.save(update_fields=["allocated_class", "allocated_section", "updated_at"])
        
        # Create enrollment record
        if enquiry.student_user_id and table_exists("portal_student_enrollment"):
            with connection.cursor() as cursor:
                cursor.execute("""
                    INSERT INTO portal_student_enrollment (student_id, class_id, academic_year, roll_number)
                    VALUES (%s, %s, %s, %s)
                    ON CONFLICT (student_id, class_id, academic_year) DO UPDATE SET roll_number=EXCLUDED.roll_number
                """, [enquiry.student_user_id, d.get("class_id"), d.get("academic_year", str(date.today().year)), d.get("roll_number")])
        
        self._log(request.user, "admission.academic_allocated", registration_number)
        
        return Response(serialise({
            "detail": "Academic allocation completed.",
            "class_id": alloc.class_id,
            "section": alloc.section,
        }))


# ---------------------------------------------------------------------------
# Phase 15: Optional Module Allocation (Transport/Hostel/Library/LMS)
# ---------------------------------------------------------------------------
class AdmissionModuleAllocationView(AdmissionWorkflowMixin, APIView):
    """POST: Allocate transport, hostel, library, LMS."""

    def get(self, request, registration_number):
        enquiry = self._get_enquiry(registration_number)
        if not enquiry:
            return Response({"detail": "Application not found."}, status=404)
        
        if table_exists("portal_admission_module_allocation"):
            modules = rows(
                "SELECT * FROM portal_admission_module_allocation WHERE enquiry_id = %s AND is_active = true",
                [enquiry.id]
            )
            return Response(serialise(modules))
        
        return Response([])

    def post(self, request, registration_number):
        enquiry = self._get_enquiry(registration_number)
        if not enquiry:
            return Response({"detail": "Application not found."}, status=404)
        
        d = request.data
        module_type = d.get("module_type")
        
        if module_type not in ("Transport", "Hostel", "Library", "LMS", "Medical"):
            return Response({"detail": "Invalid module type."}, status=400)
        
        if table_exists("portal_admission_module_allocation"):
            with connection.cursor() as cursor:
                cursor.execute("""
                    INSERT INTO portal_admission_module_allocation (enquiry_id, module_type, allocation_data, is_active)
                    VALUES (%s, %s, %s, true)
                """, [enquiry.id, module_type, json.dumps(d.get("allocation_data", {}))])
        
        # Handle specific module allocations
        if module_type == "Transport" and enquiry.student_user_id:
            if table_exists("portal_transport_allocation"):
                with connection.cursor() as cursor:
                    cursor.execute("""
                        INSERT INTO portal_transport_allocation (student_id, vehicle_id, route_id, pickup_point)
                        VALUES (%s, %s, %s, %s)
                        ON CONFLICT (student_id) DO UPDATE SET
                            vehicle_id=EXCLUDED.vehicle_id, route_id=EXCLUDED.route_id, pickup_point=EXCLUDED.pickup_point
                    """, [
                        enquiry.student_user_id,
                        d.get("vehicle_id"),
                        d.get("route_id"),
                        d.get("pickup_point", ""),
                    ])
        
        elif module_type == "Hostel" and enquiry.student_user_id:
            if table_exists("portal_hostel_allocation"):
                with connection.cursor() as cursor:
                    cursor.execute("""
                        INSERT INTO portal_hostel_allocation (student_id, room_id, bed_number, allocated_date)
                        VALUES (%s, %s, %s, CURRENT_DATE)
                    """, [
                        enquiry.student_user_id,
                        d.get("room_id"),
                        d.get("bed_number", ""),
                    ])
        
        elif module_type == "Library" and enquiry.student_user_id:
            # Library account is auto-created when student logs in
            pass
        
        elif module_type == "LMS" and enquiry.student_user_id:
            # LMS activation is automatic
            pass
        
        self._log(request.user, f"admission.module_{module_type.lower()}", registration_number)
        
        return Response(serialise({"detail": f"{module_type} allocation completed."}))


# ---------------------------------------------------------------------------
# Phase 16: Notifications
# ---------------------------------------------------------------------------
class AdmissionNotificationView(AdmissionWorkflowMixin, APIView):
    """GET: List notifications for an admission. POST: Send notification."""

    def get(self, request, registration_number):
        enquiry = self._get_enquiry(registration_number)
        if not enquiry:
            return Response({"detail": "Application not found."}, status=404)
        
        notifications = list(AdmissionNotification.objects.filter(enquiry=enquiry).values(
            "id", "recipient_type", "notification_type", "title",
            "message", "channel", "is_sent", "sent_at", "created_at"
        ))
        return Response(serialise(notifications))

    def post(self, request, registration_number):
        enquiry = self._get_enquiry(registration_number)
        if not enquiry:
            return Response({"detail": "Application not found."}, status=404)
        
        d = request.data
        notif = AdmissionNotification.objects.create(
            enquiry=enquiry,
            recipient_type=d.get("recipient_type", "Parent"),
            recipient_user_id=d.get("recipient_user_id"),
            notification_type=d.get("notification_type", "custom"),
            title=d.get("title", ""),
            message=d.get("message", ""),
            channel=d.get("channel", "in_app"),
        )
        
        self._log(request.user, "admission.notification_sent", registration_number, {
            "type": notif.notification_type
        })
        
        return Response(serialise({"detail": "Notification sent.", "id": notif.id}))


# ---------------------------------------------------------------------------
# Phase 18: Reports & Analytics
# ---------------------------------------------------------------------------
class AdmissionReportsView(AdmissionWorkflowMixin, APIView):
    """GET: Admission reports and analytics."""

    def get(self, request):
        report_type = request.query_params.get("type", "overview")
        
        if report_type == "overview":
            total = AdmissionEnquiry.objects.count()
            status_counts = {}
            for status_val, _ in AdmissionEnquiry.STATUS_CHOICES:
                status_counts[status_val] = AdmissionEnquiry.objects.filter(status=status_val).count()
            
            source_counts = {}
            for source_val, _ in AdmissionEnquiry.SOURCE_CHOICES:
                count = AdmissionEnquiry.objects.filter(source_of_enquiry=source_val).count()
                if count > 0:
                    source_counts[source_val] = count
            
            gender_counts = {}
            for gender_val in ["Male", "Female", "Other"]:
                count = AdmissionEnquiry.objects.filter(gender=gender_val).count()
                if count > 0:
                    gender_counts[gender_val] = count
            
            curriculum_counts = {}
            for curr_val, _ in AdmissionEnquiry.CURRICULUM_CHOICES:
                count = AdmissionEnquiry.objects.filter(curriculum=curr_val).count()
                if count > 0:
                    curriculum_counts[curr_val] = count
            
            # Fee collected
            fee_collected = 0
            if AdmissionFee.objects.exists():
                from django.db.models import Sum
                fee_collected = AdmissionFee.objects.filter(is_paid=True).aggregate(
                    total=Sum("net_amount")
                )["total"] or 0
            
            return Response(serialise({
                "total_enquiries": total,
                "status_counts": status_counts,
                "source_counts": source_counts,
                "gender_counts": gender_counts,
                "curriculum_counts": curriculum_counts,
                "fee_collected": str(fee_collected),
            }))
        
        elif report_type == "class_wise":
            class_data = {}
            for status_val, _ in AdmissionEnquiry.STATUS_CHOICES:
                qs = AdmissionEnquiry.objects.filter(status=status_val)
                for target in qs.values_list("target_class", flat=True).distinct():
                    if target not in class_data:
                        class_data[target] = {}
                    class_data[target][status_val] = qs.filter(target_class=target).count()
            return Response(serialise(class_data))
        
        elif report_type == "branch_wise":
            branch_data = {}
            for branch in AdmissionEnquiry.objects.values_list("preferred_branch", flat=True).distinct():
                if branch:
                    branch_data[branch] = AdmissionEnquiry.objects.filter(preferred_branch=branch).count()
            return Response(serialise(branch_data))
        
        elif report_type == "conversion":
            total = AdmissionEnquiry.objects.count()
            converted = AdmissionEnquiry.objects.filter(status="Confirmed").count()
            rejected = AdmissionEnquiry.objects.filter(status="Rejected").count()
            pending = AdmissionEnquiry.objects.exclude(status__in=["Confirmed", "Rejected"]).count()
            
            return Response(serialise({
                "total": total,
                "converted": converted,
                "rejected": rejected,
                "pending": pending,
                "conversion_rate": round((converted / total * 100), 1) if total > 0 else 0,
            }))
        
        elif report_type == "revenue":
            from django.db.models import Sum
            fee_data = AdmissionFee.objects.filter(is_paid=True).aggregate(
                total=Sum("net_amount"),
                total_discount=Sum("scholarship_discount"),
            )
            
            monthly = {}
            for fee in AdmissionFee.objects.filter(is_paid=True):
                month_key = fee.payment_date.strftime("%Y-%m") if fee.payment_date else "Unknown"
                if month_key not in monthly:
                    monthly[month_key] = {"collected": 0, "discount": 0}
                monthly[month_key]["collected"] += float(fee.net_amount)
                monthly[month_key]["discount"] += float(fee.scholarship_discount)
            
            return Response(serialise({
                "total_collected": str(fee_data["total"] or 0),
                "total_discount": str(fee_data["total_discount"] or 0),
                "monthly": monthly,
            }))
        
        return Response({"detail": "Unknown report type."}, status=400)


# ---------------------------------------------------------------------------
# Phase 17: Portal Synchronization — Admin Dashboard Stats
# ---------------------------------------------------------------------------
class AdmissionDashboardStatsView(AdmissionWorkflowMixin, APIView):
    """GET: Comprehensive admission dashboard stats."""

    def get(self, request):
        total = AdmissionEnquiry.objects.count()
        
        # Status pipeline counts
        pipeline = {}
        for status_val, _ in AdmissionEnquiry.STATUS_CHOICES:
            pipeline[status_val] = AdmissionEnquiry.objects.filter(status=status_val).count()
        
        # Recent applications
        recent = list(AdmissionEnquiry.objects.order_by("-submitted_at")[:10].values(
            "registration_number", "applicant_name", "target_class", "status",
            "submitted_at", "parent_name"
        ))
        
        # Today's stats
        today = date.today()
        today_new = AdmissionEnquiry.objects.filter(submitted_at__date=today).count()
        
        # Fee collection
        fee_collected = 0
        fee_pending = 0
        if AdmissionFee.objects.exists():
            from django.db.models import Sum
            fee_collected = AdmissionFee.objects.filter(is_paid=True).aggregate(
                total=Sum("net_amount")
            )["total"] or 0
            fee_pending = AdmissionFee.objects.filter(is_paid=False).aggregate(
                total=Sum("net_amount")
            )["total"] or 0
        
        # Interview pending
        interview_pending = AdmissionEnquiry.objects.filter(
            status="Interview_Pending"
        ).count()
        
        # Waitlisted
        waitlisted = AdmissionEnquiry.objects.filter(
            is_waitlisted=True
        ).count()
        
        return Response(serialise({
            "total_enquiries": total,
            "pipeline": pipeline,
            "recent_applications": recent,
            "today_new": today_new,
            "fee_collected": str(fee_collected),
            "fee_pending": str(fee_pending),
            "interview_pending": interview_pending,
            "waitlisted": waitlisted,
        }))


import csv
from django.http import HttpResponse

class AdmissionReportView(AdmissionWorkflowMixin, APIView):
    """GET: Export all admission enquiries to CSV."""
    def get(self, request):
        qs = AdmissionEnquiry.objects.all().order_by("-submitted_at")
        
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="admissions_report.csv"'
        
        writer = csv.writer(response)
        writer.writerow([
            "Registration Number", "Applicant Name", "Target Class", "Status",
            "Submitted At", "Father Name", "Father Phone", "Mother Name", "Mother Phone",
            "City", "State", "Prev School", "Scholarship Applied"
        ])
        
        for app in qs:
            writer.writerow([
                app.registration_number,
                app.applicant_name,
                app.target_class,
                app.status,
                app.submitted_at.strftime("%Y-%m-%d %H:%M:%S") if app.submitted_at else "",
                app.father_name,
                app.father_phone,
                app.mother_name,
                app.mother_phone,
                app.city,
                app.state,
                app.prev_school_name,
                "Yes" if app.scholarship_applied else "No"
            ])
            
        return response
