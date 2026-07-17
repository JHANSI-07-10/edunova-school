from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from .views import row, rows, serialise, table_exists


class AcademicLevelsView(APIView):
    """Public: list all academic levels."""
    permission_classes = [AllowAny]

    def get(self, request):
        if not table_exists("portal_academic_level"):
            return Response([])
        data = rows(
            "SELECT id, name, description, icon_name "
            "FROM portal_academic_level WHERE is_published=true ORDER BY sort_order"
        )
        return Response(serialise(data))


class PublicClassesListView(APIView):
    """Public: list classes with optional ?level= filter."""
    permission_classes = [AllowAny]

    def get(self, request):
        if not table_exists("portal_class"):
            return Response([])
        level = request.query_params.get("level", "")
        if level:
            data = rows(
                "SELECT c.id, c.name, c.section, c.curriculum, c.room_number, "
                "cd.description, cd.age_criteria, cd.student_teacher_ratio, "
                "cd.learning_objectives, cd.academic_approach, cd.facilities, "
                "cd.activities, cd.co_curricular, cd.assessment_pattern, "
                "cd.promotion_policy, cd.learning_outcomes, cd.cover_image_url, "
                "cd.academic_level "
                "FROM portal_class c "
                "LEFT JOIN portal_class_detail cd ON cd.class_id=c.id "
                "WHERE cd.is_published=true AND cd.academic_level=%s "
                "ORDER BY c.name, c.section",
                [level],
            )
        else:
            data = rows(
                "SELECT c.id, c.name, c.section, c.curriculum, c.room_number, "
                "cd.description, cd.age_criteria, cd.student_teacher_ratio, "
                "cd.learning_objectives, cd.academic_approach, cd.facilities, "
                "cd.activities, cd.co_curricular, cd.assessment_pattern, "
                "cd.promotion_policy, cd.learning_outcomes, cd.cover_image_url, "
                "cd.academic_level "
                "FROM portal_class c "
                "LEFT JOIN portal_class_detail cd ON cd.class_id=c.id "
                "WHERE (cd.is_published=true OR cd.id IS NULL) "
                "ORDER BY c.name, c.section"
            )
        return Response(serialise(data))


class PublicClassDetailView(APIView):
    """Public: full class detail by id."""
    permission_classes = [AllowAny]

    def get(self, request, class_id):
        if not table_exists("portal_class"):
            return Response({"detail": "Not found."}, status=404)
        r = row(
            "SELECT c.id, c.name, c.section, c.curriculum, c.room_number, "
            "cd.description, cd.age_criteria, cd.student_teacher_ratio, "
            "cd.learning_objectives, cd.academic_approach, cd.facilities, "
            "cd.activities, cd.co_curricular, cd.assessment_pattern, "
            "cd.promotion_policy, cd.learning_outcomes, cd.cover_image_url, "
            "cd.gallery_images, cd.meta_title, cd.meta_description, "
            "cd.academic_level "
            "FROM portal_class c "
            "LEFT JOIN portal_class_detail cd ON cd.class_id=c.id "
            "WHERE c.id=%s",
            [class_id],
        )
        if not r:
            return Response({"detail": "Not found."}, status=404)
        r = dict(r)
        if table_exists("portal_class_subject"):
            subs = rows(
                "SELECT cs.subject_id, s.name, s.subject_code, s.type, cs.is_compulsory "
                "FROM portal_class_subject cs "
                "JOIN portal_subject s ON s.id=cs.subject_id "
                "WHERE cs.class_id=%s ORDER BY cs.sort_order, s.name",
                [class_id],
            )
            r["subjects"] = serialise(subs)
        else:
            subs = rows(
                "SELECT id AS subject_id, name, subject_code, type "
                "FROM portal_subject ORDER BY name"
            )
            r["subjects"] = serialise(subs)
        if table_exists("portal_curriculum"):
            cur = rows(
                "SELECT id, curriculum_name, syllabus_description, "
                "learning_outcomes, semester_info, topics_covered, brochure_url "
                "FROM portal_curriculum WHERE class_id=%s AND is_published=true "
                "ORDER BY curriculum_name",
                [class_id],
            )
            r["curriculum"] = serialise(cur)
        return Response(r)


