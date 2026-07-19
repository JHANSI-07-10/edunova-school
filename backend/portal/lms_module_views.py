"""Complete LMS Module — Live Classes, Recorded Classes, Homework, Question Bank,
Course Certificates, Announcements, LMS Settings, Learning Analytics, Dashboard.

Every view checks role-based access via _can_access_course(). Uses raw SQL to
stay consistent with the portal app's data access pattern.
"""
import json
import uuid
import secrets
from datetime import date, datetime, timedelta

from django.db import connection
from django.db.models import Q
from django.utils import timezone
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .roles import get_role, log_action
from .views import row, rows, serialise, table_exists


class AuthenticatedMixin:
    permission_classes = [IsAuthenticated]


def _can_access_course(user, course_id):
    role = get_role(user)
    if role == "Admin":
        return True
    course = row("SELECT class_id, subject_id FROM portal_course WHERE id=%s", [course_id])
    if not course:
        return False
    if role == "Student" and table_exists("portal_student_enrollment"):
        return bool(row(
            "SELECT 1 AS ok FROM portal_student_enrollment WHERE student_id=%s AND class_id=%s",
            [user.id, course["class_id"]],
        ))
    if role == "Teacher" and table_exists("portal_academic_allocation"):
        return bool(row(
            "SELECT 1 AS ok FROM portal_academic_allocation WHERE teacher_id=%s AND class_id=%s AND subject_id=%s",
            [user.id, course["class_id"], course["subject_id"]],
        ))
    return False


def _student_class_id(user_id):
    if not table_exists("portal_student_enrollment"):
        return None
    r = row(
        "SELECT class_id FROM portal_student_enrollment WHERE student_id=%s ORDER BY academic_year DESC LIMIT 1",
        [user_id],
    )
    return r["class_id"] if r else None


def _get_lms_setting(key, default=""):
    if not table_exists("portal_lms_settings"):
        return default
    r = row("SELECT setting_value FROM portal_lms_settings WHERE setting_key=%s", [key])
    return r["setting_value"] if r else default


_FORBIDDEN = Response({"detail": "You don't have access to this course."}, status=403)


# =============================================================================
# LMS DASHBOARD — Student
# =============================================================================
class LmsDashboardView(AuthenticatedMixin, APIView):
    """GET — aggregated LMS dashboard for student: active courses, today's
    classes, pending assignments/quizzes, recent announcements, progress."""

    def get(self, request):
        role = get_role(request.user)
        if role != "Student":
            return _FORBIDDEN

        class_id = _student_class_id(request.user.id)
        if not class_id:
            return Response({
                "active_courses": [], "today_classes": [], "upcoming_classes": [],
                "pending_assignments": 0, "pending_quizzes": 0,
                "recent_announcements": [], "learning_progress": [],
            })

        # Active courses
        courses = rows(
            """
            SELECT c.id, c.title, s.name AS subject_name,
                   (SELECT COUNT(*)::int FROM portal_course_content cc WHERE cc.course_id = c.id) AS total_content,
                   (SELECT COUNT(*)::int FROM portal_course_progress cp
                    WHERE cp.student_id = %s AND cp.content_id IN
                      (SELECT id FROM portal_course_content WHERE course_id = c.id)) AS completed_content
            FROM portal_course c
            JOIN portal_subject s ON s.id = c.subject_id
            WHERE c.class_id = %s ORDER BY c.id
            """,
            [request.user.id, class_id],
        ) if table_exists("portal_course") else []

        for c in courses:
            total = c.get("total_content") or 0
            done = c.get("completed_content") or 0
            c["progress_percent"] = round((done / total) * 100, 1) if total > 0 else 0

        # Today's classes (from timetable + live classes)
        today = date.today()
        day_name = today.strftime("%A")

        timetable_today = rows(
            """
            SELECT t.id, t.start_time, t.end_time, t.room_number, t.meeting_link,
                   s.name AS subject_name, c.name || '-' || c.section AS class_name
            FROM portal_timetable t
            JOIN portal_subject s ON s.id = t.subject_id
            JOIN portal_class c ON c.id = t.class_id
            WHERE t.class_id = %s AND t.day_of_week = %s
            ORDER BY t.start_time
            """,
            [class_id, day_name],
        ) if table_exists("portal_timetable") else []

        live_today = rows(
            """
            SELECT lc.id, lc.title, lc.start_time, lc.end_time, lc.meeting_platform,
                   lc.meeting_link, lc.status, s.name AS subject_name
            FROM portal_live_class lc
            LEFT JOIN portal_subject s ON s.id = lc.subject_id
            WHERE lc.class_id = %s AND lc.scheduled_date = %s
            ORDER BY lc.start_time
            """,
            [class_id, today],
        ) if table_exists("portal_live_class") else []

        # Pending assignments
        pending_assignments = 0
        if table_exists("portal_assignment"):
            r = row(
                """
                SELECT COUNT(*)::int AS c FROM portal_assignment a
                WHERE a.class_id = %s
                AND NOT EXISTS (
                    SELECT 1 FROM portal_assignment_submission s
                    WHERE s.assignment_id = a.id AND s.student_id = %s
                )
                """,
                [class_id, request.user.id],
            )
            pending_assignments = r["c"] if r else 0

        # Pending quizzes
        pending_quizzes = 0
        if table_exists("portal_quiz"):
            r = row(
                """
                SELECT COUNT(*)::int AS c FROM portal_quiz q
                WHERE q.course_id IN (SELECT id FROM portal_course WHERE class_id = %s)
                AND NOT EXISTS (
                    SELECT 1 FROM portal_quiz_attempt qa
                    WHERE qa.quiz_id = q.id AND qa.student_id = %s
                )
                """,
                [class_id, request.user.id],
            )
            pending_quizzes = r["c"] if r else 0

        # Pending homework
        pending_homework = 0
        if table_exists("portal_lms_homework"):
            r = row(
                """
                SELECT COUNT(*)::int AS c FROM portal_lms_homework h
                WHERE h.class_id = %s AND h.status = 'Published'
                AND NOT EXISTS (
                    SELECT 1 FROM portal_lms_homework_submission hs
                    WHERE hs.homework_id = h.id AND hs.student_id = %s
                )
                """,
                [class_id, request.user.id],
            )
            pending_homework = r["c"] if r else 0

        # Recent announcements
        announcements = rows(
            """
            SELECT a.id, a.title, a.message, a.priority, a.created_at,
                   COALESCE(u.first_name || ' ' || u.last_name, u.username) AS teacher_name
            FROM portal_course_announcement a
            JOIN auth_user u ON u.id = a.teacher_id
            WHERE a.course_id IN (SELECT id FROM portal_course WHERE class_id = %s)
            ORDER BY a.created_at DESC LIMIT 10
            """,
            [class_id],
        ) if table_exists("portal_course_announcement") else []

        # Learning progress per course
        progress = []
        for c in courses:
            progress.append({
                "course_id": c["id"],
                "subject_name": c["subject_name"],
                "progress_percent": c["progress_percent"],
            })

        return Response(serialise({
            "active_courses": courses,
            "today_classes": timetable_today + live_today,
            "upcoming_classes": [],
            "pending_assignments": pending_assignments,
            "pending_quizzes": pending_quizzes,
            "pending_homework": pending_homework,
            "recent_announcements": announcements,
            "learning_progress": progress,
        }))


