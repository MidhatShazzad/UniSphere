import json

from flask import Blueprint, redirect, render_template, request, url_for

from models.db import get_db
from utils.analytics import student_global_analytics
from utils.decorators import role_required
from utils.helpers import EVENT_TYPE_COLORS, get_current_student

student_bp = Blueprint("student", __name__)


def student_sections(student_id):
    db = get_db()
    return db.execute(
        """
        SELECT
            sections.id AS section_id,
            sections.section_code,
            sections.room_no,
            sections.term,
            courses.course_code,
            courses.course_title,
            faculty.full_name AS faculty_name
        FROM enrollments
        JOIN sections ON enrollments.section_id = sections.id
        JOIN courses ON sections.course_id = courses.id
        LEFT JOIN faculty ON sections.faculty_id = faculty.id
        WHERE enrollments.student_id = ?
          AND enrollments.status = 'enrolled'
        ORDER BY courses.course_code, sections.section_code
        """,
        (student_id,),
    ).fetchall()


@student_bp.route("/dashboard")
@role_required("student")
def dashboard():
    db = get_db()
    student = get_current_student()

    courses = student_sections(student["id"])
    section_ids = [section["section_id"] for section in courses]

    global_announcements = db.execute(
        """
        SELECT announcements.*, users.username AS author_name
        FROM announcements
        JOIN users ON announcements.author_user_id = users.id
        WHERE section_id IS NULL
        ORDER BY created_at DESC
        LIMIT 5
        """
    ).fetchall()

    course_announcements = []
    if section_ids:
        placeholders = ",".join("?" for _ in section_ids)
        course_announcements = db.execute(
            f"""
            SELECT
                announcements.*,
                users.username AS author_name,
                courses.course_code,
                sections.section_code
            FROM announcements
            JOIN users ON announcements.author_user_id = users.id
            JOIN sections ON announcements.section_id = sections.id
            JOIN courses ON sections.course_id = courses.id
            WHERE announcements.section_id IN ({placeholders})
            ORDER BY announcements.created_at DESC
            LIMIT 8
            """,
            section_ids,
        ).fetchall()

    return render_template(
        "student/dashboard.html",
        student=student,
        courses=courses,
        global_announcements=global_announcements,
        course_announcements=course_announcements,
    )


@student_bp.route("/courses")
@role_required("student")
def courses():
    student = get_current_student()
    return render_template(
        "student/courses.html",
        courses=student_sections(student["id"]),
    )


@student_bp.route("/analytics")
@role_required("student")
def analytics():
    student = get_current_student()
    analytics_data = student_global_analytics(student["id"])
    overview = analytics_data["overview"]
    
    # Helper to safely extract numeric values with defaults
    def get_metric_value(value, default=0):
        try:
            return float(value) if value is not None else default
        except (ValueError, TypeError):
            return default
    
    # Safely extract all metric values
    assignment_avg = get_metric_value(overview.get("assignment_avg"))
    quiz_avg = get_metric_value(overview.get("quiz_avg"))
    exam_avg = get_metric_value(overview.get("exam_avg"))
    attendance = get_metric_value(overview.get("attendance"))
    
    analytics_data["chart_metrics"] = [
        {
            "label": "Assignments",
            "score": assignment_avg,
            "height": round(assignment_avg * 1.8, 2),
            "gradient": "linear-gradient(180deg, rgba(37, 99, 235, 0.92), rgba(20, 184, 166, 0.82))",
        },
        {
            "label": "Quizzes",
            "score": quiz_avg,
            "height": round(quiz_avg * 1.8, 2),
            "gradient": "linear-gradient(180deg, #8b5cf6, #2563eb)",
        },
        {
            "label": "Exams",
            "score": exam_avg,
            "height": round(exam_avg * 1.8, 2),
            "gradient": "linear-gradient(180deg, #f97316, #ea580c)",
        },
        {
            "label": "Attendance",
            "score": attendance,
            "height": round(attendance * 1.8, 2),
            "gradient": "linear-gradient(180deg, #14b8a6, #0f766e)",
        },
    ]
    analytics_js = {
        "overview": {
            "final_score": overview["final_score"],
        },
        "consistency_score": analytics_data["consistency_score"],
        "momentum_score": analytics_data["momentum_score"],
        "chart_metrics": analytics_data["chart_metrics"],
    }
    return render_template(
        "student/global_analytics.html",
        student=student,
        analytics=analytics_data,
        analytics_json=json.dumps(analytics_js),
    )


