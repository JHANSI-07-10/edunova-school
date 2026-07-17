import json
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .roles import IsAdmin, log_action
from .views import row, rows, serialise, table_exists

# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def _get_admin_user(request):
    return getattr(request, "user", None)


# ---------------------------------------------------------------------------
# Admin — Academic Level Management
# ---------------------------------------------------------------------------

class AdminAcademicLevelView(APIView):
    """GET list / POST create academic levels. IsAdmin."""
    permission_classes = [IsAuthenticated, IsAdmin]

    def get(self, request):
        if not table_exists("portal_academic_level"):
            return Response([])
        data = rows(
            "SELECT id, name, description, icon_name, sort_order, is_published "
            "FROM portal_academic_level ORDER BY sort_order"
        )
        return Response(serialise(data))

    def post(self, request):
        if not table_exists("portal_academic_level"):
            return Response({"detail": "Table not found."}, status=500)
        d = request.data
        name = (d.get("name") or "").strip()
        if not name:
            return Response({"detail": "Name is required."}, status=400)
        existing = row("SELECT id FROM portal_academic_level WHERE name=%s", [name])
        if existing:
            return Response({"detail": "Level with this name already exists."}, status=409)
        rid = row(
            "INSERT INTO portal_academic_level (name, description, icon_name, sort_order, is_published) "
            "VALUES (%s,%s,%s,%s,%s) RETURNING id",
            [name, d.get("description", ""), d.get("icon_name", ""), d.get("sort_order", 0), d.get("is_published", True)],
        )
        return Response({"id": rid["id"], "detail": "Created."}, status=201)

    def put(self, request, record_id=None):
        if not table_exists("portal_academic_level"):
            return Response({"detail": "Table not found."}, status=500)
        rid = record_id or request.data.get("id")
        if not rid:
            return Response({"detail": "id is required."}, status=400)
        d = request.data
        sets, params = [], []
        for col in ("name", "description", "icon_name", "sort_order", "is_published"):
            if col in d:
                sets.append(f"{col}=%s")
                params.append(d[col])
        if not sets:
            return Response({"detail": "Nothing to update."}, status=400)
        params.append(rid)
        row(f"UPDATE portal_academic_level SET {', '.join(sets)} WHERE id=%s RETURNING id", params)
        return Response({"detail": "Updated."})

    def delete(self, request, record_id):
        if not table_exists("portal_academic_level"):
            return Response({"detail": "Table not found."}, status=500)
        row("DELETE FROM portal_academic_level WHERE id=%s", [record_id])
        return Response({"detail": "Deleted."})


# ---------------------------------------------------------------------------
# Admin — Class Detail Management
# ---------------------------------------------------------------------------