class PublicSubjectsListView(APIView):
    """Public: list all subjects."""
    permission_classes = [AllowAny]

    def get(self, request):
        if not table_exists("portal_subject"):
            return Response([])
        data = rows(
            "SELECT s.id, s.name, s.subject_code, s.type, "
            "sd.description, sd.learning_outcomes, sd.teaching_methodology, "
            "sd.activities, sd.projects, sd.assessment, sd.cover_image_url "
            "FROM portal_subject s "
            "LEFT JOIN portal_subject_detail sd ON sd.subject_id=s.id "
            "WHERE (sd.is_published=true OR sd.id IS NULL) "
            "ORDER BY s.name"
        )
        return Response(serialise(data))


class PublicSubjectDetailView(APIView):
    """Public: full subject detail by id."""
    permission_classes = [AllowAny]

    def get(self, request, subject_id):
        if not table_exists("portal_subject"):
            return Response({"detail": "Not found."}, status=404)
        r = row(
            "SELECT s.id, s.name, s.subject_code, s.type, "
            "sd.description, sd.learning_outcomes, sd.teaching_methodology, "
            "sd.activities, sd.projects, sd.assessment, sd.recommended_books, "
            "sd.cover_image_url, sd.meta_title, sd.meta_description "
            "FROM portal_subject s "
            "LEFT JOIN portal_subject_detail sd ON sd.subject_id=s.id "
            "WHERE s.id=%s",
            [subject_id],
        )
        if not r:
            return Response({"detail": "Not found."}, status=404)
        r = dict(r)
        if table_exists("portal_class_subject"):
            classes = rows(
                "SELECT cs.class_id, c.name, c.section, c.curriculum "
                "FROM portal_class_subject cs "
                "JOIN portal_class c ON c.id=cs.class_id "
                "WHERE cs.subject_id=%s ORDER BY c.name, c.section",
                [subject_id],
            )
            r["classes"] = serialise(classes)
        return Response(r)


class PublicFacultyListView(APIView):
    """Public: faculty directory."""
    permission_classes = [AllowAny]

    def get(self, request):
        if not table_exists("portal_faculty_profile"):
            return Response([])
        data = rows(
            "SELECT fp.id, fp.designation, fp.qualification_detail, "
            "fp.experience_years, fp.specializations, fp.achievements, "
            "fp.bio, fp.photo_url, "
            "u.id AS user_id, u.first_name, u.last_name, u.email "
            "FROM portal_faculty_profile fp "
            "JOIN auth_user u ON u.id=fp.user_id "
            "WHERE fp.is_published=true "
            "ORDER BY fp.sort_order, u.last_name, u.first_name"
        )
        return Response(serialise(data))


class PublicFacultyDetailView(APIView):
    """Public: single faculty member with subjects."""
    permission_classes = [AllowAny]

    def get(self, request, faculty_id):
        if not table_exists("portal_faculty_profile"):
            return Response({"detail": "Not found."}, status=404)
        r = row(
            "SELECT fp.id, fp.designation, fp.qualification_detail, "
            "fp.experience_years, fp.specializations, fp.achievements, "
            "fp.research, fp.bio, fp.photo_url, "
            "u.id AS user_id, u.first_name, u.last_name, u.email "
            "FROM portal_faculty_profile fp "
            "JOIN auth_user u ON u.id=fp.user_id "
            "WHERE fp.id=%s",
            [faculty_id],
        )
        if not r:
            return Response({"detail": "Not found."}, status=404)
        r = dict(r)
        if table_exists("portal_faculty_subject"):
            subs = rows(
                "SELECT fs.class_id, c.name AS class_name, c.section, "
                "fs.subject_id, s.name AS subject_name, s.subject_code "
                "FROM portal_faculty_subject fs "
                "JOIN portal_class c ON c.id=fs.class_id "
                "JOIN portal_subject s ON s.id=fs.subject_id "
                "WHERE fs.faculty_id=%s ORDER BY c.name, c.section, s.name",
                [faculty_id],
            )
            r["subjects"] = serialise(subs)
        return Response(r)