@student_bp.route("/course/<int:section_id>")
@role_required("student")
def open_course(section_id):
    return redirect(url_for("course.course_home", section_id=section_id))


@student_bp.route("/calendar")
@role_required("student")
def calendar():
    db = get_db()
    student = get_current_student()
    sections = student_sections(student["id"])
    section_ids = [section["section_id"] for section in sections]

    if section_ids:
        placeholders = ",".join("?" for _ in section_ids)
        events = db.execute(
            f"""
            SELECT
                calendar_events.*,
                courses.course_code,
                sections.section_code
            FROM calendar_events
            LEFT JOIN sections ON calendar_events.section_id = sections.id
            LEFT JOIN courses ON sections.course_id = courses.id
            WHERE calendar_events.section_id IS NULL
               OR calendar_events.section_id IN ({placeholders})
            ORDER BY event_date ASC, title ASC
            """,
            section_ids,
        ).fetchall()
    else:
        events = db.execute(
            """
            SELECT *
            FROM calendar_events
            WHERE section_id IS NULL
            ORDER BY event_date ASC, title ASC
            """
        ).fetchall()

    event_list = [
        {
            "title": event["title"],
            "type": event["event_type"],
            "date": event["event_date"],
            "description": event["description"] or "",
            "course": (
                f'{event["course_code"]} - {event["section_code"]}'
                if event["section_id"] and event["course_code"]
                else "Global"
            ),
            "color": EVENT_TYPE_COLORS.get(event["event_type"], "#16a34a"),
        }
        for event in events
    ]

    return render_template("student/calendar.html", events=json.dumps(event_list))


@student_bp.route("/vehicle", methods=["GET", "POST"])
@role_required("student")
def vehicle():
    db = get_db()
    student = get_current_student()

    if request.method == "POST":
        db.execute(
            """
            INSERT INTO vehicles (student_id, vehicle_reg_no, vehicle_type)
            VALUES (?, ?, ?)
            ON CONFLICT(student_id) DO UPDATE SET
                vehicle_reg_no = excluded.vehicle_reg_no,
                vehicle_type = excluded.vehicle_type,
                status = 'pending',
                approval_note = NULL,
                reviewed_by = NULL,
                reviewed_at = NULL
            """,
            (
                student["id"],
                request.form.get("vehicle_reg_no"),
                request.form.get("vehicle_type"),
            ),
        )
        db.commit()
        return redirect(url_for("student.vehicle"))

    vehicle_record = db.execute(
        "SELECT * FROM vehicles WHERE student_id = ?",
        (student["id"],),
    ).fetchone()

    return render_template("student/vehicle.html", vehicle=vehicle_record)


