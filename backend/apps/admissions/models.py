import uuid
from django.db import models


def generate_registration_number():
    return f"ADM-{uuid.uuid4().hex[:10].upper()}"


class AdmissionEnquiry(models.Model):
    """
    Complete Admission Workflow Model covering all 18 phases:
    Phase 1: Admission Enquiry capture
    Phase 2: Counselling tracking
    Phase 3: Online Registration (via public form)
    Phase 4: Application Form data
    Phase 5: Document Upload tracking
    Phase 6: Eligibility Validation
    Phase 7: Application Review
    Phase 8: Interview / Assessment
    Phase 9: Seat Allocation
    Phase 10: Admission Decision
    Phase 11: Fee Payment
    Phase 12-15: Record creation, allocation, module allocation
    Phase 16: Notifications
    Phase 17: Portal Synchronization
    Phase 18: Reports & Analytics
    """
    STATUS_CHOICES = [
        ("Enquiry", "Enquiry"),
        ("Registered", "Registered"),
        ("Counselling_Pending", "Counselling Pending"),
        ("Counselling_Done", "Counselling Done"),
        ("Verification", "Verification"),
        ("Eligibility_Check", "Eligibility Check"),
        ("Screening", "Screening"),
        ("Interview_Pending", "Interview Pending"),
        ("Interview_Done", "Interview Done"),
        ("Seat_Available", "Seat Available"),
        ("Seat_Waitlisted", "Seat Waitlisted"),
        ("Fee_Pending", "Fee Pending"),
        ("Approved", "Approved"),
        ("Confirmed", "Confirmed"),
        ("Rejected", "Rejected"),
        ("Withdrawn", "Withdrawn"),
    ]

    COUNSELLING_STATUS_CHOICES = [
        ("Pending", "Pending"),
        ("Scheduled", "Scheduled"),
        ("Completed", "Completed"),
        ("Converted", "Converted"),
    ]

    SOURCE_CHOICES = [
        ("Website", "Website"),
        ("Walk-in", "Walk-in"),
        ("Phone", "Phone"),
        ("Email", "Email"),
        ("Referral", "Referral"),
        ("Social_Media", "Social Media"),
        ("Advertisement", "Advertisement"),
    ]

    CURRICULUM_CHOICES = [
        ("CBSE", "CBSE"),
        ("Cambridge", "Cambridge"),
        ("IB", "IB"),
        ("State_Board", "State Board"),
    ]

    # Phase 1: Core enquiry fields
    registration_number = models.CharField(
        max_length=100, unique=True, default=generate_registration_number, editable=False
    )
    applicant_name = models.CharField(max_length=150)
    date_of_birth = models.DateField()
    gender = models.CharField(max_length=20, blank=True)
    target_class = models.CharField(max_length=50, help_text="Class applied for, e.g. 'Grade 6'")
    
    # Restored Parent details for compatibility
    parent_name = models.CharField(max_length=150, blank=True, null=True)
    parent_phone = models.CharField(max_length=20, blank=True, null=True)
    parent_email = models.EmailField(blank=True, null=True)

    # Phase 1: Father details
    father_name = models.CharField(max_length=150, blank=True)
    father_occupation = models.CharField(max_length=150, blank=True)
    father_company = models.CharField(max_length=150, blank=True)
    father_income = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    father_phone = models.CharField(max_length=20, blank=True)
    father_email = models.EmailField(blank=True)

    # Phase 1: Mother details
    mother_name = models.CharField(max_length=150, blank=True)
    mother_occupation = models.CharField(max_length=150, blank=True)
    mother_company = models.CharField(max_length=150, blank=True)
    mother_phone = models.CharField(max_length=20, blank=True)
    mother_email = models.EmailField(blank=True)

    # Phase 1: Guardian details
    guardian_name = models.CharField(max_length=150, blank=True)
    guardian_relationship = models.CharField(max_length=100, blank=True)
    guardian_phone = models.CharField(max_length=20, blank=True)
    guardian_address = models.TextField(blank=True)

    # Phase 1: Address details
    address = models.TextField(blank=True)
    pincode = models.CharField(max_length=20, blank=True)
    city = models.CharField(max_length=100, blank=True)
    state = models.CharField(max_length=100, blank=True)
    country = models.CharField(max_length=100, blank=True)

    # Phase 1: Emergency & Medical
    emergency_contact_name = models.CharField(max_length=150, blank=True)
    emergency_contact_phone = models.CharField(max_length=20, blank=True)
    blood_group = models.CharField(max_length=10, blank=True)
    has_medical_conditions = models.BooleanField(default=False)
    medical_details = models.TextField(blank=True)

    # Phase 1: Previous School
    prev_school_name = models.CharField(max_length=200, blank=True)
    prev_school_grade = models.CharField(max_length=50, blank=True)

    # Phase 5: Documents
    doc_birth_certificate = models.FileField(upload_to="admissions/documents/", blank=True, null=True)
    doc_aadhaar_card = models.FileField(upload_to="admissions/documents/", blank=True, null=True)
    doc_passport_photo = models.FileField(upload_to="admissions/documents/", blank=True, null=True)
    doc_parent_id = models.FileField(upload_to="admissions/documents/", blank=True, null=True)
    doc_address_proof = models.FileField(upload_to="admissions/documents/", blank=True, null=True)
    doc_previous_marks = models.FileField(upload_to="admissions/documents/", blank=True, null=True)
    doc_transfer_certificate = models.FileField(upload_to="admissions/documents/", blank=True, null=True)
    
    # Phase 1: Enquiry source tracking
    source_of_enquiry = models.CharField(max_length=50, choices=SOURCE_CHOICES, default="Website")
    preferred_branch = models.CharField(max_length=150, blank=True, default="")
    curriculum = models.CharField(max_length=30, choices=CURRICULUM_CHOICES, default="CBSE")
    scholarship_applied = models.BooleanField(default=False)
    id_proof_document = models.FileField(upload_to="admissions/documents/", blank=True, null=True)

    # Phase 7: Application Review status
    status = models.CharField(max_length=25, choices=STATUS_CHOICES, default="Enquiry")
    reviewed_by = models.CharField(max_length=150, blank=True)
    rejection_reason = models.TextField(blank=True)
    
    # Phase 2: Counselling tracking
    counsellor_id = models.IntegerField(null=True, blank=True, help_text="auth_user ID of assigned counsellor")
    counselling_status = models.CharField(max_length=30, choices=COUNSELLING_STATUS_CHOICES, default="Pending")
    counselling_notes = models.TextField(blank=True, default="")
    counselling_date = models.DateTimeField(null=True, blank=True)
    
    # Phase 6: Eligibility
    is_eligible = models.BooleanField(default=False)
    eligibility_notes = models.TextField(blank=True, default="")
    
    # Phase 8: Interview
    interview_required = models.BooleanField(default=False)
    interview_scheduled = models.BooleanField(default=False)
    interview_date = models.DateTimeField(null=True, blank=True)
    interview_result = models.CharField(max_length=30, blank=True, default="")
    
    # Phase 9: Seat allocation
    seat_allocated = models.BooleanField(default=False)
    allocated_class = models.CharField(max_length=50, blank=True, default="")
    allocated_section = models.CharField(max_length=10, blank=True, default="")
    is_waitlisted = models.BooleanField(default=False)
    waitlist_position = models.IntegerField(null=True, blank=True)
    
    # Phase 11: Fee
    fee_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    scholarship_discount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    net_fee = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    fee_paid = models.BooleanField(default=False)
    fee_transaction_id = models.CharField(max_length=100, blank=True, default="")
    
    # Phase 12: Student/Parent account linking
    student_user_id = models.IntegerField(null=True, blank=True)
    parent_user_id = models.IntegerField(null=True, blank=True)
    student_admission_number = models.CharField(max_length=50, blank=True, default="")
    student_roll_number = models.CharField(max_length=20, blank=True, default="")
    
    # Timestamps
    submitted_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        if not self.parent_name:
            self.parent_name = self.father_name or self.mother_name or self.guardian_name or ""
        if not self.parent_phone:
            self.parent_phone = self.father_phone or self.mother_phone or self.guardian_phone or ""
        if not self.parent_email:
            self.parent_email = self.father_email or self.mother_email or ""
        super().save(*args, **kwargs)

    class Meta:
        ordering = ["-submitted_at"]

    def __str__(self):
        return f"{self.applicant_name} ({self.registration_number}) — {self.status}"


