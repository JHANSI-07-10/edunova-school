import json
from datetime import date, datetime

from django.db import connection, transaction
from rest_framework.response import Response
from rest_framework.views import APIView

from .admin_views import AdminMixin
from .roles import log_action
from .views import row, rows, serialise, table_exists


# ---------------------------------------------------------------------------
# VIEW 1: Academic Calendar CRUD
# ---------------------------------------------------------------------------
class AcademicCalendarView(AdminMixin, APIView):
    """GET /admin-portal/timetable/calendar/?academic_year=
    POST /admin-portal/timetable/calendar/"""

    def get(self, request):
        if not table_exists("portal_academic_calendar"):
            return Response([])
        academic_year = request.query_params.get("academic_year")
        sql = "SELECT * FROM portal_academic_calendar"
        params = []
        if academic_year:
            sql += " WHERE academic_year = %s"
            params.append(academic_year)
        sql += " ORDER BY start_date DESC"
        return Response(serialise(rows(sql, params)))

    def post(self, request):
        if not table_exists("portal_academic_calendar"):
            return Response({"detail": "Academic calendar table not found."}, status=503)
        d = request.data
        academic_year = d.get("academic_year")
        term_name = d.get("term_name")
        start_date = d.get("start_date")
        end_date = d.get("end_date")
        is_current = bool(d.get("is_current", False))
        description = d.get("description", "")

        if not all([academic_year, start_date, end_date]):
            return Response({"detail": "academic_year, start_date and end_date are required."}, status=400)

        if is_current:
            with connection.cursor() as cursor:
                cursor.execute("UPDATE portal_academic_calendar SET is_current = false WHERE is_current = true")

        with connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO portal_academic_calendar (academic_year, term_name, start_date, end_date, is_current, description)
                VALUES (%s, %s, %s, %s, %s, %s) RETURNING id
                """,
                [academic_year, term_name, start_date, end_date, is_current, description],
            )
            new_id = cursor.fetchone()[0]

        log_action(request.user, "academic_calendar.create", "portal_academic_calendar", new_id, d)
        return Response({"id": new_id, "detail": "Academic calendar created."}, status=201)


class AcademicCalendarDetailView(AdminMixin, APIView):
    """PUT /admin-portal/timetable/calendar/<id>/
    DELETE /admin-portal/timetable/calendar/<id>/"""

    def put(self, request, record_id):
        if not table_exists("portal_academic_calendar"):
            return Response({"detail": "Table not found."}, status=503)
        d = request.data
        allowed = ["academic_year", "term_name", "start_date", "end_date", "is_current", "description"]
        updates = {k: v for k, v in d.items() if k in allowed}
        if not updates:
            return Response({"detail": "No valid fields."}, status=400)

        if updates.get("is_current"):
            with connection.cursor() as cursor:
                cursor.execute("UPDATE portal_academic_calendar SET is_current = false WHERE is_current = true AND id != %s", [record_id])

        set_clause = ", ".join(f"{k}=%s" for k in updates)
        with connection.cursor() as cursor:
            cursor.execute(
                f"UPDATE portal_academic_calendar SET {set_clause}, updated_at=now() WHERE id=%s",
                list(updates.values()) + [record_id],
            )
        log_action(request.user, "academic_calendar.update", "portal_academic_calendar", record_id, updates)
        return Response({"detail": "Updated."})

    def delete(self, request, record_id):
        if not table_exists("portal_academic_calendar"):
            return Response({"detail": "Table not found."}, status=503)
        with connection.cursor() as cursor:
            cursor.execute("DELETE FROM portal_academic_calendar WHERE id=%s", [record_id])
        log_action(request.user, "academic_calendar.delete", "portal_academic_calendar", record_id, {})
        return Response({"detail": "Deleted."})


# ---------------------------------------------------------------------------
# VIEW 3: Calendar Events
# ---------------------------------------------------------------------------
class CalendarEventView(AdminMixin, APIView):
    """GET /admin-portal/timetable/calendar-events/?calendar_id=&event_type=
    POST /admin-portal/timetable/calendar-events/"""

    def get(self, request):
        if not table_exists("portal_calendar_event"):
            return Response([])
        calendar_id = request.query_params.get("calendar_id")
        event_type = request.query_params.get("event_type")
        sql = "SELECT * FROM portal_calendar_event"
        conditions = []
        params = []
        if calendar_id:
            conditions.append("calendar_id = %s")
            params.append(calendar_id)
        if event_type:
            conditions.append("event_type = %s")
            params.append(event_type)
        if conditions:
            sql += " WHERE " + " AND ".join(conditions)
        sql += " ORDER BY event_date DESC"
        return Response(serialise(rows(sql, params)))

    def post(self, request):
        if not table_exists("portal_calendar_event"):
            return Response({"detail": "Table not found."}, status=503)
        d = request.data
        calendar_id = d.get("calendar_id")
        event_date = d.get("event_date")
        event_name = d.get("event_name")
        event_type = d.get("event_type", "Holiday")
        is_working_day = bool(d.get("is_working_day", False))
        description = d.get("description", "")

        if not all([calendar_id, event_date, event_name]):
            return Response({"detail": "calendar_id, event_date and event_name are required."}, status=400)

        with connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO portal_calendar_event (calendar_id, event_date, event_name, event_type, is_working_day, description)
                VALUES (%s, %s, %s, %s, %s, %s) RETURNING id
                """,
                [calendar_id, event_date, event_name, event_type, is_working_day, description],
            )
            new_id = cursor.fetchone()[0]

        log_action(request.user, "calendar_event.create", "portal_calendar_event", new_id, d)
        return Response({"id": new_id, "detail": "Event created."}, status=201)


class CalendarEventDetailView(AdminMixin, APIView):
    """PUT /admin-portal/timetable/calendar-events/<id>/
    DELETE /admin-portal/timetable/calendar-events/<id>/"""

    def put(self, request, record_id):
        if not table_exists("portal_calendar_event"):
            return Response({"detail": "Table not found."}, status=503)
        d = request.data
        allowed = ["calendar_id", "event_date", "event_name", "event_type", "is_working_day", "description"]
        updates = {k: v for k, v in d.items() if k in allowed}
        if not updates:
            return Response({"detail": "No valid fields."}, status=400)
        set_clause = ", ".join(f"{k}=%s" for k in updates)
        with connection.cursor() as cursor:
            cursor.execute(
                f"UPDATE portal_calendar_event SET {set_clause} WHERE id=%s",
                list(updates.values()) + [record_id],
            )
        log_action(request.user, "calendar_event.update", "portal_calendar_event", record_id, updates)
        return Response({"detail": "Updated."})

    def delete(self, request, record_id):
        if not table_exists("portal_calendar_event"):
            return Response({"detail": "Table not found."}, status=503)
        with connection.cursor() as cursor:
            cursor.execute("DELETE FROM portal_calendar_event WHERE id=%s", [record_id])
        log_action(request.user, "calendar_event.delete", "portal_calendar_event", record_id, {})
        return Response({"detail": "Deleted."})