class AdminClassDetailView(APIView):
    """GET list / POST create / PUT update class detail content. IsAdmin."""
    permission_classes = [IsAuthenticated, IsAdmin]

    def get(self, request):
        if not table_exists("portal_class_detail"):
            return Response([])
        data = rows(
            "SELECT cd.id, cd.class_id, c.name AS class_name, c.section, "
            "cd.academic_level, cd.description, cd.age_criteria, "
            "cd.student_teacher_ratio, cd.learning_objectives, cd.academic_approach, "
            "cd.facilities, cd.activities, cd.co_curricular, cd.assessment_pattern, "
            "cd.promotion_policy, cd.learning_outcomes, cd.cover_image_url, "
            "cd.gallery_images, cd.is_published, cd.sort_order, "
            "cd.meta_title, cd.meta_description, cd.created_at, cd.updated_at "
            "FROM portal_class_detail cd "
            "JOIN portal_class c ON c.id=cd.class_id "
            "ORDER BY c.name, c.section"
        )
        return Response(serialise(data))

    def post(self, request):
        if not table_exists("portal_class_detail"):
            return Response({"detail": "Table not found."}, status=500)
        d = request.data
        class_id = d.get("class_id")
        if not class_id:
            return Response({"detail": "class_id is required."}, status=400)
        existing = row("SELECT id FROM portal_class_detail WHERE class_id=%s", [class_id])
        if existing:
            return Response({"detail": "Detail already exists for this class. Use PUT to update."}, status=409)
        rid = row(
            "INSERT INTO portal_class_detail "
            "(class_id, academic_level, description, age_criteria, student_teacher_ratio, "
            "learning_objectives, academic_approach, facilities, activities, co_curricular, "
            "assessment_pattern, promotion_policy, learning_outcomes, cover_image_url, "
            "gallery_images, is_published, sort_order, meta_title, meta_description) "
            "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) "
            "RETURNING id",
            [class_id, d.get("academic_level", "Primary"), d.get("description", ""),
             d.get("age_criteria", ""), d.get("student_teacher_ratio", ""),
             d.get("learning_objectives", ""), d.get("academic_approach", ""),
             d.get("facilities", ""), d.get("activities", ""), d.get("co_curricular", ""),
             d.get("assessment_pattern", ""), d.get("promotion_policy", ""),
             d.get("learning_outcomes", ""), d.get("cover_image_url", ""),
             d.get("gallery_images", ""), d.get("is_published", True),
             d.get("sort_order", 0), d.get("meta_title", ""), d.get("meta_description", "")],
        )
        return Response({"id": rid["id"], "detail": "Created."}, status=201)

    def put(self, request, record_id):
        if not table_exists("portal_class_detail"):
            return Response({"detail": "Table not found."}, status=500)
        d = request.data
        cols = [
            "academic_level", "description", "age_criteria", "student_teacher_ratio",
            "learning_objectives", "academic_approach", "facilities", "activities",
            "co_curricular", "assessment_pattern", "promotion_policy", "learning_outcomes",
            "cover_image_url", "gallery_images", "is_published", "sort_order",
            "meta_title", "meta_description",
        ]
        sets, params = [], []
        for c in cols:
            if c in d:
                sets.append(f"{c}=%s")
                params.append(d[c])
        if not sets:
            return Response({"detail": "Nothing to update."}, status=400)
        sets.append("updated_at=now()")
        params.append(record_id)
        row(f"UPDATE portal_class_detail SET {', '.join(sets)} WHERE id=%s RETURNING id", params)
        return Response({"detail": "Updated."})

    def delete(self, request, record_id):
        if not table_exists("portal_class_detail"):
            return Response({"detail": "Table not found."}, status=500)
        row("DELETE FROM portal_class_detail WHERE id=%s", [record_id])
        return Response({"detail": "Deleted."})


# ---------------------------------------------------------------------------
# Admin — Subject Detail Management
# ---------------------------------------------------------------------------

class AdminSubjectDetailView(APIView):
    """GET list / POST create / PUT update subject detail content. IsAdmin."""
    permission_classes = [IsAuthenticated, IsAdmin]

    def get(self, request):
        if not table_exists("portal_subject_detail"):
            return Response([])
        data = rows(
            "SELECT sd.id, sd.subject_id, s.name AS subject_name, s.subject_code, "
            "sd.description, sd.learning_outcomes, sd.teaching_methodology, "
            "sd.activities, sd.projects, sd.assessment, sd.recommended_books, "
            "sd.cover_image_url, sd.is_published, sd.sort_order, "
            "sd.meta_title, sd.meta_description, sd.created_at, sd.updated_at "
            "FROM portal_subject_detail sd "
            "JOIN portal_subject s ON s.id=sd.subject_id "
            "ORDER BY s.name"
        )
        return Response(serialise(data))

    def post(self, request):
        if not table_exists("portal_subject_detail"):
            return Response({"detail": "Table not found."}, status=500)
        d = request.data
        subject_id = d.get("subject_id")
        if not subject_id:
            return Response({"detail": "subject_id is required."}, status=400)
        existing = row("SELECT id FROM portal_subject_detail WHERE subject_id=%s", [subject_id])
        if existing:
            return Response({"detail": "Detail already exists for this subject. Use PUT to update."}, status=409)
        rid = row(
            "INSERT INTO portal_subject_detail "
            "(subject_id, description, learning_outcomes, teaching_methodology, "
            "activities, projects, assessment, recommended_books, cover_image_url, "
            "is_published, sort_order, meta_title, meta_description) "
            "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) "
            "RETURNING id",
            [subject_id, d.get("description", ""), d.get("learning_outcomes", ""),
             d.get("teaching_methodology", ""), d.get("activities", ""),
             d.get("projects", ""), d.get("assessment", ""),
             d.get("recommended_books", ""), d.get("cover_image_url", ""),
             d.get("is_published", True), d.get("sort_order", 0),
             d.get("meta_title", ""), d.get("meta_description", "")],
        )
        return Response({"id": rid["id"], "detail": "Created."}, status=201)

    def put(self, request, record_id):
        if not table_exists("portal_subject_detail"):
            return Response({"detail": "Table not found."}, status=500)
        d = request.data
        cols = [
            "description", "learning_outcomes", "teaching_methodology",
            "activities", "projects", "assessment", "recommended_books",
            "cover_image_url", "is_published", "sort_order",
            "meta_title", "meta_description",
        ]
        sets, params = [], []
        for c in cols:
            if c in d:
                sets.append(f"{c}=%s")
                params.append(d[c])
        if not sets:
            return Response({"detail": "Nothing to update."}, status=400)
        sets.append("updated_at=now()")
        params.append(record_id)
        row(f"UPDATE portal_subject_detail SET {', '.join(sets)} WHERE id=%s RETURNING id", params)
        return Response({"detail": "Updated."})

    def delete(self, request, record_id):
        if not table_exists("portal_subject_detail"):
            return Response({"detail": "Table not found."}, status=500)
        row("DELETE FROM portal_subject_detail WHERE id=%s", [record_id])
        return Response({"detail": "Deleted."})


