import json
from datetime import date, datetime, time as dt_time

from django.db import connection, transaction
from django.utils.crypto import get_random_string
from rest_framework.response import Response
from rest_framework.views import APIView

from .admin_views import AdminMixin
from .roles import log_action
from .views import row, rows, serialise, table_exists


# ---------------------------------------------------------------------------
# 1. Exam Type Management
# ---------------------------------------------------------------------------
class ExamTypeView(AdminMixin, APIView):
    """GET /admin-portal/exam-types/  — list all exam types
    POST /admin-portal/exam-types/  — create a new exam type"""

    def get(self, request):
        if not table_exists("portal_exam_type"):
            return Response([])
        active_only = request.query_params.get("active")
        sql = "SELECT * FROM portal_exam_type"
        params = []
        if active_only is not None and active_only.lower() in ("1", "true", "yes"):
            sql += " WHERE is_active = true"
        sql += " ORDER BY sort_order ASC, id ASC"
        return Response(serialise(rows(sql, params)))

    def post(self, request):
        if not table_exists("portal_exam_type"):
            return Response({"detail": "Exam type table not found. Apply the examination SQL extension."}, status=400)
        d = request.data
        name = (d.get("name") or "").strip()
        if not name:
            return Response({"detail": "name is required."}, status=400)
        description = d.get("description", "")
        sort_order = d.get("sort_order", 0)
        is_active = d.get("is_active", True)
        with connection.cursor() as cursor:
            cursor.execute(
                "INSERT INTO portal_exam_type (name, description, sort_order, is_active) "
                "VALUES (%s,%s,%s,%s) RETURNING id",
                [name, description, sort_order, is_active],
            )
            new_id = cursor.fetchone()[0]
        log_action(request.user, "exam_type.create", "portal_exam_type", new_id, {"name": name})
        return Response({"id": new_id, "detail": "Exam type created."}, status=201)


# ---------------------------------------------------------------------------
# 2. Exam Subject Configuration
# ---------------------------------------------------------------------------
class ExamSubjectConfigView(AdminMixin, APIView):
    """Manage subjects assigned to an exam schedule.
    GET    ?exam_schedule_id= — list subjects for an exam
    POST   — assign a subject to an exam
    PUT    — update a subject config (body must include id)
    DELETE ?id= — remove a subject from an exam"""

    def get(self, request):
        if not table_exists("portal_exam_subject"):
            return Response([])
        exam_id = request.query_params.get("exam_schedule_id")
        sql = """
            SELECT es.id, es.exam_schedule_id, es.subject_id, es.exam_date, es.start_time,
                   es.duration_minutes, es.max_marks, es.passing_marks,
                   s.name AS subject_name
            FROM portal_exam_subject es
            JOIN portal_subject s ON s.id = es.subject_id
        """
        params = []
        if exam_id:
            sql += " WHERE es.exam_schedule_id = %s"
            params.append(exam_id)
        sql += " ORDER BY es.exam_date NULLS LAST, es.start_time NULLS LAST"
        return Response(serialise(rows(sql, params)))

    def post(self, request):
        if not table_exists("portal_exam_subject"):
            return Response({"detail": "Exam subject table not found."}, status=400)
        d = request.data
        sched_id = d.get("exam_schedule_id")
        subject_id = d.get("subject_id")
        if not sched_id or not subject_id:
            return Response({"detail": "exam_schedule_id and subject_id are required."}, status=400)
        # Verify schedule exists
        sched = row("SELECT id FROM portal_exam_schedule WHERE id=%s", [sched_id])
        if not sched:
            return Response({"detail": "Exam schedule not found."}, status=404)
        with connection.cursor() as cursor:
            cursor.execute(
                "INSERT INTO portal_exam_subject (exam_schedule_id, subject_id, exam_date, start_time, "
                "duration_minutes, max_marks, passing_marks) VALUES (%s,%s,%s,%s,%s,%s,%s) "
                "ON CONFLICT (exam_schedule_id, subject_id) DO UPDATE SET "
                "exam_date=EXCLUDED.exam_date, start_time=EXCLUDED.start_time, "
                "duration_minutes=EXCLUDED.duration_minutes, max_marks=EXCLUDED.max_marks, "
                "passing_marks=EXCLUDED.passing_marks "
                "RETURNING id",
                [sched_id, subject_id, d.get("exam_date"), d.get("start_time"),
                 d.get("duration_minutes", 180), d.get("max_marks", 100), d.get("passing_marks", 35)],
            )
            new_id = cursor.fetchone()[0]
        log_action(request.user, "exam_subject.upsert", "portal_exam_subject", new_id,
                   {"exam_schedule_id": sched_id, "subject_id": subject_id})
        return Response({"id": new_id, "detail": "Subject assigned to exam."}, status=201)

    def put(self, request):
        if not table_exists("portal_exam_subject"):
            return Response({"detail": "Exam subject table not found."}, status=400)
        d = request.data
        rec_id = d.get("id")
        if not rec_id:
            return Response({"detail": "id is required."}, status=400)
        existing = row("SELECT id FROM portal_exam_subject WHERE id=%s", [rec_id])
        if not existing:
            return Response({"detail": "Record not found."}, status=404)
        fields = []
        vals = []
        for col in ("exam_date", "start_time", "duration_minutes", "max_marks", "passing_marks"):
            if col in d:
                fields.append(f"{col} = %s")
                vals.append(d[col])
        if not fields:
            return Response({"detail": "No fields to update."}, status=400)
        vals.append(rec_id)
        with connection.cursor() as cursor:
            cursor.execute(f"UPDATE portal_exam_subject SET {', '.join(fields)} WHERE id = %s", vals)
        log_action(request.user, "exam_subject.update", "portal_exam_subject", rec_id, d)
        return Response({"detail": "Updated."})

    def delete(self, request):
        if not table_exists("portal_exam_subject"):
            return Response({"detail": "Exam subject table not found."}, status=400)
        rec_id = request.query_params.get("id")
        if not rec_id:
            return Response({"detail": "id is required."}, status=400)
        with connection.cursor() as cursor:
            cursor.execute("DELETE FROM portal_exam_subject WHERE id=%s RETURNING id", [rec_id])
            deleted = cursor.fetchone()
        if not deleted:
            return Response({"detail": "Not found."}, status=404)
        log_action(request.user, "exam_subject.delete", "portal_exam_subject", rec_id, {})
        return Response({"detail": "Deleted."})


# ---------------------------------------------------------------------------
# 3. Seating Arrangement
# ---------------------------------------------------------------------------
class SeatingArrangementView(AdminMixin, APIView):
    """Manage seating for an exam.
    GET    ?exam_schedule_id= — list seating
    POST   {exam_schedule_id, room_name, ?student_ids} — auto-generate or assign
    DELETE ?exam_schedule_id= — clear all seating for an exam"""

    def get(self, request):
        if not table_exists("portal_seating_arrangement"):
            return Response([])
        exam_id = request.query_params.get("exam_schedule_id")
        sql = """
            SELECT sa.id, sa.exam_schedule_id, sa.student_id, sa.room_name, sa.seat_number,
                   COALESCE(u.first_name || ' ' || u.last_name, u.username) AS student_name
            FROM portal_seating_arrangement sa
            JOIN auth_user u ON u.id = sa.student_id
        """
        params = []
        if exam_id:
            sql += " WHERE sa.exam_schedule_id = %s"
            params.append(exam_id)
        sql += " ORDER BY sa.room_name, sa.seat_number"
        return Response(serialise(rows(sql, params)))

    def post(self, request):
        if not table_exists("portal_seating_arrangement"):
            return Response({"detail": "Seating arrangement table not found."}, status=400)
        d = request.data
        exam_id = d.get("exam_schedule_id")
        room_name = (d.get("room_name") or "").strip()
        if not exam_id or not room_name:
            return Response({"detail": "exam_schedule_id and room_name are required."}, status=400)
        # Verify exam exists
        sched = row("SELECT id, class_id FROM portal_exam_schedule WHERE id=%s", [exam_id])
        if not sched:
            return Response({"detail": "Exam schedule not found."}, status=404)
        # Check for existing seating
        existing = row(
            "SELECT COUNT(*)::int AS c FROM portal_seating_arrangement WHERE exam_schedule_id=%s",
            [exam_id],
        )
        if existing and existing["c"] > 0:
            return Response({"detail": "Seating already exists for this exam. Delete first to re-generate."}, status=400)

        # Auto-generate seating for all students enrolled in the class
        student_ids = d.get("student_ids")
        if not student_ids:
            # Fetch all enrolled students for the exam's class
            if table_exists("portal_student_enrollment") and sched.get("class_id"):
                enrolled = rows(
                    "SELECT student_id FROM portal_student_enrollment WHERE class_id=%s ORDER BY student_id",
                    [sched["class_id"]],
                )
                student_ids = [e["student_id"] for e in enrolled]
        if not student_ids:
            return Response({"detail": "No students found to assign seating."}, status=400)

        # Check for student conflicts with other exams at the same time
        exam_details = row(
            "SELECT exam_date, start_time, duration_minutes FROM portal_exam_schedule WHERE id=%s",
            [exam_id],
        )
        conflict_students = []
        if exam_details and exam_details.get("exam_date") and exam_details.get("start_time"):
            for sid in student_ids:
                conflict = row(
                    """
                    SELECT sa2.exam_schedule_id
                    FROM portal_seating_arrangement sa2
                    JOIN portal_exam_schedule es2 ON es2.id = sa2.exam_schedule_id
                    WHERE sa2.student_id = %s AND sa2.exam_schedule_id != %s
                      AND es2.exam_date = %s
                      AND ((es2.start_time, es2.start_time + interval '1 minute' * es2.duration_minutes)
                           OVERLAPS (%s::time, %s::time + interval '1 minute' * %s::integer))
                    LIMIT 1
                    """,
                    [sid, exam_id, exam_details["exam_date"],
                     exam_details["start_time"], exam_details["start_time"], exam_details["duration_minutes"]],
                )
                if conflict:
                    conflict_students.append(sid)

        eligible_ids = [s for s in student_ids if s not in conflict_students]
        if not eligible_ids:
            return Response({"detail": "All students have scheduling conflicts."}, status=400)

        # Generate seat numbers: ROOM-A-001, ROOM-A-002, ...
        room_prefix = room_name.replace(" ", "-").upper()
        inserted = 0
        with connection.cursor() as cursor:
            for idx, sid in enumerate(eligible_ids, start=1):
                seat_number = f"{room_prefix}-{idx:03d}"
                try:
                    cursor.execute(
                        "INSERT INTO portal_seating_arrangement (exam_schedule_id, student_id, room_name, seat_number) "
                        "VALUES (%s,%s,%s,%s)",
                        [exam_id, sid, room_name, seat_number],
                    )
                    inserted += 1
                except Exception:
                    pass  # skip duplicates
        log_action(request.user, "seating.generate", "portal_seating_arrangement", exam_id,
                   {"room": room_name, "total": len(eligible_ids), "inserted": inserted,
                    "conflicts_skipped": len(conflict_students)})
        return Response({
            "detail": f"Seating generated for {inserted} student(s) in room '{room_name}'.",
            "inserted": inserted,
            "conflicts_skipped": len(conflict_students),
        }, status=201)

    def delete(self, request):
        if not table_exists("portal_seating_arrangement"):
            return Response({"detail": "Seating arrangement table not found."}, status=400)
        exam_id = request.query_params.get("exam_schedule_id")
        if not exam_id:
            return Response({"detail": "exam_schedule_id is required."}, status=400)
        with connection.cursor() as cursor:
            cursor.execute(
                "DELETE FROM portal_seating_arrangement WHERE exam_schedule_id=%s",
                [exam_id],
            )
            deleted_count = cursor.rowcount
        log_action(request.user, "seating.clear", "portal_seating_arrangement", exam_id,
                   {"deleted": deleted_count})
        return Response({"detail": f"Cleared {deleted_count} seating record(s)."})