class AdmissionDocument(models.Model):
    """Phase 5: Document upload tracking for each admission application."""
    DOCUMENT_TYPE_CHOICES = [
        ("Birth_Certificate", "Birth Certificate"),
        ("Aadhaar", "Aadhaar"),
        ("Passport_Photo", "Passport Photo"),
        ("Parent_ID", "Parent ID"),
        ("Address_Proof", "Address Proof"),
        ("Marks_Memo", "Previous Marks Memo"),
        ("Transfer_Certificate", "Transfer Certificate"),
        ("Medical_Certificate", "Medical Certificate"),
        ("Caste_Certificate", "Caste Certificate"),
        ("Income_Certificate", "Income Certificate"),
        ("Other", "Other"),
    ]
    
    enquiry = models.ForeignKey(AdmissionEnquiry, on_delete=models.CASCADE, related_name="documents")
    document_type = models.CharField(max_length=50, choices=DOCUMENT_TYPE_CHOICES)
    document_name = models.CharField(max_length=200)
    file_url = models.TextField()
    file_size = models.IntegerField(default=0)
    file_type = models.CharField(max_length=20, default="")
    is_verified = models.BooleanField(default=False)
    verified_by = models.IntegerField(null=True, blank=True)
    verification_notes = models.TextField(blank=True, default="")
    uploaded_at = models.DateTimeField(auto_now_add=True)
    verified_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-uploaded_at"]

    def __str__(self):
        return f"{self.document_type} for {self.enquiry.applicant_name}"