# ---------------------------------------------------------------------------
# VIEW 5: Working Days
# ---------------------------------------------------------------------------
class WorkingDayView(AdminMixin, APIView):
    """GET /admin-portal/timetable/working-days/?academic_year=2025-26
    POST /admin-portal/timetable/working-days/  (bulk upsert)
    PUT /admin-portal/timetable/working-days/?record_id=  (single update)"""

    ALL_DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]

    def get(self, request):
        if not table_exists("portal_working_day"):
            return Response([])
        academic_year = request.query_params.get("academic_year", "2025-26")
        existing = rows(
            "SELECT * FROM portal_working_day WHERE academic_year = %s",
            [academic_year],
        )
        existing_map = {r["day_of_week"]: r for r in existing}
        result = []
        for day in self.ALL_DAYS:
            if day in existing_map:
                result.append(existing_map[day])
            else:
                result.append({
                    "day_of_week": day,
                    "is_working": day not in ("Sunday",),
                    "is_half_day": day == "Saturday",
                    "start_time": None,
                    "end_time": None,
                })
        return Response(serialise(result))

    def post(self, request):
        if not table_exists("portal_working_day"):
            return Response({"detail": "Table not found."}, status=503)
        days = request.data.get("days", [])
        academic_year = request.data.get("academic_year", "2025-26")

        if not days:
            return Response({"detail": "days array is required."}, status=400)

        with connection.cursor() as cursor:
            for d in days:
                day_of_week = d.get("day_of_week")
                if not day_of_week:
                    continue
                is_working = bool(d.get("is_working", True))
                is_half_day = bool(d.get("is_half_day", False))
                start_time = d.get("start_time") or None
                end_time = d.get("end_time") or None
                cursor.execute(
                    """
                    INSERT INTO portal_working_day (academic_year, day_of_week, is_working, is_half_day, start_time, end_time)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    ON CONFLICT (academic_year, day_of_week) DO UPDATE SET
                        is_working = EXCLUDED.is_working,
                        is_half_day = EXCLUDED.is_half_day,
                        start_time = EXCLUDED.start_time,
                        end_time = EXCLUDED.end_time
                    """,
                    [academic_year, day_of_week, is_working, is_half_day, start_time, end_time],
                )

        log_action(request.user, "working_day.bulk_update", "portal_working_day", 0, {"academic_year": academic_year, "count": len(days)})
        return Response({"detail": f"{len(days)} working day(s) saved."})

    def put(self, request):
        if not table_exists("portal_working_day"):
            return Response({"detail": "Table not found."}, status=503)
        record_id = request.query_params.get("record_id")
        if not record_id:
            return Response({"detail": "record_id is required."}, status=400)
        d = request.data
        allowed = ["day_of_week", "is_working", "is_half_day", "start_time", "end_time", "academic_year"]
        updates = {k: v for k, v in d.items() if k in allowed}
        if not updates:
            return Response({"detail": "No valid fields."}, status=400)
        set_clause = ", ".join(f"{k}=%s" for k in updates)
        with connection.cursor() as cursor:
            cursor.execute(
                f"UPDATE portal_working_day SET {set_clause} WHERE id=%s",
                list(updates.values()) + [record_id],
            )
        log_action(request.user, "working_day.update", "portal_working_day", record_id, updates)
        return Response({"detail": "Updated."})


# ---------------------------------------------------------------------------
# VIEW 6: School Timings
# ---------------------------------------------------------------------------
class SchoolTimingView(AdminMixin, APIView):
    """GET /admin-portal/timetable/school-timings/?academic_year=&day_type=
    POST /admin-portal/timetable/school-timings/
    PUT /admin-portal/timetable/school-timings/?record_id=
    DELETE /admin-portal/timetable/school-timings/?record_id="""

    def get(self, request):
        if not table_exists("portal_school_timing"):
            return Response([])
        academic_year = request.query_params.get("academic_year")
        day_type = request.query_params.get("day_type")
        sql = "SELECT * FROM portal_school_timing"
        conditions = []
        params = []
        if academic_year:
            conditions.append("academic_year = %s")
            params.append(academic_year)
        if day_type:
            conditions.append("day_type = %s")
            params.append(day_type)
        if conditions:
            sql += " WHERE " + " AND ".join(conditions)
        sql += " ORDER BY id"
        return Response(serialise(rows(sql, params)))

    def post(self, request):
        if not table_exists("portal_school_timing"):
            return Response({"detail": "Table not found."}, status=503)
        d = request.data
        academic_year = d.get("academic_year")
        day_type = d.get("day_type")
        opening_time = d.get("opening_time")
        closing_time = d.get("closing_time")

        if not all([academic_year, day_type, opening_time, closing_time]):
            return Response({"detail": "academic_year, day_type, opening_time and closing_time are required."}, status=400)

        with connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO portal_school_timing
                    (academic_year, day_type, opening_time, closing_time,
                     assembly_time, lunch_start, lunch_end, tea_break_start, tea_break_end)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (academic_year, day_type) DO UPDATE SET
                    opening_time = EXCLUDED.opening_time,
                    closing_time = EXCLUDED.closing_time,
                    assembly_time = EXCLUDED.assembly_time,
                    lunch_start = EXCLUDED.lunch_start,
                    lunch_end = EXCLUDED.lunch_end,
                    tea_break_start = EXCLUDED.tea_break_start,
                    tea_break_end = EXCLUDED.tea_break_end
                RETURNING id
                """,
                [
                    academic_year, day_type, opening_time, closing_time,
                    d.get("assembly_time"), d.get("lunch_start"), d.get("lunch_end"),
                    d.get("tea_break_start"), d.get("tea_break_end"),
                ],
            )
            new_id = cursor.fetchone()[0]

        log_action(request.user, "school_timing.create", "portal_school_timing", new_id, d)
        return Response({"id": new_id, "detail": "School timing saved."}, status=201)

    def put(self, request):
        if not table_exists("portal_school_timing"):
            return Response({"detail": "Table not found."}, status=503)
        record_id = request.query_params.get("record_id")
        if not record_id:
            return Response({"detail": "record_id is required."}, status=400)
        d = request.data
        allowed = ["academic_year", "day_type", "opening_time", "closing_time",
                    "assembly_time", "lunch_start", "lunch_end", "tea_break_start", "tea_break_end"]
        updates = {k: v for k, v in d.items() if k in allowed}
        if not updates:
            return Response({"detail": "No valid fields."}, status=400)
        set_clause = ", ".join(f"{k}=%s" for k in updates)
        with connection.cursor() as cursor:
            cursor.execute(
                f"UPDATE portal_school_timing SET {set_clause} WHERE id=%s",
                list(updates.values()) + [record_id],
            )
        log_action(request.user, "school_timing.update", "portal_school_timing", record_id, updates)
        return Response({"detail": "Updated."})

    def delete(self, request):
        if not table_exists("portal_school_timing"):
            return Response({"detail": "Table not found."}, status=503)
        record_id = request.query_params.get("record_id")
        if not record_id:
            return Response({"detail": "record_id is required."}, status=400)
        with connection.cursor() as cursor:
            cursor.execute("DELETE FROM portal_school_timing WHERE id=%s", [record_id])
        log_action(request.user, "school_timing.delete", "portal_school_timing", record_id, {})
        return Response({"detail": "Deleted."})


# ---------------------------------------------------------------------------
# VIEW 7: Period Management
# ---------------------------------------------------------------------------
class PeriodManagementView(AdminMixin, APIView):
    """GET /admin-portal/timetable/periods/?academic_year=&day_type=
    POST /admin-portal/timetable/periods/
    PUT /admin-portal/timetable/periods/?record_id=
    DELETE /admin-portal/timetable/periods/?record_id="""

    def get(self, request):
        if not table_exists("portal_period"):
            return Response([])
        academic_year = request.query_params.get("academic_year")
        day_type = request.query_params.get("day_type")
        sql = "SELECT * FROM portal_period"
        conditions = []
        params = []
        if academic_year:
            conditions.append("academic_year = %s")
            params.append(academic_year)
        if day_type:
            conditions.append("day_type = %s")
            params.append(day_type)
        if conditions:
            sql += " WHERE " + " AND ".join(conditions)
        sql += " ORDER BY period_number"
        return Response(serialise(rows(sql, params)))

    def post(self, request):
        if not table_exists("portal_period"):
            return Response({"detail": "Table not found."}, status=503)
        d = request.data
        academic_year = d.get("academic_year")
        period_number = d.get("period_number")
        period_name = d.get("period_name")
        start_time = d.get("start_time")
        end_time = d.get("end_time")
        day_type = d.get("day_type", "FullDay")

        if not all([academic_year, period_number, start_time, end_time]):
            return Response({"detail": "academic_year, period_number, start_time and end_time are required."}, status=400)

        is_break = bool(d.get("is_break", False))
        break_label = d.get("break_label", "Break")
        is_active = bool(d.get("is_active", True))

        with connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO portal_period (academic_year, period_number, period_name, start_time, end_time, is_break, break_label, day_type, is_active)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (academic_year, period_number, day_type) DO UPDATE SET
                    period_name = EXCLUDED.period_name,
                    start_time = EXCLUDED.start_time,
                    end_time = EXCLUDED.end_time,
                    is_break = EXCLUDED.is_break,
                    break_label = EXCLUDED.break_label,
                    is_active = EXCLUDED.is_active
                RETURNING id
                """,
                [academic_year, period_number, period_name, start_time, end_time, is_break, break_label, day_type, is_active],
            )
            new_id = cursor.fetchone()[0]

        log_action(request.user, "period.create", "portal_period", new_id, d)
        return Response({"id": new_id, "detail": "Period saved."}, status=201)

    def put(self, request):
        if not table_exists("portal_period"):
            return Response({"detail": "Table not found."}, status=503)
        record_id = request.query_params.get("record_id")
        if not record_id:
            return Response({"detail": "record_id is required."}, status=400)
        d = request.data
        allowed = ["academic_year", "period_number", "period_name", "start_time", "end_time",
                    "is_break", "break_label", "day_type", "is_active"]
        updates = {k: v for k, v in d.items() if k in allowed}
        if not updates:
            return Response({"detail": "No valid fields."}, status=400)
        set_clause = ", ".join(f"{k}=%s" for k in updates)
        with connection.cursor() as cursor:
            cursor.execute(
                f"UPDATE portal_period SET {set_clause} WHERE id=%s",
                list(updates.values()) + [record_id],
            )
        log_action(request.user, "period.update", "portal_period", record_id, updates)
        return Response({"detail": "Updated."})

    def delete(self, request):
        if not table_exists("portal_period"):
            return Response({"detail": "Table not found."}, status=503)
        record_id = request.query_params.get("record_id")
        if not record_id:
            return Response({"detail": "record_id is required."}, status=400)
        with connection.cursor() as cursor:
            cursor.execute("DELETE FROM portal_period WHERE id=%s", [record_id])
        log_action(request.user, "period.delete", "portal_period", record_id, {})
        return Response({"detail": "Deleted."})