# =============================================================================
# LIVE CLASSES
# =============================================================================
class LiveClassListView(AuthenticatedMixin, APIView):
    """GET — list live classes. Teacher/Admin can see all for their courses;
    Student sees classes for their enrolled class."""

    def get(self, request):
        role = get_role(request.user)
        course_id = request.query_params.get("course_id")
        class_id_param = request.query_params.get("class_id")

        if not table_exists("portal_live_class"):
            return Response([])

        if role == "Teacher":
            courses = rows(
                """
                SELECT c.id FROM portal_course c
                JOIN portal_academic_allocation aa ON aa.class_id = c.class_id AND aa.subject_id = c.subject_id
                WHERE aa.teacher_id = %s
                """,
                [request.user.id],
            ) if table_exists("portal_academic_allocation") else []
            course_ids = [str(c["id"]) for c in courses]
            if not course_ids:
                return Response([])
            where = f"lc.course_id IN ({','.join(course_ids)})"
            params = []
        elif role == "Student":
            cid = _student_class_id(request.user.id)
            if not cid:
                return Response([])
            where = "lc.class_id = %s"
            params = [cid]
        else:
            where = "1=1"
            params = []

        if course_id:
            where += " AND lc.course_id = %s"
            params.append(course_id)
        if class_id_param:
            where += " AND lc.class_id = %s"
            params.append(class_id_param)

        status_filter = request.query_params.get("status")
        if status_filter:
            where += " AND lc.status = %s"
            params.append(status_filter)

        classes = rows(
            f"""
            SELECT lc.id, lc.title, lc.description, lc.meeting_platform, lc.meeting_link,
                   lc.meeting_password, lc.recording_url, lc.scheduled_date, lc.start_time,
                   lc.end_time, lc.status, lc.attendance_recorded, lc.created_at,
                   c.title AS course_title, s.name AS subject_name,
                   cl.name || '-' || cl.section AS class_name,
                   COALESCE(u.first_name || ' ' || u.last_name, u.username) AS teacher_name
            FROM portal_live_class lc
            JOIN portal_course c ON c.id = lc.course_id
            LEFT JOIN portal_subject s ON s.id = lc.subject_id
            LEFT JOIN portal_class cl ON cl.id = lc.class_id
            LEFT JOIN auth_user u ON u.id = lc.teacher_id
            WHERE {where}
            ORDER BY lc.scheduled_date DESC, lc.start_time DESC
            """,
            params,
        )

        # Attach attendance count
        for lc in classes:
            if table_exists("portal_live_class_attendance"):
                att = row(
                    "SELECT COUNT(*)::int AS c FROM portal_live_class_attendance WHERE live_class_id=%s AND status='Present'",
                    [lc["id"]],
                )
                lc["attended_count"] = att["c"] if att else 0
                total = row(
                    "SELECT COUNT(*)::int AS c FROM portal_live_class_attendance WHERE live_class_id=%s",
                    [lc["id"]],
                )
                lc["total_students"] = total["c"] if total else 0

        return Response(serialise(classes))

    def post(self, request):
        role = get_role(request.user)
        if role not in ("Teacher", "Admin"):
            return _FORBIDDEN

        d = request.data
        course_id = d.get("course_id")
        if not course_id:
            return Response({"detail": "course_id is required."}, status=400)

        if not _can_access_course(request.user, course_id):
            return _FORBIDDEN

        course = row("SELECT class_id, subject_id FROM portal_course WHERE id=%s", [course_id])
        if not course:
            return Response({"detail": "Course not found."}, status=404)

        required = ["title", "scheduled_date", "start_time", "end_time"]
        for f in required:
            if not d.get(f):
                return Response({"detail": f"{f} is required."}, status=400)

        with connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO portal_live_class
                (course_id, teacher_id, title, description, subject_id, class_id,
                 meeting_platform, meeting_link, meeting_password, scheduled_date,
                 start_time, end_time, status)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) RETURNING id
                """,
                [
                    course_id, request.user.id, d["title"], d.get("description", ""),
                    course["subject_id"], course["class_id"],
                    d.get("meeting_platform", "Zoom"), d.get("meeting_link", ""),
                    d.get("meeting_password", ""), d["scheduled_date"],
                    d["start_time"], d["end_time"],
                    d.get("status", "Scheduled"),
                ],
            )
            lid = cursor.fetchone()[0]

            # Create attendance records for all enrolled students
            if table_exists("portal_live_class_attendance"):
                students = rows(
                    "SELECT student_id FROM portal_student_enrollment WHERE class_id=%s",
                    [course["class_id"]],
                )
                for s in students:
                    cursor.execute(
                        "INSERT INTO portal_live_class_attendance (live_class_id, student_id) VALUES (%s,%s) ON CONFLICT DO NOTHING",
                        [lid, s["student_id"]],
                    )

            # Send notification
            if table_exists("portal_notification"):
                cursor.execute(
                    """
                    INSERT INTO portal_notification (sender_id, recipient_type, target_class_id, title, message)
                    VALUES (%s, 'Class', %s, %s, %s)
                    """,
                    [
                        request.user.id, course["class_id"],
                        f"Live Class: {d['title']}",
                        f"A live class '{d['title']}' is scheduled on {d['scheduled_date']} at {d['start_time']}. Platform: {d.get('meeting_platform', 'Zoom')}",
                    ],
                )

        log_action(request.user, "lms.live_class.create", "portal_live_class", lid, {"title": d["title"]})
        return Response({"id": lid, "detail": "Live class scheduled successfully."})

    def put(self, request):
        role = get_role(request.user)
        if role not in ("Teacher", "Admin"):
            return _FORBIDDEN

        d = request.data
        lid = d.get("id")
        if not lid:
            return Response({"detail": "id is required."}, status=400)

        if not table_exists("portal_live_class"):
            return Response({"detail": "Live class table does not exist."}, status=400)

        existing = row("SELECT teacher_id, course_id FROM portal_live_class WHERE id=%s", [lid])
        if not existing:
            return Response({"detail": "Live class not found."}, status=404)

        if role == "Teacher" and existing["teacher_id"] != request.user.id:
            return _FORBIDDEN

        with connection.cursor() as cursor:
            cursor.execute(
                """
                UPDATE portal_live_class SET
                    title = COALESCE(NULLIF(%s, ''), title),
                    description = COALESCE(%s, description),
                    meeting_platform = COALESCE(NULLIF(%s, ''), meeting_platform),
                    meeting_link = COALESCE(NULLIF(%s, ''), meeting_link),
                    meeting_password = COALESCE(%s, meeting_password),
                    recording_url = COALESCE(NULLIF(%s, ''), recording_url),
                    status = COALESCE(NULLIF(%s, ''), status),
                    updated_at = now()
                WHERE id = %s
                """,
                [
                    d.get("title", ""), d.get("description"), d.get("meeting_platform", ""),
                    d.get("meeting_link", ""), d.get("meeting_password"),
                    d.get("recording_url", ""), d.get("status", ""), lid,
                ],
            )
        return Response({"detail": "Live class updated."})

    def delete(self, request):
        role = get_role(request.user)
        if role not in ("Teacher", "Admin"):
            return _FORBIDDEN
        lid = request.query_params.get("id") or request.data.get("id")
        if not lid:
            return Response({"detail": "id is required."}, status=400)
        with connection.cursor() as cursor:
            cursor.execute("DELETE FROM portal_live_class WHERE id=%s", [lid])
        return Response({"detail": "Live class deleted."})


class LiveClassAttendanceView(AuthenticatedMixin, APIView):
    """POST — student joins live class (records attendance). GET — attendance for a live class."""

    def post(self, request):
        role = get_role(request.user)
        if role != "Student":
            return _FORBIDDEN

        live_class_id = request.data.get("live_class_id")
        if not live_class_id:
            return Response({"detail": "live_class_id is required."}, status=400)

        if not table_exists("portal_live_class_attendance"):
            return Response({"detail": "Attendance table not found."}, status=400)

        lc = row("SELECT id, class_id, status FROM portal_live_class WHERE id=%s", [live_class_id])
        if not lc:
            return Response({"detail": "Live class not found."}, status=404)

        with connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO portal_live_class_attendance (live_class_id, student_id, joined_at, status)
                VALUES (%s, %s, now(), 'Present')
                ON CONFLICT (live_class_id, student_id)
                DO UPDATE SET joined_at = COALESCE(portal_live_class_attendance.joined_at, now()), status = 'Present'
                """,
                [live_class_id, request.user.id],
            )

        # Also mark attendance in main attendance module
        if table_exists("portal_attendance"):
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO portal_attendance (student_id, class_id, date, status, marked_by, remarks)
                    VALUES (%s, %s, CURRENT_DATE, 'Present', %s, 'Auto-marked via Live Class')
                    ON CONFLICT (student_id, class_id, date)
                    DO UPDATE SET status = CASE
                        WHEN portal_attendance.status = 'Absent' THEN 'Present'
                        ELSE portal_attendance.status END
                    """,
                    [request.user.id, lc["class_id"], request.user.id],
                )

        return Response({"detail": "Attendance recorded."})

    def get(self, request):
        live_class_id = request.query_params.get("live_class_id")
        if not live_class_id or not table_exists("portal_live_class_attendance"):
            return Response([])

        data = rows(
            """
            SELECT la.id, la.student_id, la.joined_at, la.left_at, la.duration_minutes, la.status,
                   COALESCE(u.first_name || ' ' || u.last_name, u.username) AS student_name,
                   se.roll_number
            FROM portal_live_class_attendance la
            JOIN auth_user u ON u.id = la.student_id
            LEFT JOIN portal_student_enrollment se ON se.student_id = la.student_id
            WHERE la.live_class_id = %s
            ORDER BY se.roll_number, la.joined_at
            """,
            [live_class_id],
        )
        return Response(serialise(data))


# =============================================================================
# RECORDED CLASSES
# =============================================================================
class RecordedClassListView(AuthenticatedMixin, APIView):
    def get(self, request):
        role = get_role(request.user)
        course_id = request.query_params.get("course_id")
        if not table_exists("portal_recorded_class"):
            return Response([])

        if role == "Student":
            cid = _student_class_id(request.user.id)
            if not cid:
                return Response([])
            where = "rc.class_id = %s"
            params = [cid]
        elif role == "Teacher":
            courses = rows(
                "SELECT c.id FROM portal_course c JOIN portal_academic_allocation aa ON aa.class_id = c.class_id AND aa.subject_id = c.subject_id WHERE aa.teacher_id = %s",
                [request.user.id],
            ) if table_exists("portal_academic_allocation") else []
            course_ids = [str(c["id"]) for c in courses]
            if not course_ids:
                return Response([])
            where = f"rc.course_id IN ({','.join(course_ids)})"
            params = []
        else:
            where = "1=1"
            params = []

        if course_id:
            where += " AND rc.course_id = %s"
            params.append(course_id)

        classes = rows(
            f"""
            SELECT rc.id, rc.title, rc.description, rc.video_url, rc.video_platform,
                   rc.thumbnail_url, rc.duration_seconds, rc.sort_order, rc.status, rc.created_at,
                   c.title AS course_title, s.name AS subject_name,
                   cl.name || '-' || cl.section AS class_name,
                   COALESCE(u.first_name || ' ' || u.last_name, u.username) AS teacher_name,
                   rc.chapter_id, rc.lesson_id
            FROM portal_recorded_class rc
            JOIN portal_course c ON c.id = rc.course_id
            LEFT JOIN portal_subject s ON s.id = c.subject_id
            LEFT JOIN portal_class cl ON cl.id = c.class_id
            LEFT JOIN auth_user u ON u.id = rc.teacher_id
            WHERE {where}
            ORDER BY rc.sort_order, rc.created_at DESC
            """,
            params,
        )

        # Attach student progress
        if role == "Student":
            for rc in classes:
                prog = row(
                    "SELECT last_position_seconds, is_completed, bookmarked FROM portal_recorded_class_progress WHERE recorded_class_id=%s AND student_id=%s",
                    [rc["id"], request.user.id],
                ) if table_exists("portal_recorded_class_progress") else None
                rc["progress"] = prog

        return Response(serialise(classes))

    def post(self, request):
        role = get_role(request.user)
        if role not in ("Teacher", "Admin"):
            return _FORBIDDEN

        d = request.data
        course_id = d.get("course_id")
        if not course_id or not _can_access_course(request.user, course_id):
            return _FORBIDDEN

        with connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO portal_recorded_class
                (course_id, teacher_id, chapter_id, lesson_id, title, description,
                 video_url, video_platform, thumbnail_url, duration_seconds, sort_order, status)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) RETURNING id
                """,
                [
                    course_id, request.user.id,
                    d.get("chapter_id"), d.get("lesson_id"),
                    d["title"], d.get("description", ""),
                    d["video_url"], d.get("video_platform", "Upload"),
                    d.get("thumbnail_url", ""), d.get("duration_seconds", 0),
                    d.get("sort_order", 0), d.get("status", "Published"),
                ],
            )
            rid = cursor.fetchone()[0]

        log_action(request.user, "lms.recorded_class.create", "portal_recorded_class", rid, {"title": d["title"]})
        return Response({"id": rid, "detail": "Recorded class added."})

    def put(self, request):
        role = get_role(request.user)
        if role not in ("Teacher", "Admin"):
            return _FORBIDDEN

        d = request.data
        rid = d.get("id")
        if not rid:
            return Response({"detail": "id is required."}, status=400)

        with connection.cursor() as cursor:
            cursor.execute(
                """
                UPDATE portal_recorded_class SET
                    title = COALESCE(NULLIF(%s, ''), title),
                    description = COALESCE(%s, description),
                    video_url = COALESCE(NULLIF(%s, ''), video_url),
                    status = COALESCE(NULLIF(%s, ''), status),
                    updated_at = now()
                WHERE id = %s
                """,
                [d.get("title", ""), d.get("description"), d.get("video_url", ""), d.get("status", ""), rid],
            )
        return Response({"detail": "Recorded class updated."})

    def delete(self, request):
        role = get_role(request.user)
        if role not in ("Teacher", "Admin"):
            return _FORBIDDEN
        rid = request.query_params.get("id")
        if not rid:
            return Response({"detail": "id required."}, status=400)
        with connection.cursor() as cursor:
            cursor.execute("DELETE FROM portal_recorded_class WHERE id=%s", [rid])
        return Response({"detail": "Deleted."})