# ---------------------------------------------------------------------------
# 4. Invigilator Allocation
# ---------------------------------------------------------------------------
class InvigilatorAllocationView(AdminMixin, APIView):
    """Manage invigilator assignments.
    GET    ?exam_schedule_id= — list allocations
    POST   — allocate an invigilator
    PUT    — update allocation
    DELETE ?id= — remove allocation"""

    def get(self, request):
        if not table_exists("portal_invigilator_allocation"):
            return Response([])
        exam_id = request.query_params.get("exam_schedule_id")
        sql = """
            SELECT ia.id, ia.exam_schedule_id, ia.teacher_id, ia.room_name,
                   ia.exam_date, ia.start_time, ia.end_time,
                   COALESCE(u.first_name || ' ' || u.last_name, u.username) AS teacher_name
            FROM portal_invigilator_allocation ia
            JOIN auth_user u ON u.id = ia.teacher_id
        """
        params = []
        if exam_id:
            sql += " WHERE ia.exam_schedule_id = %s"
            params.append(exam_id)
        sql += " ORDER BY ia.exam_date, ia.room_name"
        return Response(serialise(rows(sql, params)))

    def post(self, request):
        if not table_exists("portal_invigilator_allocation"):
            return Response({"detail": "Invigilator allocation table not found."}, status=400)
        d = request.data
        exam_id = d.get("exam_schedule_id")
        teacher_id = d.get("teacher_id")
        room_name = (d.get("room_name") or "").strip()
        if not exam_id or not teacher_id or not room_name:
            return Response({"detail": "exam_schedule_id, teacher_id, and room_name are required."}, status=400)
        # Verify exam and teacher exist
        sched = row("SELECT id FROM portal_exam_schedule WHERE id=%s", [exam_id])
        if not sched:
            return Response({"detail": "Exam schedule not found."}, status=404)
        teacher = row("SELECT id FROM auth_user WHERE id=%s", [teacher_id])
        if not teacher:
            return Response({"detail": "Teacher not found."}, status=404)

        # Check for time conflicts for this teacher
        exam = row(
            "SELECT exam_date, start_time, duration_minutes FROM portal_exam_schedule WHERE id=%s",
            [exam_id],
        )
        if exam and exam.get("exam_date") and exam.get("start_time"):
            conflict = row(
                """
                SELECT ia2.exam_schedule_id, ia2.room_name
                FROM portal_invigilator_allocation ia2
                JOIN portal_exam_schedule es2 ON es2.id = ia2.exam_schedule_id
                WHERE ia2.teacher_id = %s AND ia2.exam_schedule_id != %s
                  AND es2.exam_date = %s
                  AND ((es2.start_time, es2.start_time + interval '1 minute' * es2.duration_minutes)
                       OVERLAPS (%s::time, %s::time + interval '1 minute' * %s::integer))
                LIMIT 1
                """,
                [teacher_id, exam_id, exam["exam_date"],
                 exam["start_time"], exam["start_time"], exam["duration_minutes"]],
            )
            if conflict:
                return Response({
                    "detail": f"Conflict: Teacher is already allocated to exam {conflict['exam_schedule_id']} "
                              f"in room '{conflict['room_name']}' at this time."
                }, status=400)

        with connection.cursor() as cursor:
            cursor.execute(
                "INSERT INTO portal_invigilator_allocation (exam_schedule_id, teacher_id, room_name, exam_date, start_time, end_time) "
                "VALUES (%s,%s,%s,%s,%s,%s) RETURNING id",
                [exam_id, teacher_id, room_name, d.get("exam_date"), d.get("start_time"), d.get("end_time")],
            )
            new_id = cursor.fetchone()[0]
        log_action(request.user, "invigilator.allocate", "portal_invigilator_allocation", new_id,
                   {"exam_schedule_id": exam_id, "teacher_id": teacher_id, "room_name": room_name})
        return Response({"id": new_id, "detail": "Invigilator allocated."}, status=201)

    def put(self, request):
        if not table_exists("portal_invigilator_allocation"):
            return Response({"detail": "Table not found."}, status=400)
        d = request.data
        rec_id = d.get("id")
        if not rec_id:
            return Response({"detail": "id is required."}, status=400)
        existing = row("SELECT id FROM portal_invigilator_allocation WHERE id=%s", [rec_id])
        if not existing:
            return Response({"detail": "Allocation not found."}, status=404)
        fields = []
        vals = []
        for col in ("room_name", "exam_date", "start_time", "end_time", "teacher_id"):
            if col in d:
                fields.append(f"{col} = %s")
                vals.append(d[col])
        if not fields:
            return Response({"detail": "No fields to update."}, status=400)
        vals.append(rec_id)
        with connection.cursor() as cursor:
            cursor.execute(f"UPDATE portal_invigilator_allocation SET {', '.join(fields)} WHERE id = %s", vals)
        log_action(request.user, "invigilator.update", "portal_invigilator_allocation", rec_id, d)
        return Response({"detail": "Updated."})

    def delete(self, request):
        if not table_exists("portal_invigilator_allocation"):
            return Response({"detail": "Table not found."}, status=400)
        rec_id = request.query_params.get("id")
        if not rec_id:
            return Response({"detail": "id is required."}, status=400)
        with connection.cursor() as cursor:
            cursor.execute("DELETE FROM portal_invigilator_allocation WHERE id=%s RETURNING id", [rec_id])
            deleted = cursor.fetchone()
        if not deleted:
            return Response({"detail": "Not found."}, status=404)
        log_action(request.user, "invigilator.delete", "portal_invigilator_allocation", rec_id, {})
        return Response({"detail": "Deleted."})