# ---------------------------------------------------------------------------
# VIEW 8: Generate Default Periods
# ---------------------------------------------------------------------------
class GenerateDefaultPeriodsView(AdminMixin, APIView):
    """POST /admin-portal/timetable/periods/generate-default/"""

    def post(self, request):
        if not table_exists("portal_period"):
            return Response({"detail": "Table not found."}, status=503)
        academic_year = request.data.get("academic_year", "2025-26")
        day_type = request.data.get("day_type", "FullDay")

        default_periods = [
            (1, "Period 1", "08:30", "09:15", False, "Break"),
            (2, "Period 2", "09:15", "10:00", False, "Break"),
            (3, "Period 3", "10:00", "10:45", False, "Break"),
            (0, "Break", "10:45", "11:00", True, "Morning Break"),
            (4, "Period 4", "11:00", "11:45", False, "Break"),
            (5, "Period 5", "11:45", "12:30", False, "Break"),
            (99, "Lunch", "12:30", "13:15", True, "Lunch Break"),
            (6, "Period 6", "13:15", "14:00", False, "Break"),
            (7, "Period 7", "14:00", "14:45", False, "Break"),
            (8, "Period 8", "14:45", "15:30", False, "Break"),
        ]

        inserted = 0
        with connection.cursor() as cursor:
            for pnum, pname, stime, etime, is_brk, brk_lbl in default_periods:
                cursor.execute(
                    """
                    INSERT INTO portal_period (academic_year, period_number, period_name, start_time, end_time, is_break, break_label, day_type, is_active)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, true)
                    ON CONFLICT (academic_year, period_number, day_type) DO NOTHING
                    """,
                    [academic_year, pnum, pname, stime, etime, is_brk, brk_lbl, day_type],
                )
                inserted += cursor.rowcount

        log_action(request.user, "period.generate_defaults", "portal_period", 0, {"academic_year": academic_year, "day_type": day_type, "created": inserted})
        return Response({"detail": f"{inserted} period(s) created.", "created": inserted})


