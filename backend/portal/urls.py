from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView

from . import auth_views, teacher_views, views, parent_views, admin_views, facilities_views, exam_extras_views, lms_extras_views, scholarship_views, admission_workflow_views, academic_website_views, admin_academic_views

urlpatterns = [
    # Auth (credentials -> OTP -> JWT), shared by every portal
    path("auth/login/", auth_views.login_step1, name="login-step1"),
    path("auth/verify-otp/", auth_views.login_step2_verify_otp, name="login-verify-otp"),
    path("auth/resend-otp/", auth_views.resend_otp, name="resend-otp"),
    path("auth/refresh/", TokenRefreshView.as_view(), name="token-refresh"),
    path("upload/", views.FileUploadView.as_view(), name="file-upload"),

    # Student portal
    path("student/profile/", views.ProfileView.as_view()),
    path("student/ai-chat/", views.StudentAIChatView.as_view(), name="student-ai-chat"),
    path("student/dashboard/", views.DashboardView.as_view()),
    path("student/attendance/", views.AttendanceListView.as_view()),
    path("student/leaves/", views.StudentLeaveView.as_view()),
    path("student/timetable/", views.TimetableView.as_view()),
    path("student/homework/", views.HomeworkListView.as_view()),
    path("student/assignments/", views.AssignmentListView.as_view()),
    path("student/assignments/<int:assignment_id>/submit/", views.AssignmentSubmitView.as_view()),
    path("student/courses/", views.CourseListView.as_view()),
    path("student/quizzes/<int:quiz_id>/", views.QuizDetailView.as_view()),
    path("student/exams/", views.ExamListView.as_view()),
    path("student/exams/attempt/", exam_extras_views.StudentExamAttemptView.as_view()),
    path("student/exams/revaluation/", exam_extras_views.RevaluationRequestView.as_view()),
    path("student/supplementary/", exam_extras_views.SupplementaryRegistrationView.as_view()),
    path("student/academic-certificates/", exam_extras_views.AcademicCertificateView.as_view()),
    path("student/hall-tickets/", views.HallTicketListView.as_view()),
    path("student/results/", views.ResultListView.as_view()),
    path("student/fees/", views.FeesView.as_view()),
    path("student/fees/pay/", views.InitiatePaymentView.as_view()),
    path("student/library/", views.LibraryView.as_view()),
    path("student/library/search/", views.BookSearchView.as_view()),
    path("student/certificates/", views.CertificateListView.as_view()),
    path("student/announcements/", views.AnnouncementListView.as_view()),
    path("student/events/", views.EventListView.as_view()),
    path("student/hostel/", facilities_views.StudentHostelView.as_view()),
    path("student/transport/", facilities_views.StudentTransportView.as_view()),
    path("student/medical-records/", facilities_views.StudentMedicalView.as_view()),
    path("student/report-card/", exam_extras_views.StudentReportCardView.as_view()),
    path("student/scholarships/", scholarship_views.ScholarshipStudentApplicationView.as_view()),
    path("student/scholarships/renew/", scholarship_views.ScholarshipRenewalView.as_view()),
    path("lms/forum-topics/", lms_extras_views.ForumTopicListView.as_view()),
    path("lms/forum-topics/<int:topic_id>/", lms_extras_views.ForumTopicDetailView.as_view()),
    path("lms/forum-topics/<int:topic_id>/reply/", lms_extras_views.ForumPostView.as_view()),
    path("lms/notes/", lms_extras_views.DigitalNoteView.as_view()),
    path("lms/mark-complete/", lms_extras_views.MarkContentCompleteView.as_view()),
    path("lms/analytics/", lms_extras_views.CourseAnalyticsView.as_view()),
    path("student/ai-tutor/", lms_extras_views.StudentAITutorView.as_view()),

    # Teacher portal — mirrors the "Teacher Portal — Detailed Flowchart"
    path("teacher/profile/", teacher_views.TeacherProfileView.as_view()),
    path("teacher/dashboard/", teacher_views.TeacherDashboardView.as_view()),
    path("teacher/classes/", teacher_views.MyClassesView.as_view()),
    path("teacher/classes/<int:class_id>/roster/", teacher_views.ClassRosterView.as_view()),
    path("teacher/attendance/", teacher_views.AttendanceView.as_view()),
    path("teacher/homework/", teacher_views.HomeworkView.as_view()),
    path("teacher/assignments/", teacher_views.AssignmentView.as_view()),
    path("teacher/assignments/scan-pdf/", teacher_views.AssignmentScanPDFView.as_view()),
    path("teacher/assignments/<int:assignment_id>/", teacher_views.AssignmentDetailView.as_view()),
    path("teacher/assignments/<int:assignment_id>/submissions/", teacher_views.AssignmentSubmissionsView.as_view()),
    path("teacher/assignments/<int:assignment_id>/submissions/<int:submission_id>/", teacher_views.AssignmentSubmissionsView.as_view()),
    path("teacher/question-bank/", teacher_views.QuestionBankView.as_view()),
    path("teacher/question-bank/<int:question_id>/", teacher_views.QuestionBankView.as_view()),
    path("teacher/exams/", teacher_views.TeacherExamView.as_view()),
    path("teacher/marks-entry/", teacher_views.MarksEntryView.as_view()),
    path("teacher/performance/", teacher_views.PerformanceAnalyticsView.as_view()),
    path("teacher/question-papers/", teacher_views.QuestionPaperView.as_view()),
    path("teacher/invigilation-duty/", teacher_views.InvigilationDutyView.as_view()),
    path("teacher/revaluation/", exam_extras_views.RevaluationRequestView.as_view()),
    path("teacher/supplementary/", exam_extras_views.SupplementaryRegistrationView.as_view()),
    path("teacher/messages/", teacher_views.MessageThreadView.as_view()),
    path("teacher/contacts/", teacher_views.MyContactsView.as_view()),
    path("teacher/notices/", teacher_views.NoticeListView.as_view()),
    path("teacher/leaves/", teacher_views.LeaveView.as_view()),
    path("teacher/admissions-review/", teacher_views.TeacherAdmissionsReviewView.as_view()),
    path("teacher/timetable/", teacher_views.TeacherTimetableView.as_view()),
    path("teacher/documents/", teacher_views.TeacherDocumentsView.as_view()),
    path("teacher/lms/courses/", teacher_views.TeacherLmsCoursesView.as_view()),
    path("teacher/lms/chapters/", teacher_views.TeacherLmsChaptersView.as_view()),
    path("teacher/lms/lessons/", teacher_views.TeacherLmsLessonsView.as_view()),
    path("teacher/lms/resources/", teacher_views.TeacherLmsResourcesView.as_view()),
    path("teacher/lms/ai-usage/", lms_extras_views.TeacherAIUsageView.as_view()),

    # Parent portal
    path("parent/profile/", parent_views.ParentProfileView.as_view()),
    path("parent/dashboard/", parent_views.ParentDashboardView.as_view()),
    path("parent/children/", parent_views.ChildrenListView.as_view()),
    path("parent/attendance/", parent_views.ChildAttendanceView.as_view()),
    path("parent/homework/", parent_views.ChildHomeworkView.as_view()),
    path("parent/results/", parent_views.ChildResultsView.as_view()),
    path("parent/exams/revaluation/", exam_extras_views.RevaluationRequestView.as_view()),
    path("parent/exams/certificates/", exam_extras_views.AcademicCertificateView.as_view()),
    path("parent/fees/", parent_views.ChildFeesView.as_view()),
    path("parent/fees/pay/", parent_views.ChildFeesPayView.as_view()),
    path("parent/documents/", parent_views.ChildDocumentsView.as_view()),
    path("parent/transport/", parent_views.ChildTransportView.as_view()),
    path("parent/hostel/", facilities_views.ChildHostelView.as_view()),
    path("parent/teachers/", parent_views.TeacherContactsView.as_view()),
    path("parent/messages/", parent_views.MessageThreadView.as_view()),
    path("parent/notifications/", parent_views.NotificationListView.as_view()),
    path("parent/leaves/", parent_views.LeaveRequestView.as_view()),
    path("parent/ptm/", parent_views.PtmBookingView.as_view()),
    path("parent/feedback/", parent_views.FeedbackView.as_view()),
    path("parent/lms/progress/", parent_views.ParentLmsProgressView.as_view()),

    # Admin portal
    path("admin-portal/dashboard/", admin_views.AdminDashboardView.as_view()),
    path("admin-portal/admissions/", admin_views.AdmissionListView.as_view()),
    path("admin-portal/admissions/<str:registration_number>/action/", admin_views.AdmissionActionView.as_view()),
    path("admin-portal/users/", admin_views.UserListView.as_view()),
    path("admin-portal/users/<int:user_id>/", admin_views.UserDetailView.as_view()),
    path("admin-portal/users/<int:user_id>/reset-password/", admin_views.UserDetailView.as_view()),
    path("admin-portal/roles/", admin_views.RolesView.as_view()),
    path("admin-portal/classes/", admin_views.ClassView.as_view()),
    path("admin-portal/classes/<int:record_id>/", admin_views.ClassView.as_view()),
    path("admin-portal/enrollments/", admin_views.ClassEnrollmentView.as_view()),
    path("admin-portal/enrollments/<int:enrollment_id>/", admin_views.ClassEnrollmentView.as_view()),
    path("admin-portal/class-teachers/", admin_views.ClassTeacherAssignView.as_view()),
    path("admin-portal/class-teachers/<int:class_id>/", admin_views.ClassTeacherAssignView.as_view()),
    path("admin-portal/subjects/", admin_views.SubjectView.as_view()),
    path("admin-portal/subjects/<int:record_id>/", admin_views.SubjectView.as_view()),
    # Transport — Vehicles
    path("admin-portal/vehicles/", admin_views.VehicleView.as_view()),
    # Transport — Routes
    path("admin-portal/routes/", admin_views.RouteView.as_view()),
    # Transport — Student Allocations
    path("admin-portal/transport-allocations/", admin_views.TransportAllocationView.as_view()),
    # Transport — Drivers
    path("admin-portal/transport/drivers/", admin_views.DriverView.as_view()),
    # Transport — Attendants
    path("admin-portal/transport/attendants/", admin_views.AttendantView.as_view()),
    # Transport — Pickup / Drop Points
    path("admin-portal/transport/pickup-points/", admin_views.PickupPointView.as_view()),
    # Transport — Passes
    path("admin-portal/transport/passes/", admin_views.TransportPassView.as_view()),
    # Transport — Trip Logs
    path("admin-portal/transport/trips/", admin_views.TripLogView.as_view()),
    # Transport — Notifications / Alerts
    path("admin-portal/transport/notifications/", admin_views.TransportNotificationView.as_view()),
    # Transport — Settings
    path("admin-portal/transport/settings/", admin_views.TransportSettingsView.as_view()),
    # Transport — Reports
    path("admin-portal/transport/reports/", admin_views.TransportReportsView.as_view()),
    # Transport — Live Fleet Map (latest GPS ping per vehicle)
    path("admin-portal/transport/live-map/", admin_views.LiveBusMapView.as_view()),
    # Transport — Transport Fees
    path("admin-portal/transport/fees/", admin_views.TransportFeeView.as_view()),
    path("admin-portal/fee-structures/", admin_views.FeeStructureView.as_view()),
    path("admin-portal/fee-structures/<int:record_id>/", admin_views.FeeStructureView.as_view()),
    path("admin-portal/academic-years/", admin_views.AcademicYearView.as_view()),
    path("admin-portal/fee-categories/", admin_views.FeeCategoryView.as_view()),
    path("admin-portal/fee-assignments/", admin_views.FeeAssignmentView.as_view()),
    path("admin-portal/fee-concessions/", admin_views.FeeConcessionView.as_view()),
    path("admin-portal/fee-ledger/", admin_views.StudentFeeLedgerView.as_view()),
    path("admin-portal/scholarships/", scholarship_views.ScholarshipAdminActionView.as_view()),
    path("admin-portal/scholarships/renew/", scholarship_views.ScholarshipRenewalView.as_view()),
    path("admin-portal/fee-reports/", admin_views.FeeReportsView.as_view()),
    path("admin-portal/payments/", admin_views.PaymentListView.as_view()),
    path("admin-portal/library/books/", admin_views.LibraryBookView.as_view()),
    path("admin-portal/library/issue/", admin_views.LibraryIssueView.as_view()),
    path("admin-portal/library/return/<int:transaction_id>/", admin_views.LibraryReturnView.as_view()),
    path("admin-portal/notices/", admin_views.NoticeBroadcastView.as_view()),
    path("admin-portal/leaves/", admin_views.LeaveApprovalListView.as_view()),
    path("admin-portal/leaves/<int:leave_id>/decide/", admin_views.LeaveApprovalListView.as_view()),
    path("admin-portal/reports/", admin_views.ReportsView.as_view()),
    path("admin-portal/audit-log/", admin_views.AuditLogListView.as_view()),
    path("admin-portal/backup/export/", admin_views.BackupExportView.as_view()),
    path("admin-portal/lms/analytics/", admin_views.AdminLmsAnalyticsView.as_view()),
    path("admin-portal/lms/ai-usage/", lms_extras_views.AdminAIUsageView.as_view()),

    # Hostel module
    path("admin-portal/hostels/", facilities_views.HostelView.as_view()),
    path("admin-portal/rooms/", facilities_views.RoomView.as_view()),
    path("admin-portal/hostel-allocations/", facilities_views.HostelAllocationView.as_view()),
    path("admin-portal/hostel-allocations/<int:allocation_id>/vacate/", facilities_views.HostelVacateView.as_view()),
    path("hostels/applications/", facilities_views.HostelApplicationView.as_view()),
    path("hostels/leaves/", facilities_views.HostelLeaveView.as_view()),
    path("hostels/complaints/", facilities_views.HostelComplaintView.as_view()),
    path("hostels/fees/", facilities_views.HostelFeeView.as_view()),
    path("hostels/reports/", facilities_views.HostelReportsView.as_view()),

    # Inventory module
    path("admin-portal/inventory/", facilities_views.InventoryView.as_view()),
    path("admin-portal/payroll/", facilities_views.PayrollView.as_view()),

    # Visitor Management
    path("admin-portal/visitors/", facilities_views.VisitorLogView.as_view()),
    path("admin-portal/visitors/<int:visitor_id>/checkout/", facilities_views.VisitorCheckoutView.as_view()),

    # Alumni Registry
    path("admin-portal/alumni/", facilities_views.AlumniView.as_view()),

    # Medical Records
    path("admin-portal/medical-logs/", facilities_views.MedicalLogView.as_view()),

    # Exam extras: rank lists + report cards
    path("admin-portal/rank-list/", exam_extras_views.RankListView.as_view()),
    path("admin-portal/rank-list/overall/", exam_extras_views.OverallRankListView.as_view()),
    path("admin-portal/report-card/", exam_extras_views.ReportCardView.as_view()),

    # Campus & Visit Locations Module
    path("campuses/", views.PublicCampusView.as_view()),
    path("campuses/visit/", views.PublicCampusVisitView.as_view()),
    path("campuses/nearest/", views.NearestCampusView.as_view()),
    path("admin-portal/campuses/", admin_views.AdminCampusView.as_view()),
    path("admin-portal/campuses/<int:campus_id>/", admin_views.AdminCampusDetailView.as_view()),
    path("admin-portal/campuses/visits/", admin_views.AdminCampusVisitsView.as_view()),
    path("admin-portal/campuses/visits/<int:visit_id>/status/", admin_views.AdminCampusVisitsView.as_view()),
    path("cms/scholarships/", views.PublicScholarshipsView.as_view()),

    # Admin exams management & publication
    path("admin-portal/exams/", exam_extras_views.AdminExamActionView.as_view()),
    path("admin-portal/exams/<int:exam_id>/action/", exam_extras_views.AdminExamActionView.as_view()),
    path("admin-portal/exams/seating/", exam_extras_views.TimetableSeatingConflictView.as_view()),
    path("admin-portal/exams/revaluation/", exam_extras_views.RevaluationRequestView.as_view()),
    path("admin-portal/exams/supplementary/", exam_extras_views.SupplementaryRegistrationView.as_view()),
    path("admin-portal/exams/certificates/", exam_extras_views.AcademicCertificateView.as_view()),

    # Timetable Management
    path("admin-portal/timetable/",             admin_views.TimetableAdminView.as_view()),
    path("admin-portal/timetable/<int:entry_id>/", admin_views.TimetableEntryAdminView.as_view()),
    path("admin-portal/timetable/publish/",     admin_views.TimetablePublishView.as_view()),
    path("admin-portal/timetable/conflicts/",   admin_views.TimetableConflictView.as_view()),
    path("admin-portal/timetable/meta/",        admin_views.TimetableMetaView.as_view()),

    # Parent portal — child timetable
    path("parent/timetable/", parent_views.ParentChildTimetableView.as_view()),
    path("parent/scholarships/", scholarship_views.ScholarshipParentView.as_view()),

    # =========================================================================
    # COMPLETE ADMISSION WORKFLOW (Phase 1-18)
    # =========================================================================

    # Phase 1: Admission Enquiry Management
    path("admin-portal/admissions/enquiries/", admission_workflow_views.AdmissionEnquiryAdminView.as_view(), name="admission-enquiries"),

    # Phase 2: Counselling
    path("admin-portal/admissions/<str:registration_number>/counselling/", admission_workflow_views.AdmissionCounsellingView.as_view(), name="admission-counselling"),

    # Phase 4: Application Form Details
    path("admin-portal/admissions/<str:registration_number>/application/", admission_workflow_views.AdmissionApplicationDetailView.as_view(), name="admission-application"),

    # Phase 5: Document Upload & Verification
    path("admin-portal/admissions/<str:registration_number>/documents/", admission_workflow_views.AdmissionDocumentView.as_view(), name="admission-documents"),
    path("admin-portal/admissions/<str:registration_number>/documents/<int:document_id>/", admission_workflow_views.AdmissionDocumentView.as_view(), name="admission-document-detail"),

    # Phase 6: Eligibility Validation
    path("admin-portal/admissions/<str:registration_number>/eligibility/", admission_workflow_views.AdmissionEligibilityView.as_view(), name="admission-eligibility"),

    # Phase 7: Application Review
    path("admin-portal/admissions/<str:registration_number>/review/", admission_workflow_views.AdmissionReviewView.as_view(), name="admission-review"),

    # Phase 8: Interview / Assessment
    path("admin-portal/admissions/<str:registration_number>/interview/", admission_workflow_views.AdmissionInterviewView.as_view(), name="admission-interview"),

    # Phase 9: Seat Allocation
    path("admin-portal/admissions/<str:registration_number>/seat/", admission_workflow_views.AdmissionSeatAllocationView.as_view(), name="admission-seat"),

    # Phase 10: Admission Decision
    path("admin-portal/admissions/<str:registration_number>/decision/", admission_workflow_views.AdmissionDecisionView.as_view(), name="admission-decision"),

    # Phase 11: Fee Payment
    path("admin-portal/admissions/<str:registration_number>/fee/", admission_workflow_views.AdmissionFeePaymentView.as_view(), name="admission-fee"),

    # Phase 12: Admission Confirmation & Account Generation
    path("admin-portal/admissions/<str:registration_number>/confirm/", admission_workflow_views.AdmissionConfirmView.as_view(), name="admission-confirm"),

    # Phase 14: Academic Allocation
    path("admin-portal/admissions/<str:registration_number>/allocation/", admission_workflow_views.AdmissionAcademicAllocationView.as_view(), name="admission-allocation"),

    # Phase 15: Optional Module Allocation (Transport/Hostel/Library/LMS)
    path("admin-portal/admissions/<str:registration_number>/modules/", admission_workflow_views.AdmissionModuleAllocationView.as_view(), name="admission-modules"),

    # Phase 16: Notifications
    path("admin-portal/admissions/<str:registration_number>/notifications/", admission_workflow_views.AdmissionNotificationView.as_view(), name="admission-notifications"),

    # Phase 17: Portal Synchronization - Dashboard Stats
    path("admin-portal/admissions/dashboard-stats/", admission_workflow_views.AdmissionDashboardStatsView.as_view(), name="admission-dashboard-stats"),

    # Phase 18: Reports & Analytics
    path("admin-portal/admissions/reports/", admission_workflow_views.AdmissionReportsView.as_view(), name="admission-reports"),

    # =========================================================================
    # ACADEMIC WEBSITE — Public endpoints (no auth required)
    # =========================================================================
    path("website/levels/", academic_website_views.AcademicLevelsView.as_view(), name="website-levels"),
    path("website/classes/", academic_website_views.PublicClassesListView.as_view(), name="website-classes"),
    path("website/classes/<int:class_id>/", academic_website_views.PublicClassDetailView.as_view(), name="website-class-detail"),
    path("website/subjects/", academic_website_views.PublicSubjectsListView.as_view(), name="website-subjects"),
    path("website/subjects/<int:subject_id>/", academic_website_views.PublicSubjectDetailView.as_view(), name="website-subject-detail"),
    path("website/faculty/", academic_website_views.PublicFacultyListView.as_view(), name="website-faculty"),
    path("website/faculty/<int:faculty_id>/", academic_website_views.PublicFacultyDetailView.as_view(), name="website-faculty-detail"),
    path("website/curriculum/", academic_website_views.PublicCurriculumView.as_view(), name="website-curriculum"),
    path("website/downloads/", academic_website_views.PublicAcademicDownloadsView.as_view(), name="website-downloads"),
    path("website/search/", academic_website_views.PublicAcademicSearchView.as_view(), name="website-search"),
    path("website/stats/", academic_website_views.PublicAcademicStatsView.as_view(), name="website-stats"),

    # =========================================================================
    # ACADEMIC WEBSITE — Admin management endpoints
    # =========================================================================
    path("admin-portal/academic/levels/", admin_academic_views.AdminAcademicLevelView.as_view(), name="admin-levels"),
    path("admin-portal/academic/levels/<int:record_id>/", admin_academic_views.AdminAcademicLevelView.as_view(), name="admin-level-detail"),
    path("admin-portal/academic/class-details/", admin_academic_views.AdminClassDetailView.as_view(), name="admin-class-details"),
    path("admin-portal/academic/class-details/<int:record_id>/", admin_academic_views.AdminClassDetailView.as_view(), name="admin-class-detail-detail"),
    path("admin-portal/academic/subject-details/", admin_academic_views.AdminSubjectDetailView.as_view(), name="admin-subject-details"),
    path("admin-portal/academic/subject-details/<int:record_id>/", admin_academic_views.AdminSubjectDetailView.as_view(), name="admin-subject-detail-detail"),
    path("admin-portal/academic/class-subjects/", admin_academic_views.AdminClassSubjectView.as_view(), name="admin-class-subjects"),
    path("admin-portal/academic/class-subjects/<int:record_id>/", admin_academic_views.AdminClassSubjectView.as_view(), name="admin-class-subject-detail"),
    path("admin-portal/academic/curriculum/", admin_academic_views.AdminCurriculumView.as_view(), name="admin-curriculum"),
    path("admin-portal/academic/curriculum/<int:record_id>/", admin_academic_views.AdminCurriculumView.as_view(), name="admin-curriculum-detail"),
    path("admin-portal/academic/faculty/", admin_academic_views.AdminFacultyManagementView.as_view(), name="admin-faculty-mgmt"),
    path("admin-portal/academic/faculty/<int:record_id>/", admin_academic_views.AdminFacultyManagementView.as_view(), name="admin-faculty-mgmt-detail"),
    path("admin-portal/academic/faculty-subjects/", admin_academic_views.AdminFacultySubjectView.as_view(), name="admin-faculty-subjects"),
    path("admin-portal/academic/faculty-subjects/<int:record_id>/", admin_academic_views.AdminFacultySubjectView.as_view(), name="admin-faculty-subject-detail"),
    path("admin-portal/academic/downloads/", admin_academic_views.AdminAcademicDownloadView.as_view(), name="admin-downloads"),
    path("admin-portal/academic/downloads/<int:record_id>/", admin_academic_views.AdminAcademicDownloadView.as_view(), name="admin-download-detail"),
    path("admin-portal/academic/dashboard/", admin_academic_views.AdminAcademicDashboardView.as_view(), name="admin-academic-dashboard"),
]