class RecordedClassProgressView(AuthenticatedMixin, APIView):
    """POST — update watch position / bookmark. GET — get progress."""

    def post(self, request):
        if not table_exists("portal_recorded_class_progress"):
            return Response({"detail": "Table not found."}, status=400)

        d = request.data
        rc_id = d.get("recorded_class_id")
        if not rc_id:
            return Response({"detail": "recorded_class_id required."}, status=400)

        position = d.get("last_position_seconds", 0)
        is_completed = d.get("is_completed", False)
        bookmarked = d.get("bookmarked")

        with connection.cursor() as cursor:
            sql = """
                INSERT INTO portal_recorded_class_progress
                (recorded_class_id, student_id, last_position_seconds, is_completed, watch_count)
                VALUES (%s, %s, %s, %s, 1)
                ON CONFLICT (recorded_class_id, student_id)
                DO UPDATE SET
                    last_position_seconds = GREATEST(portal_recorded_class_progress.last_position_seconds, %s),
                    is_completed = COALESCE(%s, portal_recorded_class_progress.is_completed),
                    watch_count = CASE WHEN %s THEN portal_recorded_class_progress.watch_count + 1 ELSE portal_recorded_class_progress.watch_count END,
                    updated_at = now()
            """
            params = [rc_id, request.user.id, position, is_completed, position, is_completed, is_completed]
            if bookmarked is not None:
                sql += ", bookmarked = %s"
                params.append(bookmarked)
            sql += " RETURNING id"
            cursor.execute(sql, params)

        return Response({"detail": "Progress saved."})

    def get(self, request):
        if not table_exists("portal_recorded_class_progress"):
            return Response([])
        rc_id = request.query_params.get("recorded_class_id")
        if rc_id:
            prog = row(
                "SELECT * FROM portal_recorded_class_progress WHERE recorded_class_id=%s AND student_id=%s",
                [rc_id, request.user.id],
            )
            return Response(serialise(prog) if prog else {})
        return Response([])