# ---------------------------------------------------------------------------
# 5. Hall Ticket Generation
# ---------------------------------------------------------------------------
class HallTicketGenerationView(AdminMixin, APIView):
    """POST to generate hall tickets for all eligible students for an exam.
    Checks fee clearance and attendance against portal_hall_ticket_config."""

    def get(self, request):
        if not table_exists("portal_hall_ticket"):
            return Response([])
        exam_id = request.query_params.get("exam_schedule_id")
        sql = """
            SELECT ht.id, ht.student_id, ht.exam_schedule_id, ht.ticket_number,
                   ht.is_verified, ht.generated_at, ht.downloaded_at,
                   ht.fee_cleared, ht.attendance_ok,
                   COALESCE(u.first_name || ' ' || u.last_name, u.username) AS student_name,
                   e.exam_name, e.exam_date
            FROM portal_hall_ticket ht
            JOIN auth_user u ON u.id = ht.student_id
            JOIN portal_exam_schedule e ON e.id = ht.exam_schedule_id
        """
        params = []
        if exam_id:
            sql += " WHERE ht.exam_schedule_id = %s"
            params.append(exam_id)
        sql += " ORDER BY ht.generated_at DESC"
        return Response(serialise(rows(sql, params)))

    def post(self, request):
        if not table_exists("portal_hall_ticket"):
            return Response({"detail": "Hall ticket table not found."}, status=400)
        d = request.data
        exam_id = d.get("exam_schedule_id")
        if not exam_id:
            return Response({"detail": "exam_schedule_id is required."}, status=400)

        # Get exam details
        sched = row("SELECT id, class_id, exam_name, exam_date FROM portal_exam_schedule WHERE id=%s", [exam_id])
        if not sched:
            return Response({"detail": "Exam schedule not found."}, status=404)

        # Get hall ticket config
        config = row(
            "SELECT * FROM portal_hall_ticket_config ORDER BY id DESC LIMIT 1"
        ) if table_exists("portal_hall_ticket_config") else None
        require_fee = config["require_fee_clearance"] if config else True
        require_attendance = config["require_min_attendance"] if config else True
        min_attendance = float(config["min_attendance_percent"]) if config else 75.0

        # Get all enrolled students for this class
        enrolled = []
        if table_exists("portal_student_enrollment") and sched.get("class_id"):
            enrolled = rows(
                "SELECT student_id FROM portal_student_enrollment WHERE class_id=%s ORDER BY student_id",
                [sched["class_id"]],
            )

        if not enrolled:
            return Response({"detail": "No students enrolled in this class."}, status=400)

        generated = 0
        skipped_fee = 0
        skipped_attendance = 0
        already_exists = 0

        with connection.cursor() as cursor:
            for e in enrolled:
                sid = e["student_id"]

                # Check if hall ticket already exists
                existing_ht = row(
                    "SELECT id FROM portal_hall_ticket WHERE student_id=%s AND exam_schedule_id=%s",
                    [sid, exam_id],
                )
                if existing_ht:
                    already_exists += 1
                    continue

                fee_ok = True
                att_ok = True

                # Fee clearance check
                if require_fee and table_exists("portal_payment") and table_exists("portal_fee_structure"):
                    unpaid = row(
                        """
                        SELECT COUNT(*)::int AS c FROM portal_fee_structure fs
                        WHERE fs.class_id = %s AND NOT EXISTS (
                            SELECT 1 FROM portal_payment p
                            WHERE p.fee_structure_id = fs.id AND p.student_id = %s AND p.status = 'Success'
                        )
                        """,
                        [sched["class_id"], sid],
                    )
                    if unpaid and unpaid["c"] > 0:
                        fee_ok = False
                        skipped_fee += 1

                # Attendance check
                if require_attendance and table_exists("portal_attendance"):
                    att_stats = row(
                        """
                        SELECT COUNT(*)::int AS total,
                               SUM(CASE WHEN status = 'Present' THEN 1 ELSE 0 END)::int AS present
                        FROM portal_attendance WHERE student_id = %s
                        """,
                        [sid],
                    )
                    if att_stats and att_stats["total"] and att_stats["total"] > 0:
                        actual_pct = (att_stats["present"] or 0) * 100.0 / att_stats["total"]
                        if actual_pct < min_attendance:
                            att_ok = False
                            skipped_attendance += 1

                ticket_number = f"HT-{exam_id:04d}-{sid:06d}-{get_random_string(4).upper()}"
                try:
                    cursor.execute(
                        "INSERT INTO portal_hall_ticket "
                        "(student_id, exam_schedule_id, ticket_number, is_verified, fee_cleared, attendance_ok) "
                        "VALUES (%s,%s,%s,true,%s,%s) RETURNING id",
                        [sid, exam_id, ticket_number, fee_ok, att_ok],
                    )
                    cursor.fetchone()
                    generated += 1
                except Exception:
                    pass

        log_action(request.user, "hall_ticket.generate", "portal_hall_ticket", exam_id,
                   {"generated": generated, "skipped_fee": skipped_fee,
                    "skipped_attendance": skipped_attendance, "already_exists": already_exists})
        return Response({
            "detail": f"Generated {generated} hall ticket(s).",
            "generated": generated,
            "skipped_fee_clearance": skipped_fee,
            "skipped_attendance": skipped_attendance,
            "already_existed": already_exists,
        }, status=201)


# ---------------------------------------------------------------------------
# 6. Marks Verification
# ---------------------------------------------------------------------------
class MarksVerificationView(AdminMixin, APIView):
    """GET  ?exam_schedule_id= — list verification records
    POST — verify marks for a result"""

    def get(self, request):
        if not table_exists("portal_marks_verification"):
            return Response([])
        exam_id = request.query_params.get("exam_schedule_id")
        sql = """
            SELECT mv.id, mv.result_id, mv.verified_by, mv.verified_at, mv.is_verified, mv.remarks,
                   COALESCE(ub.first_name || ' ' || ub.last_name, ub.username) AS verified_by_name,
                   r.student_id, r.marks_obtained, r.exam_schedule_id,
                   COALESCE(us.first_name || ' ' || us.last_name, us.username) AS student_name
            FROM portal_marks_verification mv
            JOIN auth_user ub ON ub.id = mv.verified_by
            JOIN portal_result r ON r.id = mv.result_id
            JOIN auth_user us ON us.id = r.student_id
        """
        params = []
        if exam_id:
            sql += " WHERE r.exam_schedule_id = %s"
            params.append(exam_id)
        sql += " ORDER BY mv.verified_at DESC"
        return Response(serialise(rows(sql, params)))

    def post(self, request):
        if not table_exists("portal_marks_verification"):
            return Response({"detail": "Marks verification table not found."}, status=400)
        d = request.data
        result_id = d.get("result_id")
        if not result_id:
            return Response({"detail": "result_id is required."}, status=400)
        result = row("SELECT id FROM portal_result WHERE id=%s", [result_id])
        if not result:
            return Response({"detail": "Result not found."}, status=404)
        remarks = d.get("remarks", "")
        is_verified = d.get("is_verified", True)
        with connection.cursor() as cursor:
            cursor.execute(
                "INSERT INTO portal_marks_verification (result_id, verified_by, is_verified, remarks) "
                "VALUES (%s,%s,%s,%s) RETURNING id",
                [result_id, request.user.id, is_verified, remarks],
            )
            mv_id = cursor.fetchone()[0]
            # Update result verification status
            cursor.execute(
                "UPDATE portal_result SET is_verified=%s, updated_at=now() WHERE id=%s",
                [is_verified, result_id],
            )
        log_action(request.user, "marks.verify", "portal_result", result_id,
                   {"marks_verification_id": mv_id, "is_verified": is_verified})
        return Response({"id": mv_id, "detail": "Marks verified."}, status=201)


# ---------------------------------------------------------------------------
# 7. Grade Configuration
# ---------------------------------------------------------------------------
class GradeConfigView(AdminMixin, APIView):
    """GET  ?academic_year= — list grade config
    POST — create grade config
    PUT  — update grade config
    DELETE ?id= — delete grade config"""

    def get(self, request):
        if not table_exists("portal_grade_config"):
            return Response([])
        year = request.query_params.get("academic_year")
        sql = "SELECT * FROM portal_grade_config"
        params = []
        if year:
            sql += " WHERE academic_year = %s"
            params.append(year)
        sql += " ORDER BY min_percentage DESC"
        return Response(serialise(rows(sql, params)))

    def post(self, request):
        if not table_exists("portal_grade_config"):
            return Response({"detail": "Grade config table not found."}, status=400)
        d = request.data
        academic_year = d.get("academic_year", "2025-26")
        grade_letter = d.get("grade_letter")
        min_pct = d.get("min_percentage")
        max_pct = d.get("max_percentage")
        grade_points = d.get("grade_points")
        if not grade_letter or min_pct is None or max_pct is None or grade_points is None:
            return Response({"detail": "grade_letter, min_percentage, max_percentage, grade_points are required."}, status=400)
        with connection.cursor() as cursor:
            cursor.execute(
                "INSERT INTO portal_grade_config (academic_year, grade_letter, min_percentage, max_percentage, grade_points, description) "
                "VALUES (%s,%s,%s,%s,%s,%s) "
                "ON CONFLICT (academic_year, grade_letter) DO UPDATE SET "
                "min_percentage=EXCLUDED.min_percentage, max_percentage=EXCLUDED.max_percentage, "
                "grade_points=EXCLUDED.grade_points, description=EXCLUDED.description "
                "RETURNING id",
                [academic_year, grade_letter, min_pct, max_pct, grade_points, d.get("description", "")],
            )
            new_id = cursor.fetchone()[0]
        log_action(request.user, "grade_config.upsert", "portal_grade_config", new_id, d)
        return Response({"id": new_id, "detail": "Grade configuration saved."}, status=201)

    def put(self, request):
        if not table_exists("portal_grade_config"):
            return Response({"detail": "Table not found."}, status=400)
        d = request.data
        rec_id = d.get("id")
        if not rec_id:
            return Response({"detail": "id is required."}, status=400)
        existing = row("SELECT id FROM portal_grade_config WHERE id=%s", [rec_id])
        if not existing:
            return Response({"detail": "Not found."}, status=404)
        fields = []
        vals = []
        for col in ("academic_year", "grade_letter", "min_percentage", "max_percentage", "grade_points", "description"):
            if col in d:
                fields.append(f"{col} = %s")
                vals.append(d[col])
        if not fields:
            return Response({"detail": "No fields to update."}, status=400)
        vals.append(rec_id)
        with connection.cursor() as cursor:
            cursor.execute(f"UPDATE portal_grade_config SET {', '.join(fields)} WHERE id = %s", vals)
        log_action(request.user, "grade_config.update", "portal_grade_config", rec_id, d)
        return Response({"detail": "Updated."})

    def delete(self, request):
        if not table_exists("portal_grade_config"):
            return Response({"detail": "Table not found."}, status=400)
        rec_id = request.query_params.get("id")
        if not rec_id:
            return Response({"detail": "id is required."}, status=400)
        with connection.cursor() as cursor:
            cursor.execute("DELETE FROM portal_grade_config WHERE id=%s RETURNING id", [rec_id])
            deleted = cursor.fetchone()
        if not deleted:
            return Response({"detail": "Not found."}, status=404)
        log_action(request.user, "grade_config.delete", "portal_grade_config", rec_id, {})
        return Response({"detail": "Deleted."})