# ---------------------------------------------------------------------------
# VIEW 9: Subject Allocation
# ---------------------------------------------------------------------------
class SubjectAllocationView(AdminMixin, APIView):
    """GET /admin-portal/timetable/subject-allocations/?class_id=&academic_year=
    POST /admin-portal/timetable/subject-allocations/
    PUT /admin-portal/timetable/subject-allocations/?record_id=
    DELETE /admin-portal/timetable/subject-allocations/?record_id="""

    def get(self, request):
        if not table_exists("portal_subject_allocation"):
            return Response([])
        class_id = request.query_params.get("class_id")
        academic_year = request.query_params.get("academic_year")
        sql = """
            SELECT sa.*, s.name AS subject_name,
                   c.name || '-' || c.section AS class_name
            FROM portal_subject_allocation sa
            LEFT JOIN portal_subject s ON s.id = sa.subject_id
            LEFT JOIN portal_class c ON c.id = sa.class_id
        """
        conditions = []
        params = []
        if class_id:
            conditions.append("sa.class_id = %s")
            params.append(class_id)
        if academic_year:
            conditions.append("sa.academic_year = %s")
            params.append(academic_year)
        if conditions:
            sql += " WHERE " + " AND ".join(conditions)
        sql += " ORDER BY sa.class_id, sa.subject_id"
        return Response(serialise(rows(sql, params)))

    def post(self, request):
        if not table_exists("portal_subject_allocation"):
            return Response({"detail": "Table not found."}, status=503)
        d = request.data
        academic_year = d.get("academic_year")
        class_id = d.get("class_id")
        subject_id = d.get("subject_id")
        weekly_periods = d.get("weekly_periods", 1)

        if not all([academic_year, class_id, subject_id]):
            return Response({"detail": "academic_year, class_id and subject_id are required."}, status=400)

        is_mandatory = bool(d.get("is_mandatory", True))
        is_elective = bool(d.get("is_elective", False))

        with connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO portal_subject_allocation (academic_year, class_id, subject_id, weekly_periods, is_mandatory, is_elective)
                VALUES (%s, %s, %s, %s, %s, %s)
                ON CONFLICT (academic_year, class_id, subject_id) DO UPDATE SET
                    weekly_periods = EXCLUDED.weekly_periods,
                    is_mandatory = EXCLUDED.is_mandatory,
                    is_elective = EXCLUDED.is_elective
                RETURNING id
                """,
                [academic_year, class_id, subject_id, weekly_periods, is_mandatory, is_elective],
            )
            new_id = cursor.fetchone()[0]

        log_action(request.user, "subject_allocation.create", "portal_subject_allocation", new_id, d)
        return Response({"id": new_id, "detail": "Subject allocation saved."}, status=201)

    def put(self, request):
        if not table_exists("portal_subject_allocation"):
            return Response({"detail": "Table not found."}, status=503)
        record_id = request.query_params.get("record_id")
        if not record_id:
            return Response({"detail": "record_id is required."}, status=400)
        d = request.data
        allowed = ["academic_year", "class_id", "subject_id", "weekly_periods", "is_mandatory", "is_elective"]
        updates = {k: v for k, v in d.items() if k in allowed}
        if not updates:
            return Response({"detail": "No valid fields."}, status=400)
        set_clause = ", ".join(f"{k}=%s" for k in updates)
        with connection.cursor() as cursor:
            cursor.execute(
                f"UPDATE portal_subject_allocation SET {set_clause} WHERE id=%s",
                list(updates.values()) + [record_id],
            )
        log_action(request.user, "subject_allocation.update", "portal_subject_allocation", record_id, updates)
        return Response({"detail": "Updated."})

    def delete(self, request):
        if not table_exists("portal_subject_allocation"):
            return Response({"detail": "Table not found."}, status=503)
        record_id = request.query_params.get("record_id")
        if not record_id:
            return Response({"detail": "record_id is required."}, status=400)
        with connection.cursor() as cursor:
            cursor.execute("DELETE FROM portal_subject_allocation WHERE id=%s", [record_id])
        log_action(request.user, "subject_allocation.delete", "portal_subject_allocation", record_id, {})
        return Response({"detail": "Deleted."})


# ---------------------------------------------------------------------------
# VIEW 10: Teacher Allocation
# ---------------------------------------------------------------------------
class TeacherAllocationView(AdminMixin, APIView):
    """GET /admin-portal/timetable/teacher-allocations/?class_id=&subject_id=&academic_year=
    POST /admin-portal/timetable/teacher-allocations/
    PUT /admin-portal/timetable/teacher-allocations/?record_id=
    DELETE /admin-portal/timetable/teacher-allocations/?record_id="""

    def get(self, request):
        if not table_exists("portal_teacher_allocation"):
            return Response([])
        class_id = request.query_params.get("class_id")
        subject_id = request.query_params.get("subject_id")
        academic_year = request.query_params.get("academic_year")
        sql = """
            SELECT ta.*,
                   COALESCE(u.first_name || ' ' || u.last_name, u.username) AS teacher_name,
                   s.name AS subject_name,
                   c.name || '-' || c.section AS class_name
            FROM portal_teacher_allocation ta
            LEFT JOIN auth_user u ON u.id = ta.teacher_id
            LEFT JOIN portal_subject s ON s.id = ta.subject_id
            LEFT JOIN portal_class c ON c.id = ta.class_id
        """
        conditions = []
        params = []
        if class_id:
            conditions.append("ta.class_id = %s")
            params.append(class_id)
        if subject_id:
            conditions.append("ta.subject_id = %s")
            params.append(subject_id)
        if academic_year:
            conditions.append("ta.academic_year = %s")
            params.append(academic_year)
        if conditions:
            sql += " WHERE " + " AND ".join(conditions)
        sql += " ORDER BY ta.class_id, ta.subject_id"
        return Response(serialise(rows(sql, params)))

    def post(self, request):
        if not table_exists("portal_teacher_allocation"):
            return Response({"detail": "Table not found."}, status=503)
        d = request.data
        academic_year = d.get("academic_year")
        class_id = d.get("class_id")
        subject_id = d.get("subject_id")
        teacher_id = d.get("teacher_id")
        max_periods = d.get("max_periods_per_week", 1)

        if not all([academic_year, class_id, subject_id, teacher_id]):
            return Response({"detail": "academic_year, class_id, subject_id and teacher_id are required."}, status=400)

        with connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO portal_teacher_allocation (academic_year, class_id, subject_id, teacher_id, max_periods_per_week)
                VALUES (%s, %s, %s, %s, %s)
                ON CONFLICT (academic_year, class_id, subject_id, teacher_id) DO UPDATE SET
                    max_periods_per_week = EXCLUDED.max_periods_per_week
                RETURNING id
                """,
                [academic_year, class_id, subject_id, teacher_id, max_periods],
            )
            new_id = cursor.fetchone()[0]

        log_action(request.user, "teacher_allocation.create", "portal_teacher_allocation", new_id, d)
        return Response({"id": new_id, "detail": "Teacher allocation saved."}, status=201)

    def put(self, request):
        if not table_exists("portal_teacher_allocation"):
            return Response({"detail": "Table not found."}, status=503)
        record_id = request.query_params.get("record_id")
        if not record_id:
            return Response({"detail": "record_id is required."}, status=400)
        d = request.data
        allowed = ["academic_year", "class_id", "subject_id", "teacher_id", "max_periods_per_week"]
        updates = {k: v for k, v in d.items() if k in allowed}
        if not updates:
            return Response({"detail": "No valid fields."}, status=400)
        set_clause = ", ".join(f"{k}=%s" for k in updates)
        with connection.cursor() as cursor:
            cursor.execute(
                f"UPDATE portal_teacher_allocation SET {set_clause} WHERE id=%s",
                list(updates.values()) + [record_id],
            )
        log_action(request.user, "teacher_allocation.update", "portal_teacher_allocation", record_id, updates)
        return Response({"detail": "Updated."})

    def delete(self, request):
        if not table_exists("portal_teacher_allocation"):
            return Response({"detail": "Table not found."}, status=503)
        record_id = request.query_params.get("record_id")
        if not record_id:
            return Response({"detail": "record_id is required."}, status=400)
        with connection.cursor() as cursor:
            cursor.execute("DELETE FROM portal_teacher_allocation WHERE id=%s", [record_id])
        log_action(request.user, "teacher_allocation.delete", "portal_teacher_allocation", record_id, {})
        return Response({"detail": "Deleted."})