@student_bp.route("/create_ride", methods=["GET", "POST"])
@role_required("student")
def create_ride():
    db = get_db()
    student = get_current_student()

    vehicle_record = db.execute(
        """
        SELECT *
        FROM vehicles
        WHERE student_id = ? AND status = 'approved'
        """,
        (student["id"],),
    ).fetchone()

    routes = db.execute(
        "SELECT * FROM carpool_routes ORDER BY route_name"
    ).fetchall()

    if request.method == "POST" and vehicle_record:
        total_seats = int(request.form.get("available_seats", "0") or 0)
        db.execute(
            """
            INSERT INTO rides (
                driver_id, route_id, departure_time, available_seats, total_seats, comment
            )
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                student["id"],
                request.form.get("route_id"),
                request.form.get("departure_time"),
                total_seats,
                total_seats,
                request.form.get("comment"),
            ),
        )
        db.commit()
        return redirect(url_for("student.rides"))

    return render_template(
        "student/create_ride.html",
        routes=routes,
        vehicle=vehicle_record,
    )


@student_bp.route("/rides")
@role_required("student")
def rides():
    db = get_db()
    student = get_current_student()

    rides_list = db.execute(
        """
        SELECT
            rides.*,
            carpool_routes.route_name,
            students.full_name AS driver_name,
            vehicles.vehicle_type
        FROM rides
        JOIN carpool_routes ON rides.route_id = carpool_routes.id
        JOIN students ON rides.driver_id = students.id
        LEFT JOIN vehicles ON vehicles.student_id = students.id
        WHERE rides.status = 'open'
        ORDER BY rides.departure_time ASC
        """
    ).fetchall()

    joined_ride_ids = {
        row["ride_id"]
        for row in db.execute(
            """
            SELECT ride_id
            FROM ride_bookings
            WHERE student_id = ? AND status = 'joined'
            """,
            (student["id"],),
        ).fetchall()
    }

    return render_template(
        "student/rides.html",
        rides=rides_list,
        student=student,
        joined_ride_ids=joined_ride_ids,
    )


@student_bp.route("/join_ride/<int:ride_id>", methods=["POST"])
@role_required("student")
def join_ride(ride_id):
    db = get_db()
    student = get_current_student()

    ride = db.execute(
        "SELECT * FROM rides WHERE id = ? AND status = 'open'",
        (ride_id,),
    ).fetchone()

    if not ride:
        return redirect(url_for("student.rides"))

    if ride["driver_id"] == student["id"]:
        return redirect(url_for("student.rides"))

    existing = db.execute(
        """
        SELECT 1
        FROM ride_bookings
        WHERE ride_id = ? AND student_id = ? AND status = 'joined'
        """,
        (ride_id, student["id"]),
    ).fetchone()

    if existing:
        return redirect(url_for("student.rides"))

    updated = db.execute(
        """
        UPDATE rides
        SET available_seats = available_seats - 1
        WHERE id = ? AND available_seats > 0 AND status = 'open'
        """,
        (ride_id,),
    )

    if updated.rowcount:
        db.execute(
            """
            INSERT INTO ride_bookings (ride_id, student_id)
            VALUES (?, ?)
            """,
            (ride_id, student["id"]),
        )
        db.commit()

    return redirect(url_for("student.rides"))


@student_bp.route("/ride/<int:ride_id>/cancel", methods=["POST"])
@role_required("student")
def cancel_ride_booking(ride_id):
    db = get_db()
    student = get_current_student()

    booking = db.execute(
        """
        SELECT *
        FROM ride_bookings
        WHERE ride_id = ? AND student_id = ? AND status = 'joined'
        """,
        (ride_id, student["id"]),
    ).fetchone()

    if booking:
        db.execute(
            """
            UPDATE ride_bookings
            SET status = 'cancelled'
            WHERE id = ?
            """,
            (booking["id"],),
        )
        db.execute(
            """
            UPDATE rides
            SET available_seats = available_seats + 1
            WHERE id = ? AND status = 'open'
            """,
            (ride_id,),
        )
        db.commit()

    return redirect(url_for("student.rides"))


@student_bp.route("/carpool")
@role_required("student")
def carpool_home():
    db = get_db()
    student = get_current_student()

    vehicle_record = db.execute(
        "SELECT * FROM vehicles WHERE student_id = ?",
        (student["id"],),
    ).fetchone()

    open_rides = db.execute(
        """
        SELECT COUNT(*) AS total
        FROM rides
        WHERE status = 'open'
        """
    ).fetchone()["total"]

    return render_template(
        "student/carpool.html",
        vehicle=vehicle_record,
        open_rides=open_rides,
    )