# ---------------------------------------------------------------------------
# 8. Result Processing
# ---------------------------------------------------------------------------
class ResultProcessingView(AdminMixin, APIView):
    """POST to process results for an exam schedule.
    Auto-compute percentage, grade_letter, grade_points for all results
    using JOIN with portal_grade_config for grade lookup."""

    def get(self, request):
        if not table_exists("portal_result"):
            return Response([])
        exam_id = request.query_params.get("exam_schedule_id")
        sql = """
            SELECT r.id, r.student_id, r.exam_schedule_id, r.marks_obtained,
                   r.grade_letter, r.grade_points, r.rank_position, r.remarks,
                   r.total_marks, r.percentage, r.pass_fail, r.is_verified,
                   COALESCE(u.first_name || ' ' || u.last_name, u.username) AS student_name,
                   e.exam_name, e.max_marks, s.name AS subject_name
            FROM portal_result r
            JOIN auth_user u ON u.id = r.student_id
            JOIN portal_exam_schedule e ON e.id = r.exam_schedule_id
            JOIN portal_subject s ON s.id = e.subject_id
        """
        params = []
        if exam_id:
            sql += " WHERE r.exam_schedule_id = %s"
            params.append(exam_id)
        sql += " ORDER BY r.marks_obtained DESC NULLS LAST"
        return Response(serialise(rows(sql, params)))

    def post(self, request):
        if not table_exists("portal_result") or not table_exists("portal_exam_schedule"):
            return Response({"detail": "Result/exam tables not found."}, status=400)
        d = request.data
        exam_id = d.get("exam_schedule_id")
        if not exam_id:
            return Response({"detail": "exam_schedule_id is required."}, status=400)
        sched = row("SELECT id, max_marks FROM portal_exam_schedule WHERE id=%s", [exam_id])
        if not sched:
            return Response({"detail": "Exam schedule not found."}, status=404)
        max_marks = float(sched["max_marks"] or 100)

        # Get academic year for grade lookup
        exam_date = row("SELECT exam_date FROM portal_exam_schedule WHERE id=%s", [exam_id])
        academic_year = "2025-26"
        if exam_date and exam_date.get("exam_date"):
            yr = exam_date["exam_date"].year
            academic_year = f"{yr}-{str(yr + 1)[-2:]}"

        # Fetch grade config for this year (if available)
        grade_config = []
        if table_exists("portal_grade_config"):
            grade_config = rows(
                "SELECT * FROM portal_grade_config WHERE academic_year = %s ORDER BY min_percentage DESC",
                [academic_year],
            )

        results = rows(
            "SELECT id, marks_obtained FROM portal_result WHERE exam_schedule_id = %s",
            [exam_id],
        )
        if not results:
            return Response({"detail": "No results found for this exam."}, status=400)

        updated = 0
        with connection.cursor() as cursor:
            for r in results:
                marks = float(r["marks_obtained"]) if r["marks_obtained"] is not None else 0
                pct = round((marks / max_marks) * 100, 2) if max_marks > 0 else 0

                # Find matching grade from config
                grade_letter = "F"
                grade_points = 0
                if grade_config:
                    for gc in grade_config:
                        if float(gc["min_percentage"]) <= pct <= float(gc["max_percentage"]):
                            grade_letter = gc["grade_letter"]
                            grade_points = float(gc["grade_points"])
                            break
                else:
                    # Fallback simple grading
                    if pct >= 90:
                        grade_letter, grade_points = "A+", 10
                    elif pct >= 80:
                        grade_letter, grade_points = "A", 9
                    elif pct >= 70:
                        grade_letter, grade_points = "B+", 8
                    elif pct >= 60:
                        grade_letter, grade_points = "B", 7
                    elif pct >= 50:
                        grade_letter, grade_points = "C+", 6
                    elif pct >= 40:
                        grade_letter, grade_points = "C", 5
                    elif pct >= 35:
                        grade_letter, grade_points = "D", 4
                    else:
                        grade_letter, grade_points = "E", 0

                total_marks = int(max_marks)
                pass_fail = "Pass" if pct >= 35 else "Fail"

                cursor.execute(
                    "UPDATE portal_result SET total_marks=%s, percentage=%s, grade_letter=%s, "
                    "grade_points=%s, pass_fail=%s, updated_at=now() WHERE id=%s",
                    [total_marks, pct, grade_letter, grade_points, pass_fail, r["id"]],
                )
                updated += 1

        # Now compute ranks
        with connection.cursor() as cursor:
            cursor.execute(
                """
                WITH ranked AS (
                    SELECT id, RANK() OVER (ORDER BY marks_obtained DESC) AS rnk
                    FROM portal_result WHERE exam_schedule_id = %s
                )
                UPDATE portal_result r SET rank_position = ranked.rnk
                FROM ranked WHERE ranked.id = r.id
                """,
                [exam_id],
            )

        log_action(request.user, "result.process", "portal_exam_schedule", exam_id,
                   {"academic_year": academic_year, "results_processed": updated})
        return Response({
            "detail": f"Processed {updated} result(s). Percentage, grade, pass/fail, and ranks computed.",
            "results_processed": updated,
        })


# ---------------------------------------------------------------------------
# 9. Exam Notification
# ---------------------------------------------------------------------------
class ExamNotificationView(AdminMixin, APIView):
    """GET  — list exam notifications
    POST — create notification
    DELETE ?id= — delete notification"""

    def get(self, request):
        if not table_exists("portal_exam_notification"):
            return Response([])
        exam_id = request.query_params.get("exam_schedule_id")
        sql = """
            SELECT en.id, en.exam_schedule_id, en.notification_type, en.title,
                   en.message, en.target_audience, en.is_sent, en.sent_at, en.created_at,
                   e.exam_name
            FROM portal_exam_notification en
            LEFT JOIN portal_exam_schedule e ON e.id = en.exam_schedule_id
        """
        params = []
        if exam_id:
            sql += " WHERE en.exam_schedule_id = %s"
            params.append(exam_id)
        sql += " ORDER BY en.created_at DESC"
        return Response(serialise(rows(sql, params)))

    def post(self, request):
        if not table_exists("portal_exam_notification"):
            return Response({"detail": "Exam notification table not found."}, status=400)
        d = request.data
        notification_type = (d.get("notification_type") or "").strip()
        title = (d.get("title") or "").strip()
        message = (d.get("message") or "").strip()
        if not notification_type or not title or not message:
            return Response({"detail": "notification_type, title, and message are required."}, status=400)
        with connection.cursor() as cursor:
            cursor.execute(
                "INSERT INTO portal_exam_notification (exam_schedule_id, notification_type, title, message, target_audience) "
                "VALUES (%s,%s,%s,%s,%s) RETURNING id",
                [d.get("exam_schedule_id"), notification_type, title, message,
                 d.get("target_audience", "all")],
            )
            new_id = cursor.fetchone()[0]
        log_action(request.user, "exam_notification.create", "portal_exam_notification", new_id, d)
        return Response({"id": new_id, "detail": "Notification created."}, status=201)

    def delete(self, request):
        if not table_exists("portal_exam_notification"):
            return Response({"detail": "Table not found."}, status=400)
        rec_id = request.query_params.get("id")
        if not rec_id:
            return Response({"detail": "id is required."}, status=400)
        with connection.cursor() as cursor:
            cursor.execute("DELETE FROM portal_exam_notification WHERE id=%s RETURNING id", [rec_id])
            deleted = cursor.fetchone()
        if not deleted:
            return Response({"detail": "Not found."}, status=404)
        log_action(request.user, "exam_notification.delete", "portal_exam_notification", rec_id, {})
        return Response({"detail": "Deleted."})


# ---------------------------------------------------------------------------
# 10. Send Exam Notification
# ---------------------------------------------------------------------------
class SendExamNotificationView(AdminMixin, APIView):
    """POST to mark a notification as sent."""

    def post(self, request, notification_id=None):
        if not table_exists("portal_exam_notification"):
            return Response({"detail": "Table not found."}, status=400)
        nid = notification_id or request.data.get("id")
        if not nid:
            return Response({"detail": "Notification id is required."}, status=400)
        existing = row("SELECT id, is_sent FROM portal_exam_notification WHERE id=%s", [nid])
        if not existing:
            return Response({"detail": "Notification not found."}, status=404)
        if existing["is_sent"]:
            return Response({"detail": "Notification already sent."}, status=400)
        with connection.cursor() as cursor:
            cursor.execute(
                "UPDATE portal_exam_notification SET is_sent = true, sent_at = now() WHERE id = %s",
                [nid],
            )
        log_action(request.user, "exam_notification.send", "portal_exam_notification", nid, {})
        return Response({"detail": "Notification marked as sent."})


# ---------------------------------------------------------------------------
# 11. Exam Audit Log
# ---------------------------------------------------------------------------
class ExamAuditLogView(AdminMixin, APIView):
    """GET ?action=&exam_schedule_id= — list audit logs"""

    def get(self, request):
        if not table_exists("portal_exam_audit"):
            return Response([])
        action_filter = request.query_params.get("action")
        exam_id = request.query_params.get("exam_schedule_id")
        sql = """
            SELECT ea.id, ea.exam_schedule_id, ea.action, ea.action_by, ea.details, ea.created_at,
                   COALESCE(u.first_name || ' ' || u.last_name, u.username) AS action_by_name,
                   e.exam_name
            FROM portal_exam_audit ea
            LEFT JOIN auth_user u ON u.id = ea.action_by
            LEFT JOIN portal_exam_schedule e ON e.id = ea.exam_schedule_id
        """
        conditions = []
        params = []
        if action_filter:
            conditions.append("ea.action = %s")
            params.append(action_filter)
        if exam_id:
            conditions.append("ea.exam_schedule_id = %s")
            params.append(exam_id)
        if conditions:
            sql += " WHERE " + " AND ".join(conditions)
        sql += " ORDER BY ea.created_at DESC LIMIT 200"
        return Response(serialise(rows(sql, params)))