# ---------------------------------------------------------------------------
# VIEW 11: Classroom Allocation
# ---------------------------------------------------------------------------
class ClassroomAllocationView(AdminMixin, APIView):
    """GET /admin-portal/timetable/classroom-allocations/?class_id=&academic_year=
    POST /admin-portal/timetable/classroom-allocations/
    PUT /admin-portal/timetable/classroom-allocations/?record_id=
    DELETE /admin-portal/timetable/classroom-allocations/?record_id="""

    def get(self, request):
        if not table_exists("portal_classroom_allocation"):
            return Response([])
        class_id = request.query_params.get("class_id")
        academic_year = request.query_params.get("academic_year")
        sql = """
            SELECT ca.*, c.name || '-' || c.section AS class_name
            FROM portal_classroom_allocation ca
            LEFT JOIN portal_class c ON c.id = ca.class_id
        """
        conditions = []
        params = []
        if class_id:
            conditions.append("ca.class_id = %s")
            params.append(class_id)
        if academic_year:
            conditions.append("ca.academic_year = %s")
            params.append(academic_year)
        if conditions:
            sql += " WHERE " + " AND ".join(conditions)
        sql += " ORDER BY ca.class_id, ca.room_number"
        return Response(serialise(rows(sql, params)))

    def post(self, request):
        if not table_exists("portal_classroom_allocation"):
            return Response({"detail": "Table not found."}, status=503)
        d = request.data
        academic_year = d.get("academic_year")
        class_id = d.get("class_id")
        room_number = d.get("room_number")

        if not all([academic_year, class_id, room_number]):
            return Response({"detail": "academic_year, class_id and room_number are required."}, status=400)

        room_type = d.get("room_type", "Classroom")
        capacity = d.get("capacity", 0)
        is_lab = bool(d.get("is_lab", False))

        with connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO portal_classroom_allocation (academic_year, class_id, room_number, room_type, capacity, is_lab)
                VALUES (%s, %s, %s, %s, %s, %s)
                ON CONFLICT (academic_year, class_id, room_number) DO UPDATE SET
                    room_type = EXCLUDED.room_type,
                    capacity = EXCLUDED.capacity,
                    is_lab = EXCLUDED.is_lab
                RETURNING id
                """,
                [academic_year, class_id, room_number, room_type, capacity, is_lab],
            )
            new_id = cursor.fetchone()[0]

        log_action(request.user, "classroom_allocation.create", "portal_classroom_allocation", new_id, d)
        return Response({"id": new_id, "detail": "Classroom allocation saved."}, status=201)

    def put(self, request):
        if not table_exists("portal_classroom_allocation"):
            return Response({"detail": "Table not found."}, status=503)
        record_id = request.query_params.get("record_id")
        if not record_id:
            return Response({"detail": "record_id is required."}, status=400)
        d = request.data
        allowed = ["academic_year", "class_id", "room_number", "room_type", "capacity", "is_lab"]
        updates = {k: v for k, v in d.items() if k in allowed}
        if not updates:
            return Response({"detail": "No valid fields."}, status=400)
        set_clause = ", ".join(f"{k}=%s" for k in updates)
        with connection.cursor() as cursor:
            cursor.execute(
                f"UPDATE portal_classroom_allocation SET {set_clause} WHERE id=%s",
                list(updates.values()) + [record_id],
            )
        log_action(request.user, "classroom_allocation.update", "portal_classroom_allocation", record_id, updates)
        return Response({"detail": "Updated."})

    def delete(self, request):
        if not table_exists("portal_classroom_allocation"):
            return Response({"detail": "Table not found."}, status=503)
        record_id = request.query_params.get("record_id")
        if not record_id:
            return Response({"detail": "record_id is required."}, status=400)
        with connection.cursor() as cursor:
            cursor.execute("DELETE FROM portal_classroom_allocation WHERE id=%s", [record_id])
        log_action(request.user, "classroom_allocation.delete", "portal_classroom_allocation", record_id, {})
        return Response({"detail": "Deleted."})


# ---------------------------------------------------------------------------
# VIEW 12: Substitute Teacher
# ---------------------------------------------------------------------------
class SubstituteTeacherView(AdminMixin, APIView):
    """GET /admin-portal/timetable/substitutes/?date=&teacher_id=
    POST /admin-portal/timetable/substitutes/
    DELETE /admin-portal/timetable/substitutes/?record_id="""

    def get(self, request):
        if not table_exists("portal_substitute"):
            return Response([])
        sub_date = request.query_params.get("date")
        teacher_id = request.query_params.get("teacher_id")
        sql = """
            SELECT sub.*,
                   COALESCE(ou.first_name || ' ' || ou.last_name, ou.username) AS original_teacher_name,
                   COALESCE(su.first_name || ' ' || su.last_name, su.username) AS substitute_teacher_name,
                   t.day_of_week, t.period_number, t.start_time, t.end_time,
                   c.name || '-' || c.section AS class_name
            FROM portal_substitute sub
            LEFT JOIN auth_user ou ON ou.id = sub.original_teacher_id
            LEFT JOIN auth_user su ON su.id = sub.substitute_teacher_id
            LEFT JOIN portal_timetable t ON t.id = sub.timetable_entry_id
            LEFT JOIN portal_class c ON c.id = t.class_id
        """
        conditions = []
        params = []
        if sub_date:
            conditions.append("sub.substitute_date = %s")
            params.append(sub_date)
        if teacher_id:
            conditions.append("(sub.original_teacher_id = %s OR sub.substitute_teacher_id = %s)")
            params.extend([teacher_id, teacher_id])
        if conditions:
            sql += " WHERE " + " AND ".join(conditions)
        sql += " ORDER BY sub.substitute_date DESC"
        return Response(serialise(rows(sql, params)))

    def post(self, request):
        if not table_exists("portal_substitute"):
            return Response({"detail": "Table not found."}, status=503)
        d = request.data
        timetable_entry_id = d.get("timetable_entry_id")
        original_teacher_id = d.get("original_teacher_id")
        substitute_teacher_id = d.get("substitute_teacher_id")
        substitute_date = d.get("substitute_date")
        reason = d.get("reason", "")

        if not all([timetable_entry_id, original_teacher_id, substitute_teacher_id, substitute_date]):
            return Response({"detail": "timetable_entry_id, original_teacher_id, substitute_teacher_id and substitute_date are required."}, status=400)

        with connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO portal_substitute (timetable_entry_id, original_teacher_id, substitute_teacher_id, substitute_date, reason)
                VALUES (%s, %s, %s, %s, %s) RETURNING id
                """,
                [timetable_entry_id, original_teacher_id, substitute_teacher_id, substitute_date, reason],
            )
            new_id = cursor.fetchone()[0]

            if table_exists("portal_timetable"):
                cursor.execute(
                    "UPDATE portal_timetable SET updated_at=now() WHERE id=%s",
                    [timetable_entry_id],
                )

        log_action(request.user, "substitute.create", "portal_substitute", new_id, d)
        return Response({"id": new_id, "detail": "Substitute assigned."}, status=201)

    def delete(self, request):
        if not table_exists("portal_substitute"):
            return Response({"detail": "Table not found."}, status=503)
        record_id = request.query_params.get("record_id")
        if not record_id:
            return Response({"detail": "record_id is required."}, status=400)

        sub = row("SELECT timetable_entry_id FROM portal_substitute WHERE id=%s", [record_id])
        with connection.cursor() as cursor:
            cursor.execute("DELETE FROM portal_substitute WHERE id=%s", [record_id])
            if sub and sub.get("timetable_entry_id") and table_exists("portal_timetable"):
                cursor.execute(
                    "UPDATE portal_timetable SET updated_at=now() WHERE id=%s",
                    [sub["timetable_entry_id"]],
                )

        log_action(request.user, "substitute.delete", "portal_substitute", record_id, {})
        return Response({"detail": "Deleted."})