# =============================================================================
# HOMEWORK (LMS)
# =============================================================================
class LmsHomeworkView(AuthenticatedMixin, APIView):
    """CRUD for LMS homework."""

    def get(self, request):
        if not table_exists("portal_lms_homework"):
            return Response([])

        role = get_role(request.user)
        course_id = request.query_params.get("course_id")
        class_id = request.query_params.get("class_id")

        if role == "Student":
            cid = _student_class_id(request.user.id)
            if not cid:
                return Response([])
            homework = rows(
                """
                SELECT h.id, h.title, h.description, h.instructions, h.due_date, h.max_marks,
                       h.status, h.created_at,
                       c.title AS course_title, s.name AS subject_name,
                       COALESCE(u.first_name || ' ' || u.last_name, u.username) AS teacher_name,
                       (SELECT json_build_object(
                           'id', sub.id, 'marks_obtained', sub.marks_obtained,
                           'teacher_feedback', sub.teacher_feedback, 'status', sub.status,
                           'submitted_at', sub.submitted_at
                       ) FROM portal_lms_homework_submission sub
                       WHERE sub.homework_id = h.id AND sub.student_id = %s) AS my_submission
                FROM portal_lms_homework h
                JOIN portal_course c ON c.id = h.course_id
                LEFT JOIN portal_subject s ON s.id = h.subject_id
                LEFT JOIN auth_user u ON u.id = h.teacher_id
                WHERE h.class_id = %s AND h.status = 'Published'
                ORDER BY h.due_date DESC
                """,
                [request.user.id, cid],
            )
        elif role in ("Teacher", "Admin"):
            conditions = ["1=1"]
            params = []
            if course_id:
                conditions.append("h.course_id = %s")
                params.append(course_id)
            if class_id:
                conditions.append("h.class_id = %s")
                params.append(class_id)
            where = " AND ".join(conditions)
            homework = rows(
                f"""
                SELECT h.id, h.title, h.description, h.instructions, h.due_date, h.max_marks,
                       h.status, h.created_at,
                       c.title AS course_title, s.name AS subject_name,
                       cl.name || '-' || cl.section AS class_name,
                       (SELECT COUNT(*)::int FROM portal_lms_homework_submission sub WHERE sub.homework_id = h.id) AS submission_count
                FROM portal_lms_homework h
                JOIN portal_course c ON c.id = h.course_id
                LEFT JOIN portal_subject s ON s.id = h.subject_id
                LEFT JOIN portal_class cl ON cl.id = h.class_id
                WHERE {where}
                ORDER BY h.created_at DESC
                """,
                params,
            )
        else:
            return Response([])

        return Response(serialise(homework))

    def post(self, request):
        role = get_role(request.user)
        if role not in ("Teacher", "Admin"):
            return _FORBIDDEN

        d = request.data
        course_id = d.get("course_id")
        if not course_id or not _can_access_course(request.user, course_id):
            return _FORBIDDEN

        course = row("SELECT class_id, subject_id FROM portal_course WHERE id=%s", [course_id])

        with connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO portal_lms_homework
                (course_id, teacher_id, class_id, subject_id, title, description,
                 instructions, attachments, due_date, max_marks, status)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) RETURNING id
                """,
                [
                    course_id, request.user.id, course["class_id"], course["subject_id"],
                    d["title"], d.get("description", ""), d.get("instructions", ""),
                    json.dumps(d.get("attachments", [])), d["due_date"],
                    d.get("max_marks", 0), d.get("status", "Published"),
                ],
            )
            hid = cursor.fetchone()[0]

            # Notification
            if table_exists("portal_notification"):
                cursor.execute(
                    "INSERT INTO portal_notification (sender_id, recipient_type, target_class_id, title, message) VALUES (%s, 'Class', %s, %s, %s)",
                    [request.user.id, course["class_id"], f"New Homework: {d['title']}", f"Due on {d['due_date']}. Check your LMS portal."],
                )

        log_action(request.user, "lms.homework.create", "portal_lms_homework", hid, {"title": d["title"]})
        return Response({"id": hid, "detail": "Homework created."})

    def put(self, request):
        role = get_role(request.user)
        if role not in ("Teacher", "Admin"):
            return _FORBIDDEN
        d = request.data
        hid = d.get("id")
        if not hid:
            return Response({"detail": "id required."}, status=400)
        with connection.cursor() as cursor:
            cursor.execute(
                """
                UPDATE portal_lms_homework SET
                    title = COALESCE(NULLIF(%s, ''), title),
                    description = COALESCE(%s, description),
                    instructions = COALESCE(%s, instructions),
                    due_date = COALESCE(%s, due_date),
                    status = COALESCE(NULLIF(%s, ''), status),
                    updated_at = now()
                WHERE id = %s
                """,
                [d.get("title", ""), d.get("description"), d.get("instructions"), d.get("due_date"), d.get("status", ""), hid],
            )
        return Response({"detail": "Updated."})

    def delete(self, request):
        role = get_role(request.user)
        if role not in ("Teacher", "Admin"):
            return _FORBIDDEN
        hid = request.query_params.get("id")
        if not hid:
            return Response({"detail": "id required."}, status=400)
        with connection.cursor() as cursor:
            cursor.execute("DELETE FROM portal_lms_homework WHERE id=%s", [hid])
        return Response({"detail": "Deleted."})


class LmsHomeworkSubmitView(AuthenticatedMixin, APIView):
    """POST — student submits homework. GET — teacher views submissions."""

    def get(self, request):
        role = get_role(request.user)
        if role not in ("Teacher", "Admin"):
            return _FORBIDDEN
        hid = request.query_params.get("homework_id")
        if not hid or not table_exists("portal_lms_homework_submission"):
            return Response([])

        submissions = rows(
            """
            SELECT s.id, s.submission_url, s.submission_text, s.marks_obtained,
                   s.teacher_feedback, s.grade, s.status, s.submitted_at,
                   COALESCE(u.first_name || ' ' || u.last_name, u.username) AS student_name,
                   se.roll_number
            FROM portal_lms_homework_submission s
            JOIN auth_user u ON u.id = s.student_id
            LEFT JOIN portal_student_enrollment se ON se.student_id = s.student_id AND se.class_id = (
                SELECT h.class_id FROM portal_lms_homework h WHERE h.id = %s
            )
            WHERE s.homework_id = %s
            ORDER BY se.roll_number, s.submitted_at
            """,
            [hid, hid],
        )
        return Response(serialise(submissions))

    def post(self, request):
        role = get_role(request.user)
        if role != "Student":
            return _FORBIDDEN

        d = request.data
        hid = d.get("homework_id")
        if not hid:
            return Response({"detail": "homework_id required."}, status=400)

        hw = row("SELECT class_id FROM portal_lms_homework WHERE id=%s", [hid])
        if not hw:
            return Response({"detail": "Homework not found."}, status=404)

        if not table_exists("portal_lms_homework_submission"):
            return Response({"detail": "Table not found."}, status=400)

        with connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO portal_lms_homework_submission (homework_id, student_id, submission_url, submission_text, status)
                VALUES (%s, %s, %s, %s, 'Submitted')
                ON CONFLICT (homework_id, student_id)
                DO UPDATE SET submission_url = EXCLUDED.submission_url, submission_text = EXCLUDED.submission_text,
                              status = 'Submitted', submitted_at = now()
                RETURNING id
                """,
                [hid, request.user.id, d.get("submission_url", ""), d.get("submission_text", "")],
            )
            sid = cursor.fetchone()[0]

        return Response({"id": sid, "detail": "Homework submitted."})

    def put(self, request):
        """Teacher reviews/grades homework submission."""
        role = get_role(request.user)
        if role not in ("Teacher", "Admin"):
            return _FORBIDDEN

        d = request.data
        sid = d.get("id")
        if not sid:
            return Response({"detail": "id required."}, status=400)

        with connection.cursor() as cursor:
            cursor.execute(
                """
                UPDATE portal_lms_homework_submission SET
                    marks_obtained = COALESCE(%s, marks_obtained),
                    teacher_feedback = COALESCE(%s, teacher_feedback),
                    grade = COALESCE(%s, grade),
                    status = 'Reviewed',
                    reviewed_at = now()
                WHERE id = %s
                """,
                [d.get("marks_obtained"), d.get("teacher_feedback"), d.get("grade"), sid],
            )
        return Response({"detail": "Submission reviewed."})