# ---------------------------------------------------------------------------
# 12. Exam Reports
# ---------------------------------------------------------------------------
class ExamReportsView(AdminMixin, APIView):
    """GET ?type=&exam_schedule_id=&class_id=&exam_name=
    Supported types: schedule, marks, analysis, pass_fail, rank_list,
    grade_distribution, toppers, evaluation_status, hall_ticket"""

    def get(self, request):
        report_type = request.query_params.get("type", "schedule")
        exam_id = request.query_params.get("exam_schedule_id")
        class_id = request.query_params.get("class_id")
        exam_name = request.query_params.get("exam_name")

        if report_type == "schedule":
            return self._schedule_report(exam_id, class_id)
        elif report_type == "marks":
            return self._marks_report(exam_id)
        elif report_type == "analysis":
            return self._analysis_report(exam_id)
        elif report_type == "pass_fail":
            return self._pass_fail_report(exam_id, class_id, exam_name)
        elif report_type == "rank_list":
            return self._rank_list_report(exam_id, class_id, exam_name)
        elif report_type == "grade_distribution":
            return self._grade_distribution_report(exam_id, class_id, exam_name)
        elif report_type == "toppers":
            return self._toppers_report(exam_id, class_id, exam_name)
        elif report_type == "evaluation_status":
            return self._evaluation_status_report(exam_id)
        elif report_type == "hall_ticket":
            return self._hall_ticket_report(exam_id)
        return Response({"detail": f"Unknown report type '{report_type}'."}, status=400)

    def _schedule_report(self, exam_id, class_id):
        if not table_exists("portal_exam_schedule"):
            return Response([])
        sql = """
            SELECT e.id, e.exam_name, e.exam_type, e.exam_date, e.start_time,
                   e.duration_minutes, e.max_marks, e.status, e.room, e.is_practical, e.is_online,
                   c.name || '-' || c.section AS class_name,
                   s.name AS subject_name,
                   COALESCE(u.first_name || ' ' || u.last_name, u.username) AS teacher_name
            FROM portal_exam_schedule e
            JOIN portal_class c ON c.id = e.class_id
            JOIN portal_subject s ON s.id = e.subject_id
            LEFT JOIN auth_user u ON u.id = e.teacher_id
        """
        conditions = []
        params = []
        if exam_id:
            conditions.append("e.id = %s")
            params.append(exam_id)
        if class_id:
            conditions.append("e.class_id = %s")
            params.append(class_id)
        if conditions:
            sql += " WHERE " + " AND ".join(conditions)
        sql += " ORDER BY e.exam_date DESC"
        return Response(serialise(rows(sql, params)))

    def _marks_report(self, exam_id):
        if not exam_id or not table_exists("portal_result"):
            return Response([])
        data = rows(
            """
            SELECT r.id, r.student_id, r.marks_obtained, r.grade_letter, r.grade_points,
                   r.rank_position, r.total_marks, r.percentage, r.pass_fail,
                   COALESCE(u.first_name || ' ' || u.last_name, u.username) AS student_name,
                   e.max_marks, s.name AS subject_name
            FROM portal_result r
            JOIN auth_user u ON u.id = r.student_id
            JOIN portal_exam_schedule e ON e.id = r.exam_schedule_id
            JOIN portal_subject s ON s.id = e.subject_id
            WHERE r.exam_schedule_id = %s
            ORDER BY r.marks_obtained DESC NULLS LAST
            """,
            [exam_id],
        )
        return Response(serialise(data))

    def _analysis_report(self, exam_id):
        if not exam_id or not table_exists("portal_result"):
            return Response({})
        stats = row(
            """
            SELECT COUNT(*)::int AS total_students,
                   COALESCE(AVG(marks_obtained), 0)::numeric(7,2) AS average_marks,
                   COALESCE(MAX(marks_obtained), 0)::numeric(7,2) AS highest_marks,
                   COALESCE(MIN(marks_obtained), 0)::numeric(7,2) AS lowest_marks,
                   COALESCE(MAX(max_marks), 0)::numeric(7,2) AS max_marks,
                   SUM(CASE WHEN pass_fail = 'Pass' THEN 1 ELSE 0 END)::int AS passed,
                   SUM(CASE WHEN pass_fail = 'Fail' THEN 1 ELSE 0 END)::int AS failed
            FROM portal_result r
            JOIN portal_exam_schedule e ON e.id = r.exam_schedule_id
            WHERE r.exam_schedule_id = %s
            """,
            [exam_id],
        )
        if stats:
            total = stats["total_students"]
            if total > 0:
                stats["pass_percentage"] = round((stats["passed"] or 0) * 100.0 / total, 1)
                stats["fail_percentage"] = round((stats["failed"] or 0) * 100.0 / total, 1)
            else:
                stats["pass_percentage"] = 0
                stats["fail_percentage"] = 0
            max_m = float(stats["max_marks"]) if stats["max_marks"] else 100
            avg_m = float(stats["average_marks"]) if stats["average_marks"] else 0
            stats["average_percentage"] = round((avg_m / max_m) * 100, 1) if max_m > 0 else 0
        return Response(serialise(stats or {}))

    def _pass_fail_report(self, exam_id, class_id, exam_name):
        if not table_exists("portal_result"):
            return Response([])
        sql = """
            SELECT r.student_id, r.pass_fail, r.marks_obtained, r.grade_letter,
                   COALESCE(u.first_name || ' ' || u.last_name, u.username) AS student_name,
                   e.exam_name, e.exam_schedule_id
            FROM portal_result r
            JOIN auth_user u ON u.id = r.student_id
            JOIN portal_exam_schedule e ON e.id = r.exam_schedule_id
        """
        conditions = []
        params = []
        if exam_id:
            conditions.append("r.exam_schedule_id = %s")
            params.append(exam_id)
        if class_id:
            conditions.append("e.class_id = %s")
            params.append(class_id)
        if exam_name:
            conditions.append("e.exam_name = %s")
            params.append(exam_name)
        if conditions:
            sql += " WHERE " + " AND ".join(conditions)
        sql += " ORDER BY r.pass_fail, r.marks_obtained DESC"
        return Response(serialise(rows(sql, params)))

    def _rank_list_report(self, exam_id, class_id, exam_name):
        if not table_exists("portal_result"):
            return Response([])
        sql = """
            SELECT r.student_id, r.marks_obtained, r.rank_position, r.grade_letter,
                   COALESCE(u.first_name || ' ' || u.last_name, u.username) AS student_name,
                   se.roll_number
            FROM portal_result r
            JOIN auth_user u ON u.id = r.student_id
            JOIN portal_exam_schedule e ON e.id = r.exam_schedule_id
            LEFT JOIN portal_student_enrollment se ON se.student_id = r.student_id AND se.class_id = e.class_id
        """
        conditions = []
        params = []
        if exam_id:
            conditions.append("r.exam_schedule_id = %s")
            params.append(exam_id)
        if class_id:
            conditions.append("e.class_id = %s")
            params.append(class_id)
        if exam_name:
            conditions.append("e.exam_name = %s")
            params.append(exam_name)
        if conditions:
            sql += " WHERE " + " AND ".join(conditions)
        sql += " ORDER BY r.rank_position NULLS LAST, r.marks_obtained DESC"
        return Response(serialise(rows(sql, params)))

    def _grade_distribution_report(self, exam_id, class_id, exam_name):
        if not table_exists("portal_result"):
            return Response([])
        sql = """
            SELECT r.grade_letter, COUNT(*)::int AS student_count,
                   AVG(r.marks_obtained)::numeric(7,2) AS average_marks
            FROM portal_result r
            JOIN portal_exam_schedule e ON e.id = r.exam_schedule_id
        """
        conditions = []
        params = []
        if exam_id:
            conditions.append("r.exam_schedule_id = %s")
            params.append(exam_id)
        if class_id:
            conditions.append("e.class_id = %s")
            params.append(class_id)
        if exam_name:
            conditions.append("e.exam_name = %s")
            params.append(exam_name)
        if conditions:
            sql += " WHERE " + " AND ".join(conditions)
        sql += " GROUP BY r.grade_letter ORDER BY r.grade_letter"
        return Response(serialise(rows(sql, params)))

    def _toppers_report(self, exam_id, class_id, exam_name):
        if not table_exists("portal_result"):
            return Response([])
        sql = """
            SELECT r.student_id, r.marks_obtained, r.grade_letter, r.rank_position,
                   COALESCE(u.first_name || ' ' || u.last_name, u.username) AS student_name,
                   e.exam_name, e.exam_schedule_id
            FROM portal_result r
            JOIN auth_user u ON u.id = r.student_id
            JOIN portal_exam_schedule e ON e.id = r.exam_schedule_id
        """
        conditions = []
        params = []
        if exam_id:
            conditions.append("r.exam_schedule_id = %s")
            params.append(exam_id)
        if class_id:
            conditions.append("e.class_id = %s")
            params.append(class_id)
        if exam_name:
            conditions.append("e.exam_name = %s")
            params.append(exam_name)
        if conditions:
            sql += " WHERE " + " AND ".join(conditions)
        sql += " ORDER BY r.marks_obtained DESC LIMIT 10"
        return Response(serialise(rows(sql, params)))

    def _evaluation_status_report(self, exam_id):
        if not exam_id or not table_exists("portal_result") or not table_exists("portal_exam_schedule"):
            return Response({})
        sched = row("SELECT class_id, exam_name FROM portal_exam_schedule WHERE id=%s", [exam_id])
        if not sched:
            return Response({"detail": "Exam not found."}, status=404)
        enrolled_count = row(
            "SELECT COUNT(*)::int AS c FROM portal_student_enrollment WHERE class_id=%s",
            [sched["class_id"]],
        ) if table_exists("portal_student_enrollment") else {"c": 0}
        results_count = row(
            "SELECT COUNT(*)::int AS c FROM portal_result WHERE exam_schedule_id=%s",
            [exam_id],
        )
        verified_count = row(
            "SELECT COUNT(*)::int AS c FROM portal_result WHERE exam_schedule_id=%s AND is_verified=true",
            [exam_id],
        )
        total = enrolled_count["c"] if enrolled_count else 0
        evaluated = results_count["c"] if results_count else 0
        verified = verified_count["c"] if verified_count else 0
        return Response(serialise({
            "exam_schedule_id": exam_id,
            "exam_name": sched.get("exam_name"),
            "total_enrolled": total,
            "evaluated": evaluated,
            "pending": total - evaluated,
            "verified": verified,
            "completion_percentage": round((evaluated * 100.0 / total), 1) if total > 0 else 0,
        }))

    def _hall_ticket_report(self, exam_id):
        if not exam_id or not table_exists("portal_hall_ticket"):
            return Response([])
        data = rows(
            """
            SELECT ht.id, ht.student_id, ht.ticket_number, ht.is_verified,
                   ht.generated_at, ht.downloaded_at, ht.fee_cleared, ht.attendance_ok,
                   COALESCE(u.first_name || ' ' || u.last_name, u.username) AS student_name
            FROM portal_hall_ticket ht
            JOIN auth_user u ON u.id = ht.student_id
            WHERE ht.exam_schedule_id = %s
            ORDER BY ht.ticket_number
            """,
            [exam_id],
        )
        return Response(serialise(data))