# ---------------------------------------------------------------------------
# Admin — Class-Subject Mapping
# ---------------------------------------------------------------------------

class AdminClassSubjectView(APIView):
    """GET list / POST create / DELETE class-subject mapping. IsAdmin."""
    permission_classes = [IsAuthenticated, IsAdmin]

    def get(self, request):
        if not table_exists("portal_class_subject"):
            return Response([])
        class_id = request.query_params.get("class_id")
        if class_id:
            data = rows(
                "SELECT cs.id, cs.class_id, c.name AS class_name, c.section, "
                "cs.subject_id, s.name AS subject_name, s.subject_code, "
                "cs.is_compulsory, cs.sort_order "
                "FROM portal_class_subject cs "
                "JOIN portal_class c ON c.id=cs.class_id "
                "JOIN portal_subject s ON s.id=cs.subject_id "
                "WHERE cs.class_id=%s ORDER BY cs.sort_order, s.name",
                [class_id],
            )
        else:
            data = rows(
                "SELECT cs.id, cs.class_id, c.name AS class_name, c.section, "
                "cs.subject_id, s.name AS subject_name, s.subject_code, "
                "cs.is_compulsory, cs.sort_order "
                "FROM portal_class_subject cs "
                "JOIN portal_class c ON c.id=cs.class_id "
                "JOIN portal_subject s ON s.id=cs.subject_id "
                "ORDER BY c.name, c.section, cs.sort_order, s.name"
            )
        return Response(serialise(data))

    def post(self, request):
        if not table_exists("portal_class_subject"):
            return Response({"detail": "Table not found."}, status=500)
        d = request.data
        class_id = d.get("class_id")
        subject_id = d.get("subject_id")
        if not class_id or not subject_id:
            return Response({"detail": "class_id and subject_id required."}, status=400)
        existing = row(
            "SELECT id FROM portal_class_subject WHERE class_id=%s AND subject_id=%s",
            [class_id, subject_id],
        )
        if existing:
            return Response({"detail": "Mapping already exists."}, status=409)
        rid = row(
            "INSERT INTO portal_class_subject (class_id, subject_id, is_compulsory, sort_order) "
            "VALUES (%s,%s,%s,%s) RETURNING id",
            [class_id, subject_id, d.get("is_compulsory", True), d.get("sort_order", 0)],
        )
        return Response({"id": rid["id"], "detail": "Created."}, status=201)

    def delete(self, request, record_id):
        if not table_exists("portal_class_subject"):
            return Response({"detail": "Table not found."}, status=500)
        row("DELETE FROM portal_class_subject WHERE id=%s", [record_id])
        return Response({"detail": "Deleted."})


# ---------------------------------------------------------------------------
# Admin — Curriculum Management
# ---------------------------------------------------------------------------