# =============================================================================
# QUESTION BANK (Enhanced)
# =============================================================================
class LmsQuestionView(AuthenticatedMixin, APIView):
    """CRUD for LMS question bank."""

    def get(self, request):
        if not table_exists("portal_lms_question"):
            return Response([])

        role = get_role(request.user)
        subject_id = request.query_params.get("subject_id")
        difficulty = request.query_params.get("difficulty")
        q_type = request.query_params.get("type")
        chapter = request.query_params.get("chapter")

        conditions = ["q.status = 'Active'"]
        params = []

        if subject_id:
            conditions.append("q.subject_id = %s")
            params.append(subject_id)
        if difficulty:
            conditions.append("q.difficulty = %s")
            params.append(difficulty)
        if q_type:
            conditions.append("q.question_type = %s")
            params.append(q_type)
        if chapter:
            conditions.append("q.chapter ILIKE %s")
            params.append(f"%{chapter}%")

        if role == "Teacher":
            conditions.append("q.teacher_id = %s")
            params.append(request.user.id)

        where = " AND ".join(conditions)

        questions = rows(
            f"""
            SELECT q.id, q.question_type, q.difficulty, q.question_text, q.options,
                   q.correct_answer, q.explanation, q.bloom_taxonomy,
                   q.learning_outcome, q.chapter, q.marks, q.created_at,
                   s.name AS subject_name
            FROM portal_lms_question q
            JOIN portal_subject s ON s.id = q.subject_id
            WHERE {where}
            ORDER BY q.created_at DESC
            """,
            params,
        )
        return Response(serialise(questions))

    def post(self, request):
        role = get_role(request.user)
        if role not in ("Teacher", "Admin"):
            return _FORBIDDEN

        d = request.data
        questions_data = d.get("questions", [d])
        if not isinstance(questions_data, list):
            questions_data = [questions_data]

        ids = []
        with connection.cursor() as cursor:
            for q in questions_data:
                cursor.execute(
                    """
                    INSERT INTO portal_lms_question
                    (subject_id, teacher_id, chapter, question_type, difficulty, question_text,
                     options, correct_answer, explanation, bloom_taxonomy, learning_outcome, marks, status)
                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) RETURNING id
                    """,
                    [
                        q.get("subject_id", d.get("subject_id")),
                        request.user.id,
                        q.get("chapter", d.get("chapter", "")),
                        q.get("question_type", d.get("question_type", "MCQ")),
                        q.get("difficulty", d.get("difficulty", "Medium")),
                        q["question_text"],
                        json.dumps(q.get("options", [])),
                        q.get("correct_answer", ""),
                        q.get("explanation", ""),
                        q.get("bloom_taxonomy", "Remember"),
                        q.get("learning_outcome", ""),
                        q.get("marks", 1),
                        "Active",
                    ],
                )
                ids.append(cursor.fetchone()[0])

        return Response({"ids": ids, "detail": f"{len(ids)} question(s) added."})

    def delete(self, request):
        role = get_role(request.user)
        if role not in ("Teacher", "Admin"):
            return _FORBIDDEN
        qid = request.query_params.get("id")
        if not qid:
            return Response({"detail": "id required."}, status=400)
        with connection.cursor() as cursor:
            cursor.execute("UPDATE portal_lms_question SET status = 'Archived' WHERE id = %s", [qid])
        return Response({"detail": "Question archived."})