class PublicCurriculumView(APIView):
    """Public: curriculum details for a class."""
    permission_classes = [AllowAny]

    def get(self, request):
        if not table_exists("portal_curriculum"):
            return Response([])
        class_id = request.query_params.get("class_id")
        if not class_id:
            data = rows(
                "SELECT cu.id, cu.class_id, c.name AS class_name, c.section, "
                "cu.curriculum_name, cu.syllabus_description, cu.learning_outcomes, "
                "cu.semester_info, cu.topics_covered, cu.brochure_url "
                "FROM portal_curriculum cu "
                "JOIN portal_class c ON c.id=cu.class_id "
                "WHERE cu.is_published=true "
                "ORDER BY c.name, c.section, cu.curriculum_name"
            )
        else:
            data = rows(
                "SELECT cu.id, cu.class_id, c.name AS class_name, c.section, "
                "cu.curriculum_name, cu.syllabus_description, cu.learning_outcomes, "
                "cu.semester_info, cu.topics_covered, cu.brochure_url "
                "FROM portal_curriculum cu "
                "JOIN portal_class c ON c.id=cu.class_id "
                "WHERE cu.class_id=%s AND cu.is_published=true "
                "ORDER BY cu.curriculum_name",
                [class_id],
            )
        return Response(serialise(data))


class PublicAcademicDownloadsView(APIView):
    """Public: academic downloads (brochures, syllabus, etc.)."""
    permission_classes = [AllowAny]

    def get(self, request):
        if not table_exists("portal_academic_download"):
            return Response([])
        category = request.query_params.get("category", "")
        class_id = request.query_params.get("class_id", "")
        query = (
            "SELECT d.id, d.title, d.description, d.file_url, d.file_type, "
            "d.category, d.target_class_id, d.download_count, d.created_at "
            "FROM portal_academic_download d WHERE d.is_published=true"
        )
        params = []
        if category:
            query += " AND d.category=%s"
            params.append(category)
        if class_id:
            query += " AND (d.target_class_id=%s OR d.target_class_id IS NULL)"
            params.append(class_id)
        query += " ORDER BY d.category, d.title"
        data = rows(query, params)
        return Response(serialise(data))


class PublicAcademicSearchView(APIView):
    """Public: search across classes, subjects, faculty."""
    permission_classes = [AllowAny]

    def get(self, request):
        q = request.query_params.get("q", "").strip()
        if len(q) < 2:
            return Response({"classes": [], "subjects": [], "faculty": []})
        pattern = f"%{q}%"
        results = {}
        if table_exists("portal_class"):
            cl = rows(
                "SELECT c.id, c.name, c.section, c.curriculum "
                "FROM portal_class c "
                "WHERE c.name ILIKE %s OR c.section ILIKE %s "
                "ORDER BY c.name LIMIT 20",
                [pattern, pattern],
            )
            results["classes"] = serialise(cl)
        else:
            results["classes"] = []
        if table_exists("portal_subject"):
            su = rows(
                "SELECT s.id, s.name, s.subject_code, s.type "
                "FROM portal_subject s "
                "WHERE s.name ILIKE %s OR s.subject_code ILIKE %s "
                "ORDER BY s.name LIMIT 20",
                [pattern, pattern],
            )
            results["subjects"] = serialise(su)
        else:
            results["subjects"] = []
        if table_exists("portal_faculty_profile"):
            fa = rows(
                "SELECT fp.id, u.first_name, u.last_name, fp.designation, "
                "fp.specializations "
                "FROM portal_faculty_profile fp "
                "JOIN auth_user u ON u.id=fp.user_id "
                "WHERE u.first_name ILIKE %s OR u.last_name ILIKE %s "
                "OR fp.designation ILIKE %s OR fp.specializations ILIKE %s "
                "ORDER BY u.last_name LIMIT 20",
                [pattern, pattern, pattern, pattern],
            )
            results["faculty"] = serialise(fa)
        else:
            results["faculty"] = []
        return Response(results)


class PublicAcademicStatsView(APIView):
    """Public: academic stats (counts of classes, subjects, faculty)."""
    permission_classes = [AllowAny]

    def get(self, request):
        stats = {}
        if table_exists("portal_class"):
            r = row("SELECT COUNT(*) AS cnt FROM portal_class")
            stats["classes"] = r["cnt"] if r else 0
        else:
            stats["classes"] = 0
        if table_exists("portal_subject"):
            r = row("SELECT COUNT(*) AS cnt FROM portal_subject")
            stats["subjects"] = r["cnt"] if r else 0
        else:
            stats["subjects"] = 0
        if table_exists("portal_faculty_profile"):
            r = row("SELECT COUNT(*) AS cnt FROM portal_faculty_profile WHERE is_published=true")
            stats["faculty"] = r["cnt"] if r else 0
        else:
            stats["faculty"] = 0
        if table_exists("portal_student_profile"):
            r = row("SELECT COUNT(*) AS cnt FROM portal_student_profile WHERE status='Active'")
            stats["students"] = r["cnt"] if r else 0
        else:
            stats["students"] = 0
        return Response(stats)