# ---------------------------------------------------------------------------
# VIEW 13: Timetable Approval
# ---------------------------------------------------------------------------
class TimetableApprovalView(AdminMixin, APIView):
    """GET /admin-portal/timetable/approvals/?class_id=&status=&academic_year=
    POST /admin-portal/timetable/approvals/
    PUT /admin-portal/timetable/approvals/?record_id="""

    def get(self, request):
        if not table_exists("portal_timetable_approval"):
            return Response([])
        class_id = request.query_params.get("class_id")
        status_filter = request.query_params.get("status")
        academic_year = request.query_params.get("academic_year")
        sql = """
            SELECT ta.*,
                   c.name || '-' || c.section AS class_name,
                   COALESCE(sb.first_name || ' ' || sb.last_name, sb.username) AS submitted_by_name,
                   COALESCE(ab.first_name || ' ' || ab.last_name, ab.username) AS approved_by_name
            FROM portal_timetable_approval ta
            LEFT JOIN portal_class c ON c.id = ta.class_id
            LEFT JOIN auth_user sb ON sb.id = ta.submitted_by
            LEFT JOIN auth_user ab ON ab.id = ta.approved_by
        """
        conditions = []
        params = []
        if class_id:
            conditions.append("ta.class_id = %s")
            params.append(class_id)
        if status_filter:
            conditions.append("ta.status = %s")
            params.append(status_filter)
        if academic_year:
            conditions.append("ta.academic_year = %s")
            params.append(academic_year)
        if conditions:
            sql += " WHERE " + " AND ".join(conditions)
        sql += " ORDER BY ta.created_at DESC"
        return Response(serialise(rows(sql, params)))

    def post(self, request):
        if not table_exists("portal_timetable_approval"):
            return Response({"detail": "Table not found."}, status=503)
        d = request.data
        class_id = d.get("class_id")
        academic_year = d.get("academic_year")

        if not all([class_id, academic_year]):
            return Response({"detail": "class_id and academic_year are required."}, status=400)

        with connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO portal_timetable_approval (class_id, academic_year, status, submitted_by, submitted_at)
                VALUES (%s, %s, 'Submitted', %s, now())
                ON CONFLICT (class_id, academic_year) DO UPDATE SET
                    status = 'Submitted',
                    submitted_by = EXCLUDED.submitted_by,
                    submitted_at = now(),
                    rejection_reason = NULL,
                    reviewed_at = NULL
                RETURNING id
                """,
                [class_id, academic_year, request.user.id],
            )
            new_id = cursor.fetchone()[0]

        log_action(request.user, "timetable_approval.submit", "portal_timetable_approval", new_id, d)
        return Response({"id": new_id, "detail": "Approval request submitted."}, status=201)

    def put(self, request):
        if not table_exists("portal_timetable_approval"):
            return Response({"detail": "Table not found."}, status=503)
        record_id = request.query_params.get("record_id")
        if not record_id:
            return Response({"detail": "record_id is required."}, status=400)

        d = request.data
        new_status = d.get("status")
        rejection_reason = d.get("rejection_reason", "")

        if new_status not in ("Approved", "Rejected"):
            return Response({"detail": "status must be 'Approved' or 'Rejected'."}, status=400)

        if new_status == "Approved":
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    UPDATE portal_timetable_approval
                    SET status = 'Approved', approved_by = %s, reviewed_at = now(), updated_at = now()
                    WHERE id = %s
                    """,
                    [request.user.id, record_id],
                )
        else:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    UPDATE portal_timetable_approval
                    SET status = 'Rejected', rejection_reason = %s, reviewed_at = now(), updated_at = now()
                    WHERE id = %s
                    """,
                    [rejection_reason, record_id],
                )

        approval = row("SELECT class_id, academic_year FROM portal_timetable_approval WHERE id=%s", [record_id])
        if approval and table_exists("portal_timetable"):
            with connection.cursor() as cursor:
                cursor.execute(
                    "UPDATE portal_timetable SET updated_at=now() WHERE class_id=%s AND academic_year=%s",
                    [approval["class_id"], approval["academic_year"]],
                )

        log_action(request.user, f"timetable_approval.{new_status.lower()}", "portal_timetable_approval", record_id, d)
        return Response({"detail": f"Timetable {new_status.lower()}."})

    def delete(self, request):
        if not table_exists("portal_timetable_approval"):
            return Response({"detail": "Table not found."}, status=503)
        record_id = request.query_params.get("record_id")
        if not record_id:
            return Response({"detail": "record_id is required."}, status=400)
        with connection.cursor() as cursor:
            cursor.execute("DELETE FROM portal_timetable_approval WHERE id=%s", [record_id])
        log_action(request.user, "timetable_approval.delete", "portal_timetable_approval", record_id, {})
        return Response({"detail": "Deleted."})


# ---------------------------------------------------------------------------
# VIEW 14: Timetable Notification
# ---------------------------------------------------------------------------
class TimetableNotificationView(AdminMixin, APIView):
    """GET /admin-portal/timetable/notifications/?class_id=
    POST /admin-portal/timetable/notifications/
    DELETE /admin-portal/timetable/notifications/?record_id="""

    def get(self, request):
        if not table_exists("portal_timetable_notification"):
            return Response([])
        class_id = request.query_params.get("class_id")
        sql = """
            SELECT tn.*,
                   c.name || '-' || c.section AS class_name
            FROM portal_timetable_notification tn
            LEFT JOIN portal_class c ON c.id = tn.class_id
        """
        conditions = []
        params = []
        if class_id:
            conditions.append("tn.class_id = %s")
            params.append(class_id)
        if conditions:
            sql += " WHERE " + " AND ".join(conditions)
        sql += " ORDER BY tn.created_at DESC"
        return Response(serialise(rows(sql, params)))

    def post(self, request):
        if not table_exists("portal_timetable_notification"):
            return Response({"detail": "Table not found."}, status=503)
        d = request.data
        class_id = d.get("class_id")
        notification_type = d.get("notification_type")
        title = d.get("title")
        message = d.get("message")
        target_audience = d.get("target_audience", "All")

        if not all([class_id, notification_type, title, message]):
            return Response({"detail": "class_id, notification_type, title and message are required."}, status=400)

        with connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO portal_timetable_notification (class_id, notification_type, title, message, target_audience)
                VALUES (%s, %s, %s, %s, %s) RETURNING id
                """,
                [class_id, notification_type, title, message, target_audience],
            )
            new_id = cursor.fetchone()[0]

        log_action(request.user, "timetable_notification.create", "portal_timetable_notification", new_id, d)
        return Response({"id": new_id, "detail": "Notification created."}, status=201)

    def delete(self, request):
        if not table_exists("portal_timetable_notification"):
            return Response({"detail": "Table not found."}, status=503)
        record_id = request.query_params.get("record_id")
        if not record_id:
            return Response({"detail": "record_id is required."}, status=400)
        with connection.cursor() as cursor:
            cursor.execute("DELETE FROM portal_timetable_notification WHERE id=%s", [record_id])
        log_action(request.user, "timetable_notification.delete", "portal_timetable_notification", record_id, {})
        return Response({"detail": "Deleted."})


# ---------------------------------------------------------------------------
# VIEW 15: Send Timetable Notification
# ---------------------------------------------------------------------------
class SendTimetableNotificationView(AdminMixin, APIView):
    """POST /admin-portal/timetable/notifications/send/"""

    def post(self, request):
        if not table_exists("portal_timetable_notification"):
            return Response({"detail": "Table not found."}, status=503)
        notification_id = request.data.get("notification_id")
        if not notification_id:
            return Response({"detail": "notification_id is required."}, status=400)

        existing = row("SELECT id, is_sent FROM portal_timetable_notification WHERE id=%s", [notification_id])
        if not existing:
            return Response({"detail": "Notification not found."}, status=404)
        if existing["is_sent"]:
            return Response({"detail": "Notification already sent."}, status=400)

        with connection.cursor() as cursor:
            cursor.execute(
                "UPDATE portal_timetable_notification SET is_sent = true, sent_at = now() WHERE id = %s",
                [notification_id],
            )

        log_action(request.user, "timetable_notification.send", "portal_timetable_notification", notification_id, {})
        return Response({"detail": "Notification sent."})


# ---------------------------------------------------------------------------
# VIEW 16: Timetable Audit Log
# ---------------------------------------------------------------------------
class TimetableAuditLogView(AdminMixin, APIView):
    """GET /admin-portal/timetable/audit-log/?class_id=&academic_year=&action="""

    def get(self, request):
        if not table_exists("portal_timetable_audit"):
            return Response([])
        class_id = request.query_params.get("class_id")
        academic_year = request.query_params.get("academic_year")
        action_filter = request.query_params.get("action")
        sql = """
            SELECT ta.*,
                   COALESCE(u.first_name || ' ' || u.last_name, u.username) AS action_by_name
            FROM portal_timetable_audit ta
            LEFT JOIN auth_user u ON u.id = ta.action_by
        """
        conditions = []
        params = []
        if class_id:
            conditions.append("ta.class_id = %s")
            params.append(class_id)
        if academic_year:
            conditions.append("ta.academic_year = %s")
            params.append(academic_year)
        if action_filter:
            conditions.append("ta.action = %s")
            params.append(action_filter)
        if conditions:
            sql += " WHERE " + " AND ".join(conditions)
        sql += " ORDER BY ta.created_at DESC LIMIT 100"
        return Response(serialise(rows(sql, params)))