# ---------------------------------------------------------------------------
# 13. Exam Analytics Dashboard
# ---------------------------------------------------------------------------
class ExamAnalyticsView(AdminMixin, APIView):
    """GET dashboard analytics: total exams, total students, passed, failed,
    pass_percentage, average_marks, toppers, pending evaluations."""

    def get(self, request):
        analytics = {}
        try:
            with connection.cursor() as cursor:
                # Total exams
                if table_exists("portal_exam_schedule"):
                    cursor.execute("SELECT COUNT(*)::int AS c FROM portal_exam_schedule")
                    analytics["total_exams"] = cursor.fetchone()[0]
                else:
                    analytics["total_exams"] = 0

                # Total students who have results
                if table_exists("portal_result"):
                    cursor.execute("SELECT COUNT(DISTINCT student_id)::int FROM portal_result")
                    analytics["total_students_with_results"] = cursor.fetchone()[0]

                    # Pass / fail counts
                    cursor.execute(
                        "SELECT "
                        "SUM(CASE WHEN pass_fail='Pass' THEN 1 ELSE 0 END)::int AS passed, "
                        "SUM(CASE WHEN pass_fail='Fail' THEN 1 ELSE 0 END)::int AS failed "
                        "FROM portal_result WHERE pass_fail IN ('Pass','Fail')"
                    )
                    pf = cursor.fetchone()
                    analytics["passed"] = pf[0] or 0
                    analytics["failed"] = pf[1] or 0
                    total_pf = analytics["passed"] + analytics["failed"]
                    analytics["pass_percentage"] = round((analytics["passed"] * 100.0 / total_pf), 1) if total_pf > 0 else 0

                    # Average marks
                    cursor.execute("SELECT COALESCE(AVG(marks_obtained), 0)::numeric(7,2) FROM portal_result")
                    analytics["average_marks"] = float(cursor.fetchone()[0])

                    # Top 5 toppers
                    cursor.execute(
                        """
                        SELECT r.student_id, r.marks_obtained, r.grade_letter,
                               COALESCE(u.first_name || ' ' || u.last_name, u.username) AS student_name,
                               e.exam_name
                        FROM portal_result r
                        JOIN auth_user u ON u.id = r.student_id
                        JOIN portal_exam_schedule e ON e.id = r.exam_schedule_id
                        ORDER BY r.marks_obtained DESC LIMIT 5
                        """
                    )
                    cols = [c[0] for c in cursor.description]
                    analytics["toppers"] = [dict(zip(cols, r)) for r in cursor.fetchall()]

                    # Pending evaluations: enrolled students without results
                    cursor.execute(
                        """
                        SELECT COUNT(DISTINCT se.student_id)::int AS c
                        FROM portal_student_enrollment se
                        WHERE NOT EXISTS (
                            SELECT 1 FROM portal_result r
                            JOIN portal_exam_schedule e ON e.id = r.exam_schedule_id
                            WHERE r.student_id = se.student_id AND e.class_id = se.class_id
                        )
                        """
                    )
                    analytics["pending_evaluations"] = cursor.fetchone()[0]
                else:
                    analytics["total_students_with_results"] = 0
                    analytics["passed"] = 0
                    analytics["failed"] = 0
                    analytics["pass_percentage"] = 0
                    analytics["average_marks"] = 0
                    analytics["toppers"] = []
                    analytics["pending_evaluations"] = 0

        except Exception:
            analytics = {
                "total_exams": 0,
                "total_students_with_results": 0,
                "passed": 0,
                "failed": 0,
                "pass_percentage": 0,
                "average_marks": 0,
                "toppers": [],
                "pending_evaluations": 0,
            }
        return Response(serialise(analytics))


# ---------------------------------------------------------------------------
# 14. Practical Exam
# ---------------------------------------------------------------------------
class PracticalExamView(AdminMixin, APIView):
    """GET  ?exam_schedule_id= — list practical exam records
    POST — create practical exam record
    PUT  — update practical exam record"""

    def get(self, request):
        if not table_exists("portal_exam_schedule"):
            return Response([])
        exam_id = request.query_params.get("exam_schedule_id")
        sql = """
            SELECT e.id, e.exam_name, e.exam_type, e.exam_date, e.max_marks,
                   e.internal_marks, e.practical_marks, e.status,
                   c.name || '-' || c.section AS class_name,
                   s.name AS subject_name,
                   COALESCE(u.first_name || ' ' || u.last_name, u.username) AS teacher_name
            FROM portal_exam_schedule e
            JOIN portal_class c ON c.id = e.class_id
            JOIN portal_subject s ON s.id = e.subject_id
            LEFT JOIN auth_user u ON u.id = e.teacher_id
            WHERE e.is_practical = true
        """
        params = []
        if exam_id:
            sql += " AND e.id = %s"
            params.append(exam_id)
        sql += " ORDER BY e.exam_date DESC"
        return Response(serialise(rows(sql, params)))

    def post(self, request):
        if not table_exists("portal_exam_schedule"):
            return Response({"detail": "Exam schedule table not found."}, status=400)
        d = request.data
        sched_id = d.get("exam_schedule_id")
        if not sched_id:
            return Response({"detail": "exam_schedule_id is required."}, status=400)
        sched = row("SELECT id, is_practical FROM portal_exam_schedule WHERE id=%s", [sched_id])
        if not sched:
            return Response({"detail": "Exam schedule not found."}, status=404)
        internal_marks = d.get("internal_marks", 0)
        practical_marks = d.get("practical_marks", 0)
        with connection.cursor() as cursor:
            cursor.execute(
                "UPDATE portal_exam_schedule SET is_practical=true, internal_marks=%s, practical_marks=%s, updated_at=now() WHERE id=%s",
                [internal_marks, practical_marks, sched_id],
            )
        log_action(request.user, "practical_exam.create", "portal_exam_schedule", sched_id,
                   {"internal_marks": internal_marks, "practical_marks": practical_marks})
        return Response({"detail": "Practical exam record updated."})

    def put(self, request):
        if not table_exists("portal_exam_schedule"):
            return Response({"detail": "Exam schedule table not found."}, status=400)
        d = request.data
        sched_id = d.get("exam_schedule_id") or d.get("id")
        if not sched_id:
            return Response({"detail": "exam_schedule_id is required."}, status=400)
        sched = row("SELECT id FROM portal_exam_schedule WHERE id=%s", [sched_id])
        if not sched:
            return Response({"detail": "Exam schedule not found."}, status=404)
        fields = []
        vals = []
        for col in ("internal_marks", "practical_marks", "status", "max_marks"):
            if col in d:
                fields.append(f"{col} = %s")
                vals.append(d[col])
        fields.append("is_practical = true")
        fields.append("updated_at = now()")
        if not vals:
            return Response({"detail": "No fields to update."}, status=400)
        vals.append(sched_id)
        with connection.cursor() as cursor:
            cursor.execute(f"UPDATE portal_exam_schedule SET {', '.join(fields)} WHERE id = %s", vals)
        log_action(request.user, "practical_exam.update", "portal_exam_schedule", sched_id, d)
        return Response({"detail": "Practical exam updated."})


# ---------------------------------------------------------------------------
# 15. Exam Blueprint & Pattern Management
# ---------------------------------------------------------------------------
class ExamBlueprintView(AdminMixin, APIView):
    """GET  ?exam_schedule_id= & ?subject_id= — list blueprints
    POST — create blueprint entry
    PUT  record_id — update blueprint entry
    DELETE record_id — delete blueprint entry"""

    def get(self, request):
        if not table_exists("portal_exam_blueprint"):
            return Response([])
        exam_id = request.query_params.get("exam_schedule_id")
        subject_id = request.query_params.get("subject_id")
        sql = """
            SELECT b.*, s.name AS subject_name
            FROM portal_exam_blueprint b
            LEFT JOIN portal_subject s ON s.id = b.subject_id
            WHERE 1=1
        """
        params = []
        if exam_id:
            sql += " AND b.exam_schedule_id = %s"
            params.append(exam_id)
        if subject_id:
            sql += " AND b.subject_id = %s"
            params.append(subject_id)
        sql += " ORDER BY b.id"
        return Response(serialise(rows(sql, params)))

    def post(self, request):
        if not table_exists("portal_exam_blueprint"):
            return Response({"detail": "Exam blueprint table not found."}, status=400)
        d = request.data
        required = ("exam_schedule_id", "subject_id", "question_type", "question_count",
                     "marks_per_question", "total_marks", "difficulty", "chapter")
        missing = [f for f in required if f not in d]
        if missing:
            return Response({"detail": f"Missing fields: {', '.join(missing)}"}, status=400)
        with connection.cursor() as cursor:
            cursor.execute(
                """INSERT INTO portal_exam_blueprint
                   (exam_schedule_id, subject_id, question_type, question_count,
                    marks_per_question, total_marks, difficulty, chapter, created_at, updated_at)
                   VALUES (%s,%s,%s,%s,%s,%s,%s,%s,now(),now())
                   RETURNING id""",
                [d["exam_schedule_id"], d["subject_id"], d["question_type"],
                 d["question_count"], d["marks_per_question"], d["total_marks"],
                 d["difficulty"], d["chapter"]],
            )
            bp_id = cursor.fetchone()[0]
        log_action(request.user, "blueprint.create", "portal_exam_blueprint", bp_id, d)
        return Response({"id": bp_id, "detail": "Blueprint entry created."}, status=201)

    def put(self, request):
        if not table_exists("portal_exam_blueprint"):
            return Response({"detail": "Exam blueprint table not found."}, status=400)
        d = request.data
        record_id = d.get("record_id") or d.get("id")
        if not record_id:
            return Response({"detail": "record_id is required."}, status=400)
        existing = row("SELECT id FROM portal_exam_blueprint WHERE id=%s", [record_id])
        if not existing:
            return Response({"detail": "Blueprint entry not found."}, status=404)
        fields, vals = [], []
        for col in ("subject_id", "question_type", "question_count",
                     "marks_per_question", "total_marks", "difficulty", "chapter"):
            if col in d:
                fields.append(f"{col} = %s")
                vals.append(d[col])
        fields.append("updated_at = now()")
        if not [f for f in fields if f != "updated_at = now()"]:
            return Response({"detail": "No fields to update."}, status=400)
        vals.append(record_id)
        with connection.cursor() as cursor:
            cursor.execute(f"UPDATE portal_exam_blueprint SET {', '.join(fields)} WHERE id = %s", vals)
        log_action(request.user, "blueprint.update", "portal_exam_blueprint", record_id, d)
        return Response({"detail": "Blueprint entry updated."})

    def delete(self, request):
        if not table_exists("portal_exam_blueprint"):
            return Response({"detail": "Exam blueprint table not found."}, status=400)
        record_id = request.query_params.get("record_id") or request.data.get("record_id")
        if not record_id:
            return Response({"detail": "record_id is required."}, status=400)
        existing = row("SELECT id FROM portal_exam_blueprint WHERE id=%s", [record_id])
        if not existing:
            return Response({"detail": "Blueprint entry not found."}, status=404)
        with connection.cursor() as cursor:
            cursor.execute("DELETE FROM portal_exam_blueprint WHERE id=%s", [record_id])
        log_action(request.user, "blueprint.delete", "portal_exam_blueprint", record_id)
        return Response({"detail": "Blueprint entry deleted."})