class AdminCurriculumView(APIView):
    """GET list / POST create / PUT update / DELETE curriculum. IsAdmin."""
    permission_classes = [IsAuthenticated, IsAdmin]

    def get(self, request):
        if not table_exists("portal_curriculum"):
            return Response([])
        data = rows(
            "SELECT cu.id, cu.class_id, c.name AS class_name, c.section, "
            "cu.curriculum_name, cu.syllabus_description, cu.learning_outcomes, "
            "cu.semester_info, cu.topics_covered, cu.brochure_url, "
            "cu.is_published, cu.created_at, cu.updated_at "
            "FROM portal_curriculum cu "
            "JOIN portal_class c ON c.id=cu.class_id "
            "ORDER BY c.name, c.section, cu.curriculum_name"
        )
        return Response(serialise(data))

    def post(self, request):
        if not table_exists("portal_curriculum"):
            return Response({"detail": "Table not found."}, status=500)
        d = request.data
        class_id = d.get("class_id")
        curriculum_name = (d.get("curriculum_name") or "CBSE").strip()
        if not class_id:
            return Response({"detail": "class_id is required."}, status=400)
        existing = row(
            "SELECT id FROM portal_curriculum WHERE class_id=%s AND curriculum_name=%s",
            [class_id, curriculum_name],
        )
        if existing:
            return Response({"detail": "Curriculum already exists for this class."}, status=409)
        rid = row(
            "INSERT INTO portal_curriculum "
            "(class_id, curriculum_name, syllabus_description, learning_outcomes, "
            "semester_info, topics_covered, brochure_url, is_published) "
            "VALUES (%s,%s,%s,%s,%s,%s,%s,%s) RETURNING id",
            [class_id, curriculum_name, d.get("syllabus_description", ""),
             d.get("learning_outcomes", ""), d.get("semester_info", ""),
             d.get("topics_covered", ""), d.get("brochure_url", ""),
             d.get("is_published", True)],
        )
        return Response({"id": rid["id"], "detail": "Created."}, status=201)

    def put(self, request, record_id):
        if not table_exists("portal_curriculum"):
            return Response({"detail": "Table not found."}, status=500)
        d = request.data
        cols = [
            "syllabus_description", "learning_outcomes", "semester_info",
            "topics_covered", "brochure_url", "is_published",
        ]
        sets, params = [], []
        for c in cols:
            if c in d:
                sets.append(f"{c}=%s")
                params.append(d[c])
        if not sets:
            return Response({"detail": "Nothing to update."}, status=400)
        sets.append("updated_at=now()")
        params.append(record_id)
        row(f"UPDATE portal_curriculum SET {', '.join(sets)} WHERE id=%s RETURNING id", params)
        return Response({"detail": "Updated."})

    def delete(self, request, record_id):
        if not table_exists("portal_curriculum"):
            return Response({"detail": "Table not found."}, status=500)
        row("DELETE FROM portal_curriculum WHERE id=%s", [record_id])
        return Response({"detail": "Deleted."})


# ---------------------------------------------------------------------------
# Admin — Faculty Profile Management
# ---------------------------------------------------------------------------

class AdminFacultyManagementView(APIView):
    """GET list / POST create / PUT update / DELETE faculty profiles. IsAdmin."""
    permission_classes = [IsAuthenticated, IsAdmin]

    def get(self, request):
        if not table_exists("portal_faculty_profile"):
            return Response([])
        data = rows(
            "SELECT fp.id, fp.user_id, u.first_name, u.last_name, u.email, "
            "fp.designation, fp.qualification_detail, fp.experience_years, "
            "fp.specializations, fp.achievements, fp.research, fp.bio, "
            "fp.photo_url, fp.is_published, fp.sort_order, "
            "fp.created_at, fp.updated_at "
            "FROM portal_faculty_profile fp "
            "JOIN auth_user u ON u.id=fp.user_id "
            "ORDER BY fp.sort_order, u.last_name"
        )
        return Response(serialise(data))

    def post(self, request):
        if not table_exists("portal_faculty_profile"):
            return Response({"detail": "Table not found."}, status=500)
        d = request.data
        user_id = d.get("user_id")
        if not user_id:
            return Response({"detail": "user_id is required."}, status=400)
        existing = row("SELECT id FROM portal_faculty_profile WHERE user_id=%s", [user_id])
        if existing:
            return Response({"detail": "Faculty profile already exists for this user."}, status=409)
        rid = row(
            "INSERT INTO portal_faculty_profile "
            "(user_id, designation, qualification_detail, experience_years, "
            "specializations, achievements, research, bio, photo_url, "
            "is_published, sort_order) "
            "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) RETURNING id",
            [user_id, d.get("designation", ""), d.get("qualification_detail", ""),
             d.get("experience_years", 0), d.get("specializations", ""),
             d.get("achievements", ""), d.get("research", ""), d.get("bio", ""),
             d.get("photo_url", ""), d.get("is_published", True),
             d.get("sort_order", 0)],
        )
        log_action(_get_admin_user(request), "Created faculty profile", user_id=user_id)
        return Response({"id": rid["id"], "detail": "Created."}, status=201)

    def put(self, request, record_id):
        if not table_exists("portal_faculty_profile"):
            return Response({"detail": "Table not found."}, status=500)
        d = request.data
        cols = [
            "designation", "qualification_detail", "experience_years",
            "specializations", "achievements", "research", "bio",
            "photo_url", "is_published", "sort_order",
        ]
        sets, params = [], []
        for c in cols:
            if c in d:
                sets.append(f"{c}=%s")
                params.append(d[c])
        if not sets:
            return Response({"detail": "Nothing to update."}, status=400)
        sets.append("updated_at=now()")
        params.append(record_id)
        row(f"UPDATE portal_faculty_profile SET {', '.join(sets)} WHERE id=%s RETURNING id", params)
        return Response({"detail": "Updated."})

    def delete(self, request, record_id):
        if not table_exists("portal_faculty_profile"):
            return Response({"detail": "Table not found."}, status=500)
        row("DELETE FROM portal_faculty_profile WHERE id=%s", [record_id])
        return Response({"detail": "Deleted."})