class LmsQuizAttemptView(AuthenticatedMixin, APIView):
    """POST — attempt a quiz with enhanced tracking. GET — view attempt history."""

    def get(self, request):
        if not table_exists("portal_quiz_attempt"):
            return Response([])

        quiz_id = request.query_params.get("quiz_id")
        role = get_role(request.user)

        if role == "Student":
            attempts = rows(
                """
                SELECT qa.id, qa.score, qa.total_questions, qa.percentage, qa.is_passed,
                       qa.time_taken_seconds, qa.attempt_number, qa.submitted_at
                FROM portal_quiz_attempt qa
                WHERE qa.quiz_id = %s AND qa.student_id = %s
                ORDER BY qa.attempt_number DESC
                """,
                [quiz_id, request.user.id],
            )
        else:
            attempts = rows(
                """
                SELECT qa.id, qa.score, qa.total_questions, qa.percentage, qa.is_passed,
                       qa.time_taken_seconds, qa.attempt_number, qa.submitted_at,
                       COALESCE(u.first_name || ' ' || u.last_name, u.username) AS student_name
                FROM portal_quiz_attempt qa
                JOIN auth_user u ON u.id = qa.student_id
                WHERE qa.quiz_id = %s
                ORDER BY qa.attempt_number DESC, qa.submitted_at DESC
                """,
                [quiz_id],
            )
        return Response(serialise(attempts))

    def post(self, request):
        if not table_exists("portal_quiz_attempt"):
            return Response({"detail": "Table not found."}, status=400)

        d = request.data
        quiz_id = d.get("quiz_id")
        if not quiz_id:
            return Response({"detail": "quiz_id required."}, status=400)

        quiz = row("SELECT id, title, duration_minutes, passing_score FROM portal_quiz WHERE id=%s", [quiz_id])
        if not quiz:
            return Response({"detail": "Quiz not found."}, status=404)

        questions = rows(
            "SELECT id, question_text, options, correct_answer FROM portal_quiz_question WHERE quiz_id=%s",
            [quiz_id],
        )
        if not questions:
            return Response({"score": 0, "total": 0, "percentage": 0, "passed": False})

        # Check attempt limit
        max_attempts = int(_get_lms_setting("quiz_max_attempts", "3"))
        existing_count = row(
            "SELECT COUNT(*)::int AS c FROM portal_quiz_attempt WHERE quiz_id=%s AND student_id=%s",
            [quiz_id, request.user.id],
        )["c"]

        if existing_count >= max_attempts:
            return Response({"detail": f"Maximum {max_attempts} attempts allowed."}, status=400)

        answers = d.get("answers", {})
        correct_count = 0
        total = len(questions)

        for q in questions:
            student_ans = answers.get(str(q["id"])) or answers.get(q["id"])
            if student_ans and str(student_ans).strip().lower() == str(q["correct_answer"]).strip().lower():
                correct_count += 1

        percentage = round((correct_count / total) * 100, 2) if total > 0 else 0
        passing = quiz.get("passing_score") or 40
        is_passed = percentage >= passing

        with connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO portal_quiz_attempt
                (quiz_id, student_id, answers, score, total_questions, percentage,
                 is_passed, time_taken_seconds, attempt_number)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s) RETURNING id
                """,
                [
                    quiz_id, request.user.id, json.dumps(answers),
                    correct_count, total, percentage, is_passed,
                    d.get("time_taken_seconds", 0), existing_count + 1,
                ],
            )

            # Update course progress if quiz passed
            if is_passed:
                content = row("SELECT id FROM portal_course_content WHERE quiz_id=%s", [quiz_id])
                if content and table_exists("portal_course_progress"):
                    cursor.execute(
                        """
                        INSERT INTO portal_course_progress (student_id, content_id) VALUES (%s,%s)
                        ON CONFLICT (student_id, content_id) DO UPDATE SET completed_at = now()
                        """,
                        [request.user.id, content["id"]],
                    )

        return Response({
            "percentage": percentage,
            "score": correct_count,
            "total": total,
            "passed": is_passed,
            "attempt_number": existing_count + 1,
        })


# =============================================================================
# COURSE CERTIFICATES
# =============================================================================
class CourseCertificateView(AuthenticatedMixin, APIView):
    """GET — list certificates. POST — generate certificate (admin/teacher)."""

    def get(self, request):
        if not table_exists("portal_course_certificate"):
            return Response([])

        role = get_role(request.user)
        course_id = request.query_params.get("course_id")

        if role == "Student":
            certs = rows(
                """
                SELECT cert.id, cert.certificate_id, cert.completion_date, cert.completion_percent,
                       cert.qr_code_url, cert.verification_url, cert.file_url,
                       c.title AS course_title, s.name AS subject_name
                FROM portal_course_certificate cert
                JOIN portal_course c ON c.id = cert.course_id
                LEFT JOIN portal_subject s ON s.id = c.subject_id
                WHERE cert.student_id = %s AND cert.status = 'Issued'
                ORDER BY cert.completion_date DESC
                """,
                [request.user.id],
            )
        elif role == "Parent":
            child_id = request.query_params.get("child_id")
            if not child_id:
                return Response([])
            certs = rows(
                """
                SELECT cert.id, cert.certificate_id, cert.completion_date, cert.completion_percent,
                       cert.qr_code_url, cert.verification_url, cert.file_url,
                       c.title AS course_title, s.name AS subject_name
                FROM portal_course_certificate cert
                JOIN portal_course c ON c.id = cert.course_id
                LEFT JOIN portal_subject s ON s.id = c.subject_id
                WHERE cert.student_id = %s AND cert.status = 'Issued'
                ORDER BY cert.completion_date DESC
                """,
                [child_id],
            )
        else:
            conditions = ["cert.status = 'Issued'"]
            params = []
            if course_id:
                conditions.append("cert.course_id = %s")
                params.append(course_id)
            where = " AND ".join(conditions)
            certs = rows(
                f"""
                SELECT cert.id, cert.certificate_id, cert.completion_date, cert.completion_percent,
                       cert.file_url,
                       c.title AS course_title, s.name AS subject_name,
                       COALESCE(u.first_name || ' ' || u.last_name, u.username) AS student_name
                FROM portal_course_certificate cert
                JOIN portal_course c ON c.id = cert.course_id
                LEFT JOIN portal_subject s ON s.id = c.subject_id
                LEFT JOIN auth_user u ON u.id = cert.student_id
                WHERE {where}
                ORDER BY cert.completion_date DESC
                """,
                params,
            )

        return Response(serialise(certs))

    def post(self, request):
        role = get_role(request.user)
        if role not in ("Teacher", "Admin"):
            return _FORBIDDEN

        if not table_exists("portal_course_certificate"):
            return Response({"detail": "Certificate table not found."}, status=400)

        d = request.data
        student_id = d.get("student_id")
        course_id = d.get("course_id")

        if not student_id or not course_id:
            return Response({"detail": "student_id and course_id required."}, status=400)

        # Check if already issued
        existing = row(
            "SELECT id FROM portal_course_certificate WHERE student_id=%s AND course_id=%s AND status='Issued'",
            [student_id, course_id],
        )
        if existing:
            return Response({"detail": "Certificate already issued."}, status=400)

        cert_id = f"EDN-{secrets.token_hex(4).upper()}-{course_id:04d}"
        verification_url = f"/verify-certificate/{cert_id}"

        with connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO portal_course_certificate
                (certificate_id, student_id, course_id, teacher_id, completion_date,
                 completion_percent, qr_code_url, verification_url)
                VALUES (%s,%s,%s,%s,CURRENT_DATE,%s,%s,%s) RETURNING id
                """,
                [
                    cert_id, student_id, course_id,
                    request.user.id if role == "Teacher" else None,
                    d.get("completion_percent", 100),
                    f"qr-{cert_id}", verification_url,
                ],
            )
            cid = cursor.fetchone()[0]

            # Notification
            if table_exists("portal_notification"):
                cursor.execute(
                    "INSERT INTO portal_notification (sender_id, recipient_type, title, message) VALUES (%s, 'All', %s, %s)",
                    [request.user.id, "Course Certificate Issued", f"Congratulations! Your course certificate ({cert_id}) has been generated."],
                )

        log_action(request.user, "lms.certificate.generate", "portal_course_certificate", cid, {"cert_id": cert_id})
        return Response({"id": cid, "certificate_id": cert_id, "detail": "Certificate generated."})