# ---------------------------------------------------------------------------
# 16. Viva Examination Management
# ---------------------------------------------------------------------------
class VivaExamView(AdminMixin, APIView):
    """GET  ?exam_schedule_id= & ?student_id= — list viva records
    POST — create viva record
    PUT  record_id — update viva record
    DELETE record_id — delete viva record"""

    def get(self, request):
        if not table_exists("portal_viva_exam"):
            return Response([])
        exam_id = request.query_params.get("exam_schedule_id")
        student_id = request.query_params.get("student_id")
        sql = """
            SELECT v.*,
                   COALESCE(st.first_name || ' ' || st.last_name, st.username) AS student_name,
                   COALESCE(ex.first_name || ' ' || ex.last_name, ex.username) AS examiner_name
            FROM portal_viva_exam v
            LEFT JOIN auth_user st ON st.id = v.student_id
            LEFT JOIN auth_user ex ON ex.id = v.examiner_id
            WHERE 1=1
        """
        params = []
        if exam_id:
            sql += " AND v.exam_schedule_id = %s"
            params.append(exam_id)
        if student_id:
            sql += " AND v.student_id = %s"
            params.append(student_id)
        sql += " ORDER BY v.viva_date DESC"
        return Response(serialise(rows(sql, params)))

    def post(self, request):
        if not table_exists("portal_viva_exam"):
            return Response({"detail": "Viva exam table not found."}, status=400)
        d = request.data
        required = ("exam_schedule_id", "student_id", "examiner_id", "viva_date",
                     "topic", "questions_asked", "marks_obtained", "max_marks", "remarks")
        missing = [f for f in required if f not in d]
        if missing:
            return Response({"detail": f"Missing fields: {', '.join(missing)}"}, status=400)
        with connection.cursor() as cursor:
            cursor.execute(
                """INSERT INTO portal_viva_exam
                   (exam_schedule_id, student_id, examiner_id, viva_date, topic,
                    questions_asked, marks_obtained, max_marks, remarks, created_at, updated_at)
                   VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,now(),now())
                   RETURNING id""",
                [d["exam_schedule_id"], d["student_id"], d["examiner_id"],
                 d["viva_date"], d["topic"], d["questions_asked"],
                 d["marks_obtained"], d["max_marks"], d["remarks"]],
            )
            viva_id = cursor.fetchone()[0]
        log_action(request.user, "viva_exam.create", "portal_viva_exam", viva_id, d)
        return Response({"id": viva_id, "detail": "Viva record created."}, status=201)

    def put(self, request):
        if not table_exists("portal_viva_exam"):
            return Response({"detail": "Viva exam table not found."}, status=400)
        d = request.data
        record_id = d.get("record_id") or d.get("id")
        if not record_id:
            return Response({"detail": "record_id is required."}, status=400)
        existing = row("SELECT id FROM portal_viva_exam WHERE id=%s", [record_id])
        if not existing:
            return Response({"detail": "Viva record not found."}, status=404)
        fields, vals = [], []
        for col in ("marks_obtained", "remarks", "questions_asked", "topic"):
            if col in d:
                fields.append(f"{col} = %s")
                vals.append(d[col])
        fields.append("updated_at = now()")
        if not [f for f in fields if f != "updated_at = now()"]:
            return Response({"detail": "No fields to update."}, status=400)
        vals.append(record_id)
        with connection.cursor() as cursor:
            cursor.execute(f"UPDATE portal_viva_exam SET {', '.join(fields)} WHERE id = %s", vals)
        log_action(request.user, "viva_exam.update", "portal_viva_exam", record_id, d)
        return Response({"detail": "Viva record updated."})

    def delete(self, request):
        if not table_exists("portal_viva_exam"):
            return Response({"detail": "Viva exam table not found."}, status=400)
        record_id = request.query_params.get("record_id") or request.data.get("record_id")
        if not record_id:
            return Response({"detail": "record_id is required."}, status=400)
        existing = row("SELECT id FROM portal_viva_exam WHERE id=%s", [record_id])
        if not existing:
            return Response({"detail": "Viva record not found."}, status=404)
        with connection.cursor() as cursor:
            cursor.execute("DELETE FROM portal_viva_exam WHERE id=%s", [record_id])
        log_action(request.user, "viva_exam.delete", "portal_viva_exam", record_id)
        return Response({"detail": "Viva record deleted."})


# ---------------------------------------------------------------------------
# 17. Student Exam Attendance Tracking
# ---------------------------------------------------------------------------
class ExamAttendanceView(AdminMixin, APIView):
    """GET  ?exam_schedule_id= — list attendance records
    POST — mark single attendance
    POST ?bulk=true — bulk mark attendance"""

    def get(self, request):
        if not table_exists("portal_exam_attendance"):
            return Response([])
        exam_id = request.query_params.get("exam_schedule_id")
        sql = """
            SELECT a.*,
                   COALESCE(u.first_name || ' ' || u.last_name, u.username) AS student_name
            FROM portal_exam_attendance a
            LEFT JOIN auth_user u ON u.id = a.student_id
            WHERE 1=1
        """
        params = []
        if exam_id:
            sql += " AND a.exam_schedule_id = %s"
            params.append(exam_id)
        sql += " ORDER BY a.id"
        return Response(serialise(rows(sql, params)))

    def post(self, request):
        if not table_exists("portal_exam_attendance"):
            return Response({"detail": "Exam attendance table not found."}, status=400)
        bulk = request.query_params.get("bulk", "").lower() == "true"
        if bulk:
            return self._bulk_create(request)
        return self._single_create(request)

    def _single_create(self, request):
        d = request.data
        required = ("exam_schedule_id", "student_id", "attendance_status")
        missing = [f for f in required if f not in d]
        if missing:
            return Response({"detail": f"Missing fields: {', '.join(missing)}"}, status=400)
        valid_statuses = ("Present", "Absent", "Medical", "Malpractice", "Late Entry")
        if d["attendance_status"] not in valid_statuses:
            return Response(
                {"detail": f"attendance_status must be one of: {', '.join(valid_statuses)}"},
                status=400,
            )
        with connection.cursor() as cursor:
            cursor.execute(
                """INSERT INTO portal_exam_attendance
                   (exam_schedule_id, student_id, attendance_status, check_in_time,
                    remarks, marked_by, created_at, updated_at)
                   VALUES (%s,%s,%s,%s,%s,%s,now(),now())
                   RETURNING id""",
                [d["exam_schedule_id"], d["student_id"], d["attendance_status"],
                 d.get("check_in_time"), d.get("remarks"), d.get("marked_by")],
            )
            att_id = cursor.fetchone()[0]
        log_action(request.user, "exam_attendance.create", "portal_exam_attendance", att_id, d)
        return Response({"id": att_id, "detail": "Attendance marked."}, status=201)

    def _bulk_create(self, request):
        records = request.data.get("records") or request.data.get("data")
        if not records or not isinstance(records, list):
            return Response({"detail": "records must be a non-empty array."}, status=400)
        exam_id = request.data.get("exam_schedule_id")
        if not exam_id:
            return Response({"detail": "exam_schedule_id is required for bulk."}, status=400)
        valid_statuses = ("Present", "Absent", "Medical", "Malpractice", "Late Entry")
        created_ids = []
        with transaction.atomic():
            with connection.cursor() as cursor:
                for rec in records:
                    sid = rec.get("student_id")
                    status_val = rec.get("attendance_status")
                    if not sid or not status_val:
                        continue
                    if status_val not in valid_statuses:
                        continue
                    cursor.execute(
                        """INSERT INTO portal_exam_attendance
                           (exam_schedule_id, student_id, attendance_status, remarks,
                            marked_by, created_at, updated_at)
                           VALUES (%s,%s,%s,%s,%s,now(),now())
                           RETURNING id""",
                        [exam_id, sid, status_val, rec.get("remarks"),
                         request.data.get("marked_by")],
                    )
                    created_ids.append(cursor.fetchone()[0])
        log_action(request.user, "exam_attendance.bulk_create", "portal_exam_attendance", None,
                   {"count": len(created_ids), "exam_schedule_id": exam_id})
        return Response({"detail": f"{len(created_ids)} attendance records created.",
                         "ids": created_ids}, status=201)