# ---------------------------------------------------------------------------
# Admin — Faculty-Subject-Class Mapping
# ---------------------------------------------------------------------------

class AdminFacultySubjectView(APIView):
    """GET / POST / DELETE faculty-subject-class mapping. IsAdmin."""
    permission_classes = [IsAuthenticated, IsAdmin]

    def get(self, request):
        if not table_exists("portal_faculty_subject"):
            return Response([])
        faculty_id = request.query_params.get("faculty_id")
        if faculty_id:
            data = rows(
                "SELECT fs.id, fs.faculty_id, fp.user_id, "
                "u.first_name, u.last_name, "
                "fs.class_id, c.name AS class_name, c.section, "
                "fs.subject_id, s.name AS subject_name, s.subject_code "
                "FROM portal_faculty_subject fs "
                "JOIN portal_faculty_profile fp ON fp.id=fs.faculty_id "
                "JOIN auth_user u ON u.id=fp.user_id "
                "JOIN portal_class c ON c.id=fs.class_id "
                "JOIN portal_subject s ON s.id=fs.subject_id "
                "WHERE fs.faculty_id=%s ORDER BY c.name, s.name",
                [faculty_id],
            )
        else:
            data = rows(
                "SELECT fs.id, fs.faculty_id, "
                "u.first_name, u.last_name, "
                "fs.class_id, c.name AS class_name, c.section, "
                "fs.subject_id, s.name AS subject_name, s.subject_code "
                "FROM portal_faculty_subject fs "
                "JOIN portal_faculty_profile fp ON fp.id=fs.faculty_id "
                "JOIN auth_user u ON u.id=fp.user_id "
                "JOIN portal_class c ON c.id=fs.class_id "
                "JOIN portal_subject s ON s.id=fs.subject_id "
                "ORDER BY u.last_name, c.name"
            )
        return Response(serialise(data))

    def post(self, request):
        if not table_exists("portal_faculty_subject"):
            return Response({"detail": "Table not found."}, status=500)
        d = request.data
        faculty_id = d.get("faculty_id")
        class_id = d.get("class_id")
        subject_id = d.get("subject_id")
        if not all([faculty_id, class_id, subject_id]):
            return Response({"detail": "faculty_id, class_id, subject_id required."}, status=400)
        existing = row(
            "SELECT id FROM portal_faculty_subject "
            "WHERE faculty_id=%s AND class_id=%s AND subject_id=%s",
            [faculty_id, class_id, subject_id],
        )
        if existing:
            return Response({"detail": "Mapping already exists."}, status=409)
        rid = row(
            "INSERT INTO portal_faculty_subject (faculty_id, class_id, subject_id) "
            "VALUES (%s,%s,%s) RETURNING id",
            [faculty_id, class_id, subject_id],
        )
        return Response({"id": rid["id"], "detail": "Created."}, status=201)

    def delete(self, request, record_id):
        if not table_exists("portal_faculty_subject"):
            return Response({"detail": "Table not found."}, status=500)
        row("DELETE FROM portal_faculty_subject WHERE id=%s", [record_id])
        return Response({"detail": "Deleted."})