class AdmissionInterview(models.Model):
    """Phase 8: Interview / Assessment tracking."""
    RESULT_CHOICES = [
        ("Recommended", "Recommended"),
        ("Recommended_Conditions", "Recommended with Conditions"),
        ("Not_Recommended", "Not Recommended"),
    ]
    STATUS_CHOICES = [
        ("Scheduled", "Scheduled"),
        ("Completed", "Completed"),
        ("Cancelled", "Cancelled"),
    ]
    
    enquiry = models.ForeignKey(AdmissionEnquiry, on_delete=models.CASCADE, related_name="interviews")
    interviewer_id = models.IntegerField(null=True, blank=True)
    interview_date = models.DateTimeField(null=True, blank=True)
    interview_type = models.CharField(max_length=30, default="Interview")
    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default="Scheduled")
    marks_obtained = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    max_marks = models.DecimalField(max_digits=5, decimal_places=2, default=100)
    recommendation = models.CharField(max_length=30, choices=RESULT_CHOICES, blank=True, default="")
    remarks = models.TextField(blank=True, default="")
    parent_notified = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Interview for {self.enquiry.applicant_name} - {self.status}"


class AdmissionFee(models.Model):
    """Phase 11: Fee payment tracking for admissions."""
    enquiry = models.OneToOneField(AdmissionEnquiry, on_delete=models.CASCADE, related_name="fee_record")
    fee_type = models.CharField(max_length=50, default="Admission_Fee")
    total_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    scholarship_discount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    net_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    is_paid = models.BooleanField(default=False)
    transaction_id = models.CharField(max_length=100, blank=True, default="")
    payment_method = models.CharField(max_length=40, blank=True, default="")
    payment_date = models.DateTimeField(null=True, blank=True)
    invoice_number = models.CharField(max_length=50, blank=True, default="")
    receipt_url = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Fee for {self.enquiry.applicant_name} - {self.net_amount}"


class AdmissionAllocation(models.Model):
    """Phase 14: Academic class/section allocation for confirmed admissions."""
    enquiry = models.OneToOneField(AdmissionEnquiry, on_delete=models.CASCADE, related_name="allocation")
    student_user_id = models.IntegerField(null=True, blank=True)
    class_id = models.IntegerField(null=True, blank=True)
    section = models.CharField(max_length=10, blank=True, default="")
    house = models.CharField(max_length=30, blank=True, default="")
    class_teacher_id = models.IntegerField(null=True, blank=True)
    roll_number = models.IntegerField(null=True, blank=True)
    academic_year = models.CharField(max_length=20, blank=True, default="")
    allocated_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Allocation for {self.enquiry.applicant_name}"


class AdmissionNotification(models.Model):
    """Phase 16: Notification tracking for admission workflow events."""
    CHANNEL_CHOICES = [
        ("email", "Email"),
        ("sms", "SMS"),
        ("in_app", "In-App"),
        ("push", "Push"),
    ]
    
    enquiry = models.ForeignKey(AdmissionEnquiry, on_delete=models.CASCADE, related_name="notifications")
    recipient_type = models.CharField(max_length=30)
    recipient_user_id = models.IntegerField(null=True, blank=True)
    notification_type = models.CharField(max_length=50)
    title = models.CharField(max_length=200)
    message = models.TextField()
    channel = models.CharField(max_length=20, choices=CHANNEL_CHOICES, default="in_app")
    is_sent = models.BooleanField(default=False)
    sent_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.notification_type} for {self.enquiry.applicant_name}"