# ---------------------------------------------------------------------------
# VIEW 17: Timetable Reports
# ---------------------------------------------------------------------------
class TimetableReportsView(AdminMixin, APIView):
    """GET /admin-portal/timetable/reports/?type=class&class_id=&teacher_id="""

    def get(self, request):
        report_type = request.query_params.get("type", "class")
        academic_year = request.query_params.get("academic_year", "2025-26")

        if report_type == "class":
            return self._class_report(request, academic_year)
        elif report_type == "teacher":
            return self._teacher_report(request, academic_year)
        elif report_type == "subject":
            return self._subject_report(request, academic_year)
        elif report_type == "classroom":
            return self._classroom_report(request, academic_year)
        elif report_type == "workload":
            return self._workload_report(request, academic_year)
        elif report_type == "labs":
            return self._lab_report(request, academic_year)
        elif report_type == "frees":
            return self._frees_report(request, academic_year)
        return Response({"detail": f"Unknown report type: {report_type}"}, status=400)

    def _class_report(self, request, academic_year):
        if not table_exists("portal_timetable"):
            return Response([])
        class_id = request.query_params.get("class_id")
        if not class_id:
            return Response({"detail": "class_id is required for class report."}, status=400)
        data = rows(
            """
            SELECT t.id, t.day_of_week, t.period_number, t.start_time, t.end_time,
                   t.room_number, t.is_break, t.break_label,
                   COALESCE(s.name, '') AS subject_name,
                   COALESCE(u.first_name || ' ' || u.last_name, u.username) AS teacher_name
            FROM portal_timetable t
            LEFT JOIN portal_subject s ON s.id = t.subject_id
            LEFT JOIN auth_user u ON u.id = t.teacher_id
            WHERE t.class_id = %s AND t.academic_year = %s
            ORDER BY
              CASE t.day_of_week
                WHEN 'Monday' THEN 1 WHEN 'Tuesday' THEN 2 WHEN 'Wednesday' THEN 3
                WHEN 'Thursday' THEN 4 WHEN 'Friday' THEN 5 WHEN 'Saturday' THEN 6
              END, t.start_time
            """,
            [class_id, academic_year],
        )
        return Response(serialise(data))

    def _teacher_report(self, request, academic_year):
        if not table_exists("portal_timetable"):
            return Response([])
        teacher_id = request.query_params.get("teacher_id")
        if not teacher_id:
            return Response({"detail": "teacher_id is required for teacher report."}, status=400)
        data = rows(
            """
            SELECT t.day_of_week, t.period_number, t.start_time, t.end_time,
                   t.room_number, t.is_break,
                   COALESCE(s.name, '') AS subject_name,
                   c.name || '-' || c.section AS class_name
            FROM portal_timetable t
            LEFT JOIN portal_subject s ON s.id = t.subject_id
            LEFT JOIN portal_class c ON c.id = t.class_id
            WHERE t.teacher_id = %s AND t.academic_year = %s
            ORDER BY
              CASE t.day_of_week
                WHEN 'Monday' THEN 1 WHEN 'Tuesday' THEN 2 WHEN 'Wednesday' THEN 3
                WHEN 'Thursday' THEN 4 WHEN 'Friday' THEN 5 WHEN 'Saturday' THEN 6
              END, t.start_time
            """,
            [teacher_id, academic_year],
        )
        return Response(serialise(data))

    def _subject_report(self, request, academic_year):
        if not table_exists("portal_timetable"):
            return Response([])
        data = rows(
            """
            SELECT s.name AS subject_name, c.name || '-' || c.section AS class_name,
                   COUNT(t.id)::int AS periods_per_week
            FROM portal_timetable t
            LEFT JOIN portal_subject s ON s.id = t.subject_id
            LEFT JOIN portal_class c ON c.id = t.class_id
            WHERE t.academic_year = %s AND t.is_break = false
            GROUP BY s.name, c.name, c.section
            ORDER BY s.name, c.name
            """,
            [academic_year],
        )
        return Response(serialise(data))

    def _classroom_report(self, request, academic_year):
        if not table_exists("portal_timetable"):
            return Response([])
        data = rows(
            """
            SELECT t.room_number,
                   COUNT(DISTINCT t.class_id)::int AS classes_using,
                   COUNT(DISTINCT t.day_of_week)::int AS days_used,
                   COUNT(t.id)::int AS total_periods
            FROM portal_timetable t
            WHERE t.academic_year = %s AND t.is_break = false AND t.room_number IS NOT NULL
            GROUP BY t.room_number
            ORDER BY t.room_number
            """,
            [academic_year],
        )
        return Response(serialise(data))

    def _workload_report(self, request, academic_year):
        if not table_exists("portal_timetable"):
            return Response([])
        data = rows(
            """
            SELECT u.id AS teacher_id,
                   COALESCE(u.first_name || ' ' || u.last_name, u.username) AS teacher_name,
                   COUNT(t.id)::int AS total_periods,
                   COUNT(DISTINCT t.day_of_week)::int AS days_teaching,
                   COUNT(DISTINCT t.class_id)::int AS classes_count,
                   COUNT(DISTINCT t.subject_id)::int AS subjects_count
            FROM portal_timetable t
            JOIN auth_user u ON u.id = t.teacher_id
            WHERE t.academic_year = %s AND t.is_break = false
            GROUP BY u.id, u.first_name, u.last_name, u.username
            ORDER BY total_periods DESC
            """,
            [academic_year],
        )
        return Response(serialise(data))

    def _lab_report(self, request, academic_year):
        if not table_exists("portal_timetable"):
            return Response([])
        if table_exists("portal_lab_timetable"):
            data = rows(
                """
                SELECT lt.*, COALESCE(u.first_name || ' ' || u.last_name, u.username) AS teacher_name
                FROM portal_lab_timetable lt
                LEFT JOIN auth_user u ON u.id = lt.teacher_id
                WHERE lt.is_published = true
                ORDER BY lt.lab_room, lt.day_of_week
                """,
                [],
            )
        else:
            data = rows(
                """
                SELECT t.id, t.room_number AS lab_room, t.teacher_id,
                       COALESCE(u.first_name || ' ' || u.last_name, u.username) AS teacher_name,
                       t.day_of_week, t.start_time, t.end_time, t.is_published
                FROM portal_timetable t
                LEFT JOIN auth_user u ON u.id = t.teacher_id
                WHERE t.academic_year = %s AND t.room_number LIKE '%%Lab%%'
                ORDER BY t.room_number, t.day_of_week
                """,
                [academic_year],
            )
        return Response(serialise(data))

    def _frees_report(self, request, academic_year):
        if not table_exists("portal_timetable") or not table_exists("portal_period"):
            return Response([])
        periods = rows(
            "SELECT period_number, period_name, start_time, end_time FROM portal_period WHERE academic_year = %s AND is_break = false ORDER BY period_number",
            [academic_year],
        )
        teachers = rows(
            """
            SELECT DISTINCT t.teacher_id,
                   COALESCE(u.first_name || ' ' || u.last_name, u.username) AS teacher_name
            FROM portal_timetable t
            JOIN auth_user u ON u.id = t.teacher_id
            WHERE t.academic_year = %s AND t.is_break = false
            """,
            [academic_year],
        )
        days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]
        result = []
        for teacher in teachers:
            teacher_periods = rows(
                "SELECT day_of_week, period_number FROM portal_timetable WHERE teacher_id = %s AND academic_year = %s AND is_break = false",
                [teacher["teacher_id"], academic_year],
            )
            assigned = {(r["day_of_week"], r["period_number"]) for r in teacher_periods}
            free_list = []
            for p in periods:
                for d in days:
                    if (d, p["period_number"]) not in assigned:
                        free_list.append({"day_of_week": d, "period_number": p["period_number"], "period_name": p["period_name"]})
            result.append({
                "teacher_id": teacher["teacher_id"],
                "teacher_name": teacher["teacher_name"],
                "free_periods": free_list,
                "free_count": len(free_list),
            })
        result.sort(key=lambda x: x["free_count"], reverse=True)
        return Response(serialise(result))