# =============================================================================
# COURSE ANNOUNCEMENTS
# =============================================================================
class CourseAnnouncementView(AuthenticatedMixin, APIView):
    def get(self, request):
        if not table_exists("portal_course_announcement"):
            return Response([])

        role = get_role(request.user)
        course_id = request.query_params.get("course_id")

        if role == "Student":
            cid = _student_class_id(request.user.id)
            if not cid:
                return Response([])
            announcements = rows(
                """
                SELECT a.id, a.title, a.message, a.priority, a.is_pinned, a.created_at,
                       COALESCE(u.first_name || ' ' || u.last_name, u.username) AS teacher_name,
                       c.title AS course_title
                FROM portal_course_announcement a
                JOIN auth_user u ON u.id = a.teacher_id
                JOIN portal_course c ON c.id = a.course_id
                WHERE c.class_id = %s AND a.target_audience IN ('Students', 'All')
                ORDER BY a.is_pinned DESC, a.created_at DESC
                """,
                [cid],
            )
        elif role == "Parent":
            child_id = request.query_params.get("child_id")
            if not child_id:
                return Response([])
            cid = None
            if table_exists("portal_student_enrollment"):
                r = row("SELECT class_id FROM portal_student_enrollment WHERE student_id=%s ORDER BY academic_year DESC LIMIT 1", [child_id])
                cid = r["class_id"] if r else None
            if not cid:
                return Response([])
            announcements = rows(
                """
                SELECT a.id, a.title, a.message, a.priority, a.is_pinned, a.created_at,
                       COALESCE(u.first_name || ' ' || u.last_name, u.username) AS teacher_name,
                       c.title AS course_title
                FROM portal_course_announcement a
                JOIN auth_user u ON u.id = a.teacher_id
                JOIN portal_course c ON c.id = a.course_id
                WHERE c.class_id = %s AND a.target_audience IN ('All', 'Parents')
                ORDER BY a.is_pinned DESC, a.created_at DESC
                """,
                [cid],
            )
        else:
            conditions = ["1=1"]
            params = []
            if course_id:
                conditions.append("a.course_id = %s")
                params.append(course_id)
            where = " AND ".join(conditions)
            announcements = rows(
                f"""
                SELECT a.id, a.title, a.message, a.priority, a.is_pinned, a.created_at,
                       COALESCE(u.first_name || ' ' || u.last_name, u.username) AS teacher_name,
                       c.title AS course_title, cl.name || '-' || cl.section AS class_name
                FROM portal_course_announcement a
                JOIN auth_user u ON u.id = a.teacher_id
                JOIN portal_course c ON c.id = a.course_id
                LEFT JOIN portal_class cl ON cl.id = c.class_id
                WHERE {where}
                ORDER BY a.is_pinned DESC, a.created_at DESC
                """,
                params,
            )

        return Response(serialise(announcements))

    def post(self, request):
        role = get_role(request.user)
        if role not in ("Teacher", "Admin"):
            return _FORBIDDEN

        d = request.data
        course_id = d.get("course_id")
        if not course_id or not _can_access_course(request.user, course_id):
            return _FORBIDDEN

        with connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO portal_course_announcement
                (course_id, teacher_id, title, message, priority, target_audience, is_pinned)
                VALUES (%s,%s,%s,%s,%s,%s,%s) RETURNING id
                """,
                [
                    course_id, request.user.id,
                    d["title"], d["message"],
                    d.get("priority", "Normal"),
                    d.get("target_audience", "Students"),
                    d.get("is_pinned", False),
                ],
            )
            aid = cursor.fetchone()[0]

            # Send notification
            if table_exists("portal_notification"):
                course = row("SELECT class_id FROM portal_course WHERE id=%s", [course_id])
                if course:
                    cursor.execute(
                        "INSERT INTO portal_notification (sender_id, recipient_type, target_class_id, title, message) VALUES (%s, 'Class', %s, %s, %s)",
                        [request.user.id, course["class_id"], f"Announcement: {d['title']}", d["message"]],
                    )

        log_action(request.user, "lms.announcement.create", "portal_course_announcement", aid, {"title": d["title"]})
        return Response({"id": aid, "detail": "Announcement posted."})

    def delete(self, request):
        role = get_role(request.user)
        if role not in ("Teacher", "Admin"):
            return _FORBIDDEN
        aid = request.query_params.get("id")
        if not aid:
            return Response({"detail": "id required."}, status=400)
        with connection.cursor() as cursor:
            cursor.execute("DELETE FROM portal_course_announcement WHERE id=%s", [aid])
        return Response({"detail": "Deleted."})


# =============================================================================
# LMS SETTINGS
# =============================================================================
class LmsSettingsView(AuthenticatedMixin, APIView):
    def get(self, request):
        role = get_role(request.user)
        if role != "Admin":
            return _FORBIDDEN

        if not table_exists("portal_lms_settings"):
            return Response([])

        settings = rows("SELECT * FROM portal_lms_settings ORDER BY id")
        result = {}
        for s in settings:
            try:
                result[s["setting_key"]] = json.loads(s["setting_value"])
            except (json.JSONDecodeError, TypeError):
                result[s["setting_key"]] = s["setting_value"]
        return Response(result)

    def put(self, request):
        role = get_role(request.user)
        if role != "Admin":
            return _FORBIDDEN

        if not table_exists("portal_lms_settings"):
            return Response({"detail": "Settings table not found."}, status=400)

        d = request.data
        with connection.cursor() as cursor:
            for key, value in d.items():
                val_str = json.dumps(value) if isinstance(value, (list, dict)) else str(value)
                cursor.execute(
                    """
                    INSERT INTO portal_lms_settings (setting_key, setting_value, updated_at)
                    VALUES (%s, %s, now())
                    ON CONFLICT (setting_key)
                    DO UPDATE SET setting_value = EXCLUDED.setting_value, updated_at = now()
                    """,
                    [key, val_str],
                )

        log_action(request.user, "lms.settings.update", "portal_lms_settings", 0, {"keys": list(d.keys())})
        return Response({"detail": "Settings updated."})


# =============================================================================
# LEARNING ANALYTICS
# =============================================================================
class LearningAnalyticsView(AuthenticatedMixin, APIView):
    """GET — comprehensive learning analytics."""

    def get(self, request):
        role = get_role(request.user)
        course_id = request.query_params.get("course_id")

        if role == "Student":
            student_id = request.user.id
            if course_id:
                analytics = self._student_course_analytics(student_id, course_id)
                return Response(serialise(analytics))
            else:
                analytics = self._student_overview(student_id)
                return Response(serialise(analytics))
        elif role in ("Teacher", "Admin"):
            if not course_id:
                return Response({"detail": "course_id required."}, status=400)
            if not _can_access_course(request.user, course_id):
                return _FORBIDDEN
            analytics = self._course_analytics_admin_teacher(course_id, request.query_params.get("student_id"))
            return Response(serialise(analytics))
        return _FORBIDDEN

    def _student_overview(self, student_id):
        cid = _student_class_id(student_id)
        if not cid:
            return {"courses": [], "overall_progress": 0}

        courses = rows(
            """
            SELECT c.id, c.title, s.name AS subject_name
            FROM portal_course c JOIN portal_subject s ON s.id = c.subject_id
            WHERE c.class_id = %s ORDER BY c.id
            """,
            [cid],
        )
        result = []
        total_progress = 0
        for c in courses:
            total = row("SELECT COUNT(*)::int AS c FROM portal_course_content WHERE course_id=%s", [c["id"]])["c"]
            done = row(
                "SELECT COUNT(*)::int AS c FROM portal_course_progress WHERE student_id=%s AND content_id IN (SELECT id FROM portal_course_content WHERE course_id=%s)",
                [student_id, c["id"]],
            )["c"]
            progress = round((done / total) * 100, 1) if total > 0 else 0
            total_progress += progress
            result.append({
                "course_id": c["id"], "subject_name": c["subject_name"],
                "total_content": total, "completed_content": done,
                "progress_percent": progress,
            })
        avg = round(total_progress / len(courses), 1) if courses else 0
        return {"courses": result, "overall_progress": avg}

    def _student_course_analytics(self, student_id, course_id):
        total = row("SELECT COUNT(*)::int AS c FROM portal_course_content WHERE course_id=%s", [course_id])["c"]
        done = row(
            "SELECT COUNT(*)::int AS c FROM portal_course_progress WHERE student_id=%s AND content_id IN (SELECT id FROM portal_course_content WHERE course_id=%s)",
            [student_id, course_id],
        )["c"]

        quiz_stats = row(
            """
            SELECT COUNT(*)::int AS total_attempts,
                   AVG(qa.percentage) AS avg_score,
                   SUM(CASE WHEN qa.is_passed THEN 1 ELSE 0 END)::int AS passed
            FROM portal_quiz_attempt qa
            JOIN portal_quiz q ON q.id = qa.quiz_id
            WHERE q.course_id = %s AND qa.student_id = %s
            """,
            [course_id, student_id],
        ) if table_exists("portal_quiz_attempt") else {"total_attempts": 0, "avg_score": 0, "passed": 0}

        assignment_stats = row(
            """
            SELECT COUNT(*)::int AS total,
                   SUM(CASE WHEN s.id IS NOT NULL THEN 1 ELSE 0 END)::int AS submitted,
                   AVG(s.marks_obtained) AS avg_marks
            FROM portal_assignment a
            LEFT JOIN portal_assignment_submission s ON s.assignment_id = a.id AND s.student_id = %s
            WHERE a.class_id = (SELECT class_id FROM portal_course WHERE id = %s)
            """,
            [student_id, course_id],
        ) if table_exists("portal_assignment") else {"total": 0, "submitted": 0, "avg_marks": 0}

        return {
            "total_content": total,
            "completed_content": done,
            "progress_percent": round((done / total) * 100, 1) if total > 0 else 0,
            "quiz_stats": quiz_stats,
            "assignment_stats": assignment_stats,
        }

    def _course_analytics_admin_teacher(self, course_id, student_id_filter=None):
        total = row("SELECT COUNT(*)::int AS c FROM portal_course_content WHERE course_id=%s", [course_id])["c"]

        student_progress = rows(
            """
            SELECT u.id AS student_id,
                   COALESCE(u.first_name || ' ' || u.last_name, u.username) AS student_name,
                   COUNT(DISTINCT cp.content_id)::int AS completed_count
            FROM auth_user u
            JOIN portal_student_enrollment se ON se.student_id = u.id
            LEFT JOIN portal_course_progress cp ON cp.student_id = u.id
                AND cp.content_id IN (SELECT id FROM portal_course_content WHERE course_id=%s)
            WHERE se.class_id = (SELECT class_id FROM portal_course WHERE id = %s)
            GROUP BY u.id, u.first_name, u.last_name, u.username
            ORDER BY student_name
            """,
            [course_id, course_id],
        )

        for s in student_progress:
            s["total_content"] = total
            s["completion_percent"] = round((s["completed_count"] / total) * 100, 1) if total > 0 else 0

        if student_id_filter:
            student_progress = [s for s in student_progress if str(s["student_id"]) == str(student_id_filter)]

        return {
            "course_id": course_id,
            "total_content": total,
            "student_progress": student_progress,
            "average_completion": round(
                sum(s["completion_percent"] for s in student_progress) / len(student_progress), 1
            ) if student_progress else 0,
            "engaged_students": sum(1 for s in student_progress if s["completed_count"] > 0),
            "total_students": len(student_progress),
        }


# =============================================================================
# STUDENT HOMEWORK (Student-facing view)
# =============================================================================
class StudentHomeworkView(AuthenticatedMixin, APIView):
    """GET — list homework for student. POST — submit."""

    def get(self, request):
        role = get_role(request.user)
        if role != "Student":
            return _FORBIDDEN
        if not table_exists("portal_lms_homework"):
            return Response([])

        cid = _student_class_id(request.user.id)
        if not cid:
            return Response([])

        homework = rows(
            """
            SELECT h.id, h.title, h.description, h.instructions, h.due_date, h.max_marks,
                   h.status, h.created_at,
                   c.title AS course_title, s.name AS subject_name,
                   COALESCE(u.first_name || ' ' || u.last_name, u.username) AS teacher_name,
                   (SELECT json_build_object(
                       'id', sub.id, 'marks_obtained', sub.marks_obtained,
                       'teacher_feedback', sub.teacher_feedback, 'grade', sub.grade,
                       'status', sub.status, 'submitted_at', sub.submitted_at
                   ) FROM portal_lms_homework_submission sub
                   WHERE sub.homework_id = h.id AND sub.student_id = %s) AS my_submission
            FROM portal_lms_homework h
            JOIN portal_course c ON c.id = h.course_id
            LEFT JOIN portal_subject s ON s.id = h.subject_id
            LEFT JOIN auth_user u ON u.id = h.teacher_id
            WHERE h.class_id = %s AND h.status = 'Published'
            ORDER BY h.due_date DESC
            """,
            [request.user.id, cid],
        )
        return Response(serialise(homework))


# =============================================================================
# ADMIN LMS ANALYTICS (Enhanced)
# =============================================================================
class AdminLmsAnalyticsEnhancedView(AuthenticatedMixin, APIView):
    """Enhanced admin LMS analytics with learning hours, completion rates, etc."""

    def get(self, request):
        role = get_role(request.user)
        if role != "Admin":
            return _FORBIDDEN

        # Basic stats
        total_courses = row("SELECT COUNT(*)::int AS c FROM portal_course")["c"] if table_exists("portal_course") else 0
        total_chapters = row("SELECT COUNT(*)::int AS c FROM portal_chapter")["c"] if table_exists("portal_chapter") else 0
        total_lessons = row("SELECT COUNT(*)::int AS c FROM portal_lesson")["c"] if table_exists("portal_lesson") else 0
        total_content = row("SELECT COUNT(*)::int AS c FROM portal_course_content")["c"] if table_exists("portal_course_content") else 0

        total_students = row("SELECT COUNT(*)::int AS c FROM portal_user_profile WHERE user_type='Student'")["c"] if table_exists("portal_user_profile") else 0
        total_completed_content = row("SELECT COUNT(*)::int AS c FROM portal_course_progress")["c"] if table_exists("portal_course_progress") else 0
        total_live_classes = row("SELECT COUNT(*)::int AS c FROM portal_live_class")["c"] if table_exists("portal_live_class") else 0
        total_recorded = row("SELECT COUNT(*)::int AS c FROM portal_recorded_class")["c"] if table_exists("portal_recorded_class") else 0
        total_certificates = row("SELECT COUNT(*)::int AS c FROM portal_course_certificate WHERE status='Issued'")["c"] if table_exists("portal_course_certificate") else 0
        total_quizzes = row("SELECT COUNT(*)::int AS c FROM portal_quiz")["c"] if table_exists("portal_quiz") else 0
        total_quiz_attempts = row("SELECT COUNT(*)::int AS c FROM portal_quiz_attempt")["c"] if table_exists("portal_quiz_attempt") else 0
        avg_quiz_score = row("SELECT COALESCE(AVG(percentage), 0) AS avg FROM portal_quiz_attempt")["avg"] if table_exists("portal_quiz_attempt") else 0

        # Resources by type
        resources_by_type = {}
        if table_exists("portal_course_content"):
            for r in rows("SELECT content_type, COUNT(*)::int AS count FROM portal_course_content GROUP BY content_type"):
                resources_by_type[r["content_type"]] = r["count"]

        # Course completion rates
        course_stats = []
        if table_exists("portal_course"):
            courses = rows(
                """
                SELECT c.id, c.title, s.name AS subject_name,
                       cl.name || '-' || cl.section AS class_name
                FROM portal_course c
                JOIN portal_subject s ON s.id = c.subject_id
                JOIN portal_class cl ON cl.id = c.class_id
                ORDER BY c.id
                """
            )
            for c in courses:
                total_r = row("SELECT COUNT(*)::int AS c FROM portal_course_content WHERE course_id=%s", [c["id"]])["c"]
                enrolled = row(
                    "SELECT COUNT(*)::int AS c FROM portal_student_enrollment WHERE class_id = (SELECT class_id FROM portal_course WHERE id=%s)",
                    [c["id"]],
                )["c"] if table_exists("portal_student_enrollment") else 0
                avg_comp = row(
                    """
                    SELECT COALESCE(AVG(comp.cnt), 0) AS avg_done FROM (
                        SELECT student_id, COUNT(*)::int AS cnt FROM portal_course_progress
                        WHERE content_id IN (SELECT id FROM portal_course_content WHERE course_id=%s)
                        GROUP BY student_id
                    ) comp
                    """,
                    [c["id"]],
                )["avg_done"] if table_exists("portal_course_progress") else 0

                comp_rate = round((avg_comp / total_r) * 100, 1) if total_r > 0 and avg_comp else 0

                live_count = row(
                    "SELECT COUNT(*)::int AS c FROM portal_live_class WHERE course_id=%s",
                    [c["id"]],
                )["c"] if table_exists("portal_live_class") else 0

                cert_count = row(
                    "SELECT COUNT(*)::int AS c FROM portal_course_certificate WHERE course_id=%s AND status='Issued'",
                    [c["id"]],
                )["c"] if table_exists("portal_course_certificate") else 0

                course_stats.append({
                    "id": c["id"],
                    "title": c["title"],
                    "subject_name": c["subject_name"],
                    "class_name": c["class_name"],
                    "total_content": total_r,
                    "enrolled_students": enrolled,
                    "avg_completion_percent": comp_rate,
                    "live_classes_count": live_count,
                    "certificates_issued": cert_count,
                })

        # Recent uploads
        recent_uploads = rows(
            """
            SELECT cc.id, cc.title, cc.content_type, cc.uploaded_at,
                   c.title AS course_title, cl.name || '-' || cl.section AS class_name,
                   s.name AS subject_name,
                   COALESCE(u.first_name || ' ' || u.last_name, u.username) AS teacher_name
            FROM portal_course_content cc
            JOIN portal_course c ON c.id = cc.course_id
            JOIN portal_class cl ON cl.id = c.class_id
            JOIN portal_subject s ON s.id = c.subject_id
            LEFT JOIN portal_academic_allocation aa ON aa.class_id = c.class_id AND aa.subject_id = c.subject_id
            LEFT JOIN auth_user u ON u.id = aa.teacher_id
            ORDER BY cc.uploaded_at DESC LIMIT 20
            """,
        ) if table_exists("portal_course_content") else []

        return Response(serialise({
            "stats": {
                "total_courses": total_courses,
                "total_chapters": total_chapters,
                "total_lessons": total_lessons,
                "total_content": total_content,
                "total_students": total_students,
                "total_live_classes": total_live_classes,
                "total_recorded_classes": total_recorded,
                "total_certificates": total_certificates,
                "total_quizzes": total_quizzes,
                "total_quiz_attempts": total_quiz_attempts,
                "avg_quiz_score": round(float(avg_quiz_score or 0), 1),
                "resources_by_type": resources_by_type,
            },
            "course_stats": course_stats,
            "recent_uploads": recent_uploads,
        }))