# ---------------------------------------------------------------------------
# Admin — Academic Downloads
# ---------------------------------------------------------------------------

class AdminAcademicDownloadView(APIView):
    """GET list / POST create / PUT update / DELETE academic downloads. IsAdmin."""
    permission_classes = [IsAuthenticated, IsAdmin]

    def get(self, request):
        if not table_exists("portal_academic_download"):
            return Response([])
        data = rows(
            "SELECT d.id, d.title, d.description, d.file_url, d.file_type, "
            "d.category, d.target_class_id, d.target_audience, "
            "d.download_count, d.is_published, d.created_at "
            "FROM portal_academic_download d ORDER BY d.category, d.title"
        )
        return Response(serialise(data))

    def post(self, request):
        if not table_exists("portal_academic_download"):
            return Response({"detail": "Table not found."}, status=500)
        d = request.data
        title = (d.get("title") or "").strip()
        file_url = (d.get("file_url") or "").strip()
        if not title or not file_url:
            return Response({"detail": "title and file_url required."}, status=400)
        rid = row(
            "INSERT INTO portal_academic_download "
            "(title, description, file_url, file_type, category, "
            "target_class_id, target_audience, is_published) "
            "VALUES (%s,%s,%s,%s,%s,%s,%s,%s) RETURNING id",
            [title, d.get("description", ""), file_url, d.get("file_type", "PDF"),
             d.get("category", "Curriculum"), d.get("target_class_id"),
             d.get("target_audience", "public"), d.get("is_published", True)],
        )
        log_action(_get_admin_user(request), "Created academic download")
        return Response({"id": rid["id"], "detail": "Created."}, status=201)

    def put(self, request, record_id):
        if not table_exists("portal_academic_download"):
            return Response({"detail": "Table not found."}, status=500)
        d = request.data
        cols = [
            "title", "description", "file_url", "file_type", "category",
            "target_class_id", "target_audience", "is_published",
        ]
        sets, params = [], []
        for c in cols:
            if c in d:
                sets.append(f"{c}=%s")
                params.append(d[c])
        if not sets:
            return Response({"detail": "Nothing to update."}, status=400)
        params.append(record_id)
        row(f"UPDATE portal_academic_download SET {', '.join(sets)} WHERE id=%s RETURNING id", params)
        return Response({"detail": "Updated."})

    def delete(self, request, record_id):
        if not table_exists("portal_academic_download"):
            return Response({"detail": "Table not found."}, status=500)
        row("DELETE FROM portal_academic_download WHERE id=%s", [record_id])
        return Response({"detail": "Deleted."})


# ---------------------------------------------------------------------------
# Admin — Academic Content Dashboard (stats)
# ---------------------------------------------------------------------------

class AdminAcademicDashboardView(APIView):
    """GET dashboard stats for all academic website content. IsAdmin."""
    permission_classes = [IsAuthenticated, IsAdmin]

    def get(self, request):
        stats = {}
        for tbl, key in [
            ("portal_academic_level", "levels"),
            ("portal_class_detail", "class_details"),
            ("portal_subject_detail", "subject_details"),
            ("portal_class_subject", "class_subject_mappings"),
            ("portal_curriculum", "curriculum_entries"),
            ("portal_faculty_profile", "faculty_profiles"),
            ("portal_faculty_subject", "faculty_subject_mappings"),
            ("portal_academic_download", "downloads"),
        ]:
            if table_exists(tbl):
                r = row(f"SELECT COUNT(*) AS cnt FROM {tbl}")
                stats[key] = r["cnt"] if r else 0
            else:
                stats[key] = 0
        if table_exists("portal_class"):
            r = row("SELECT COUNT(*) AS cnt FROM portal_class")
            stats["total_classes"] = r["cnt"] if r else 0
        if table_exists("portal_subject"):
            r = row("SELECT COUNT(*) AS cnt FROM portal_subject")
            stats["total_subjects"] = r["cnt"] if r else 0
        if table_exists("portal_student_profile"):
            r = row("SELECT COUNT(*) AS cnt FROM portal_student_profile WHERE status='Active'")
            stats["active_students"] = r["cnt"] if r else 0
        return Response(stats)