# ---------------------------------------------------------------------------
# VIEW 18: Timetable Analytics
# ---------------------------------------------------------------------------
class TimetableAnalyticsView(AdminMixin, APIView):
    """GET /admin-portal/timetable/analytics/"""

    def get(self, request):
        academic_year = request.query_params.get("academic_year", "2025-26")
        today = date.today()
        day_name = today.strftime("%A")

        result = {
            "classes_scheduled_today": 0,
            "teacher_workload": 0,
            "classroom_occupancy": 0,
            "free_classrooms": 0,
            "subject_coverage": 0,
            "total_classes": 0,
            "total_teachers": 0,
            "total_periods": 0,
            "approval_pending": 0,
            "substitutes_today": 0,
            "lab_sessions": 0,
        }

        if table_exists("portal_timetable"):
            r = row(
                "SELECT COUNT(*)::int AS c FROM portal_timetable WHERE academic_year = %s AND day_of_week = %s",
                [academic_year, day_name],
            )
            result["classes_scheduled_today"] = r["c"] if r else 0

            r = row(
                "SELECT COUNT(*)::int AS c FROM portal_timetable WHERE academic_year = %s AND is_break = false",
                [academic_year],
            )
            result["teacher_workload"] = r["c"] if r else 0

            r = row(
                "SELECT COUNT(DISTINCT room_number)::int AS c FROM portal_timetable WHERE academic_year = %s AND room_number IS NOT NULL AND is_break = false",
                [academic_year],
            )
            result["classroom_occupancy"] = r["c"] if r else 0

            if table_exists("portal_classroom_allocation"):
                total = row(
                    "SELECT COUNT(DISTINCT room_number)::int AS c FROM portal_classroom_allocation WHERE academic_year = %s",
                    [academic_year],
                )
                total_rooms = total["c"] if total else 0
                result["free_classrooms"] = max(0, total_rooms - result["classroom_occupancy"])
            else:
                result["free_classrooms"] = 0

            r = row(
                "SELECT COUNT(DISTINCT subject_id)::int AS c FROM portal_timetable WHERE academic_year = %s AND subject_id IS NOT NULL AND is_break = false",
                [academic_year],
            )
            result["subject_coverage"] = r["c"] if r else 0

            r = row(
                "SELECT COUNT(DISTINCT class_id)::int AS c FROM portal_timetable WHERE academic_year = %s",
                [academic_year],
            )
            result["total_classes"] = r["c"] if r else 0

            r = row(
                "SELECT COUNT(DISTINCT teacher_id)::int AS c FROM portal_timetable WHERE academic_year = %s AND teacher_id IS NOT NULL AND is_break = false",
                [academic_year],
            )
            result["total_teachers"] = r["c"] if r else 0

            r = row(
                "SELECT COUNT(*)::int AS c FROM portal_timetable WHERE academic_year = %s",
                [academic_year],
            )
            result["total_periods"] = r["c"] if r else 0

        if table_exists("portal_timetable_approval"):
            r = row(
                "SELECT COUNT(*)::int AS c FROM portal_timetable_approval WHERE academic_year = %s AND status = 'Submitted'",
                [academic_year],
            )
            result["approval_pending"] = r["c"] if r else 0

        if table_exists("portal_substitute"):
            r = row(
                "SELECT COUNT(*)::int AS c FROM portal_substitute WHERE substitute_date = %s",
                [today.isoformat()],
            )
            result["substitutes_today"] = r["c"] if r else 0

        if table_exists("portal_lab_timetable"):
            r = row(
                "SELECT COUNT(*)::int AS c FROM portal_lab_timetable WHERE is_published = true",
                [],
            )
            result["lab_sessions"] = r["c"] if r else 0
        elif table_exists("portal_timetable"):
            r = row(
                "SELECT COUNT(*)::int AS c FROM portal_timetable WHERE academic_year = %s AND room_number LIKE '%%Lab%%' AND is_break = false",
                [academic_year],
            )
            result["lab_sessions"] = r["c"] if r else 0

        return Response(serialise(result))


# ---------------------------------------------------------------------------
# VIEW 19: Timetable Workflow Config
# ---------------------------------------------------------------------------
class TimetableWorkflowConfigView(AdminMixin, APIView):
    """GET /admin-portal/timetable/workflow-config/"""

    def get(self, request):
        academic_year = request.query_params.get("academic_year", "2025-26")

        def table_info(table_name, extra_where=""):
            if not table_exists(table_name):
                return {"exists": False, "count": 0}
            where = f" WHERE academic_year = %s {extra_where}" if table_name not in (
                "portal_timetable", "portal_timetable_audit",
            ) else (f" WHERE academic_year = %s {extra_where}" if extra_where or table_name == "portal_timetable_audit" else "")
            params = [academic_year] if where and "academic_year" in where else []
            try:
                r = row(f"SELECT COUNT(*)::int AS c FROM {table_name}{where}", params)
                return {"exists": True, "count": r["c"] if r else 0}
            except Exception:
                return {"exists": True, "count": 0}

        def simple_table_info(table_name):
            if not table_exists(table_name):
                return {"exists": False, "count": 0}
            try:
                r = row(f"SELECT COUNT(*)::int AS c FROM {table_name}", [])
                return {"exists": True, "count": r["c"] if r else 0}
            except Exception:
                return {"exists": True, "count": 0}

        if table_exists("portal_timetable"):
            tt_count = row(
                "SELECT COUNT(*)::int AS c FROM portal_timetable WHERE academic_year = %s",
                [academic_year],
            )
            timetable_info = {"exists": True, "count": tt_count["c"] if tt_count else 0}
        else:
            timetable_info = {"exists": False, "count": 0}

        approval_info = {"exists": False, "count": 0}
        if table_exists("portal_timetable_approval"):
            a_count = row(
                "SELECT COUNT(*)::int AS c FROM portal_timetable_approval WHERE academic_year = %s",
                [academic_year],
            )
            approval_info = {"exists": True, "count": a_count["c"] if a_count else 0}

        return Response({
            "academic_calendar": table_info("portal_academic_calendar"),
            "working_days": table_info("portal_working_day"),
            "school_timings": table_info("portal_school_timing"),
            "periods": table_info("portal_period"),
            "subject_allocations": table_info("portal_subject_allocation"),
            "teacher_allocations": table_info("portal_teacher_allocation"),
            "classroom_allocations": table_info("portal_classroom_allocation"),
            "timetable_entries": timetable_info,
            "approvals": approval_info,
            "substitutes": simple_table_info("portal_substitute"),
        })