# ---------------------------------------------------------------------------
# 18. Malpractice Incident Register
# ---------------------------------------------------------------------------
class MalpracticeRegisterView(AdminMixin, APIView):
    """GET  ?exam_schedule_id= & ?status= — list malpractice incidents
    POST — report malpractice
    PUT  record_id — update incident status/action"""

    def get(self, request):
        if not table_exists("portal_malpractice_register"):
            return Response([])
        exam_id = request.query_params.get("exam_schedule_id")
        status_val = request.query_params.get("status")
        sql = """
            SELECT m.*,
                   COALESCE(st.first_name || ' ' || st.last_name, st.username) AS student_name,
                   COALESCE(rb.first_name || ' ' || rb.last_name, rb.username) AS reported_by_name
            FROM portal_malpractice_register m
            LEFT JOIN auth_user st ON st.id = m.student_id
            LEFT JOIN auth_user rb ON rb.id = m.reported_by
            WHERE 1=1
        """
        params = []
        if exam_id:
            sql += " AND m.exam_schedule_id = %s"
            params.append(exam_id)
        if status_val:
            sql += " AND m.status = %s"
            params.append(status_val)
        sql += " ORDER BY m.id DESC"
        return Response(serialise(rows(sql, params)))

    def post(self, request):
        if not table_exists("portal_malpractice_register"):
            return Response({"detail": "Malpractice register table not found."}, status=400)
        d = request.data
        required = ("exam_schedule_id", "student_id", "incident_description",
                     "evidence", "reported_by", "action_taken", "status")
        missing = [f for f in required if f not in d]
        if missing:
            return Response({"detail": f"Missing fields: {', '.join(missing)}"}, status=400)
        with connection.cursor() as cursor:
            cursor.execute(
                """INSERT INTO portal_malpractice_register
                   (exam_schedule_id, student_id, incident_description, evidence,
                    reported_by, action_taken, status, created_at, updated_at)
                   VALUES (%s,%s,%s,%s,%s,%s,%s,now(),now())
                   RETURNING id""",
                [d["exam_schedule_id"], d["student_id"], d["incident_description"],
                 d["evidence"], d["reported_by"], d["action_taken"], d["status"]],
            )
            mp_id = cursor.fetchone()[0]
        log_action(request.user, "malpractice.create", "portal_malpractice_register", mp_id, d)
        return Response({"id": mp_id, "detail": "Malpractice incident reported."}, status=201)

    def put(self, request):
        if not table_exists("portal_malpractice_register"):
            return Response({"detail": "Malpractice register table not found."}, status=400)
        d = request.data
        record_id = d.get("record_id") or d.get("id")
        if not record_id:
            return Response({"detail": "record_id is required."}, status=400)
        existing = row("SELECT id FROM portal_malpractice_register WHERE id=%s", [record_id])
        if not existing:
            return Response({"detail": "Malpractice incident not found."}, status=404)
        fields, vals = [], []
        for col in ("status", "action_taken", "incident_description", "evidence"):
            if col in d:
                fields.append(f"{col} = %s")
                vals.append(d[col])
        fields.append("updated_at = now()")
        if not [f for f in fields if f != "updated_at = now()"]:
            return Response({"detail": "No fields to update."}, status=400)
        vals.append(record_id)
        with connection.cursor() as cursor:
            cursor.execute(
                f"UPDATE portal_malpractice_register SET {', '.join(fields)} WHERE id = %s", vals
            )
        log_action(request.user, "malpractice.update", "portal_malpractice_register", record_id, d)
        return Response({"detail": "Malpractice incident updated."})


# ---------------------------------------------------------------------------
# 19. Improvement Exam Registration
# ---------------------------------------------------------------------------
class ImprovementExamView(AdminMixin, APIView):
    """GET  — list improvement registrations
    POST — register student for improvement
    PUT  record_id — update status/marks/grade after exam
    DELETE record_id — delete registration"""

    def get(self, request):
        if not table_exists("portal_improvement_exam"):
            return Response([])
        sql = """
            SELECT i.*,
                   COALESCE(u.first_name || ' ' || u.last_name, u.username) AS student_name,
                   s.name AS subject_name
            FROM portal_improvement_exam i
            LEFT JOIN auth_user u ON u.id = i.student_id
            LEFT JOIN portal_subject s ON s.id = i.subject_id
            ORDER BY i.id DESC
        """
        return Response(serialise(rows(sql)))

    def post(self, request):
        if not table_exists("portal_improvement_exam"):
            return Response({"detail": "Improvement exam table not found."}, status=400)
        d = request.data
        required = ("student_id", "subject_id", "original_result_id",
                     "new_exam_schedule_id", "is_paid")
        missing = [f for f in required if f not in d]
        if missing:
            return Response({"detail": f"Missing fields: {', '.join(missing)}"}, status=400)
        with connection.cursor() as cursor:
            cursor.execute(
                """INSERT INTO portal_improvement_exam
                   (student_id, subject_id, original_result_id, new_exam_schedule_id,
                    is_paid, created_at, updated_at)
                   VALUES (%s,%s,%s,%s,%s,now(),now())
                   RETURNING id""",
                [d["student_id"], d["subject_id"], d["original_result_id"],
                 d["new_exam_schedule_id"], d["is_paid"]],
            )
            ie_id = cursor.fetchone()[0]
        log_action(request.user, "improvement_exam.create", "portal_improvement_exam", ie_id, d)
        return Response({"id": ie_id, "detail": "Improvement exam registration created."}, status=201)

    def put(self, request):
        if not table_exists("portal_improvement_exam"):
            return Response({"detail": "Improvement exam table not found."}, status=400)
        d = request.data
        record_id = d.get("record_id") or d.get("id")
        if not record_id:
            return Response({"detail": "record_id is required."}, status=400)
        existing = row("SELECT id FROM portal_improvement_exam WHERE id=%s", [record_id])
        if not existing:
            return Response({"detail": "Improvement registration not found."}, status=404)
        fields, vals = [], []
        for col in ("status", "marks_obtained", "grade", "remarks"):
            if col in d:
                fields.append(f"{col} = %s")
                vals.append(d[col])
        fields.append("updated_at = now()")
        if not [f for f in fields if f != "updated_at = now()"]:
            return Response({"detail": "No fields to update."}, status=400)
        vals.append(record_id)
        with connection.cursor() as cursor:
            cursor.execute(
                f"UPDATE portal_improvement_exam SET {', '.join(fields)} WHERE id = %s", vals
            )
        log_action(request.user, "improvement_exam.update", "portal_improvement_exam", record_id, d)
        return Response({"detail": "Improvement registration updated."})

    def delete(self, request):
        if not table_exists("portal_improvement_exam"):
            return Response({"detail": "Improvement exam table not found."}, status=400)
        record_id = request.query_params.get("record_id") or request.data.get("record_id")
        if not record_id:
            return Response({"detail": "record_id is required."}, status=400)
        existing = row("SELECT id FROM portal_improvement_exam WHERE id=%s", [record_id])
        if not existing:
            return Response({"detail": "Improvement registration not found."}, status=404)
        with connection.cursor() as cursor:
            cursor.execute("DELETE FROM portal_improvement_exam WHERE id=%s", [record_id])
        log_action(request.user, "improvement_exam.delete", "portal_improvement_exam", record_id)
        return Response({"detail": "Improvement registration deleted."})


# ---------------------------------------------------------------------------
# 20. CGPA / GPA Aggregation
# ---------------------------------------------------------------------------
class CGPACalculationView(AdminMixin, APIView):
    """GET  ?student_id= & ?academic_year= — compute/display CGPA for a student
    POST ?class_id= & ?academic_year= — batch compute CGPA for all students in a class"""

    def get(self, request):
        if not table_exists("portal_result"):
            return Response({"detail": "Result table not found."}, status=400)
        student_id = request.query_params.get("student_id")
        academic_year = request.query_params.get("academic_year")
        if not student_id:
            return Response({"detail": "student_id is required."}, status=400)
        student = row(
            "SELECT id, COALESCE(first_name || ' ' || last_name, username) AS student_name "
            "FROM auth_user WHERE id=%s",
            [student_id],
        )
        if not student:
            return Response({"detail": "Student not found."}, status=404)
        sql = """
            SELECT r.id, r.grade_point
            FROM portal_result r
            JOIN portal_exam_schedule es ON es.id = r.exam_schedule_id
            WHERE r.student_id = %s
        """
        params = [student_id]
        if academic_year:
            sql += " AND es.academic_year = %s"
            params.append(academic_year)
        results = rows(sql, params)
        total_subjects = len(results)
        total_exams = len(set(r["exam_schedule_id"] for r in results if r.get("exam_schedule_id")))
        grade_points = [float(r["grade_point"]) for r in results
                        if r.get("grade_point") is not None]
        total_gp = sum(grade_points)
        cgpa = round(total_gp / len(grade_points), 2) if grade_points else 0
        return Response(serialise({
            "student_id": student_id,
            "student_name": student["student_name"],
            "academic_year": academic_year,
            "total_subjects": total_subjects,
            "total_exams": total_exams,
            "total_grade_points": total_gp,
            "cgpa": cgpa,
        }))

    def post(self, request):
        if not table_exists("portal_result"):
            return Response({"detail": "Result table not found."}, status=400)
        class_id = request.query_params.get("class_id") or request.data.get("class_id")
        academic_year = request.query_params.get("academic_year") or request.data.get("academic_year")
        if not class_id or not academic_year:
            return Response({"detail": "class_id and academic_year are required."}, status=400)
        students = rows(
            "SELECT id, COALESCE(first_name || ' ' || last_name, username) AS student_name "
            "FROM auth_user WHERE id IN "
            "(SELECT student_id FROM portal_student_enrollment WHERE class_id=%s)",
            [class_id],
        )
        if not students:
            return Response({"detail": "No students found for this class."}, status=404)
        updated_count = 0
        with connection.cursor() as cursor:
            for stu in students:
                cursor.execute(
                    """SELECT r.grade_point
                       FROM portal_result r
                       JOIN portal_exam_schedule es ON es.id = r.exam_schedule_id
                       WHERE r.student_id = %s AND es.academic_year = %s""",
                    [stu["id"], academic_year],
                )
                gp_rows = cursor.fetchall()
                grade_points = [float(r[0]) for r in gp_rows if r[0] is not None]
                cgpa = round(sum(grade_points) / len(grade_points), 2) if grade_points else 0
                cursor.execute(
                    """UPDATE portal_result SET cgpa = %s, updated_at = now()
                       WHERE student_id = %s AND exam_schedule_id IN (
                           SELECT id FROM portal_exam_schedule WHERE academic_year = %s
                       )""",
                    [cgpa, stu["id"], academic_year],
                )
                updated_count += 1
        log_action(request.user, "cgpa.batch_compute", "portal_result", None,
                   {"class_id": class_id, "academic_year": academic_year,
                    "students_updated": updated_count})
        return Response({"detail": f"CGPA computed for {updated_count} students.",
                         "students_updated": updated_count})
