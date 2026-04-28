from flask import Blueprint, redirect, render_template, request, url_for

from models.db import get_db
from utils.decorators import role_required
from utils.helpers import get_current_user

admin_bp = Blueprint("admin", __name__)


@admin_bp.route("/dashboard")
@role_required("admin")
def dashboard():
    db = get_db()

    summary = {
        "users": db.execute("SELECT COUNT(*) AS total FROM users").fetchone()["total"],
        "students": db.execute("SELECT COUNT(*) AS total FROM students").fetchone()["total"],
        "faculty": db.execute("SELECT COUNT(*) AS total FROM faculty").fetchone()["total"],
        "courses": db.execute("SELECT COUNT(*) AS total FROM courses").fetchone()["total"],
        "sections": db.execute("SELECT COUNT(*) AS total FROM sections").fetchone()["total"],
        "pending_vehicles": db.execute(
            "SELECT COUNT(*) AS total FROM vehicles WHERE status = 'pending'"
        ).fetchone()["total"],
    }

    recent_sections = db.execute(
        """
        SELECT
            sections.id,
            courses.course_code,
            courses.course_title,
            sections.section_code,
            sections.term,
            faculty.full_name AS faculty_name
        FROM sections
        JOIN courses ON sections.course_id = courses.id
        LEFT JOIN faculty ON sections.faculty_id = faculty.id
        ORDER BY sections.id DESC
        LIMIT 8
        """
    ).fetchall()

    global_announcements = db.execute(
        """
        SELECT announcements.*, users.username AS author_name
        FROM announcements
        JOIN users ON announcements.author_user_id = users.id
        WHERE announcements.section_id IS NULL
        ORDER BY announcements.created_at DESC
        LIMIT 6
        """
    ).fetchall()

    return render_template(
        "admin/dashboard.html",
        summary=summary,
        recent_sections=recent_sections,
        global_announcements=global_announcements,
    )


@admin_bp.route("/announcements/create", methods=["POST"])
@role_required("admin")
def create_global_announcement():
    db = get_db()
    admin_user = get_current_user()
    db.execute(
        """
        INSERT INTO announcements (section_id, author_user_id, title, body)
        VALUES (NULL, ?, ?, ?)
        """,
        (
            admin_user["id"],
            request.form.get("title"),
            request.form.get("body"),
        ),
    )
    db.commit()
    return redirect(url_for("admin.dashboard"))


@admin_bp.route("/users")
@role_required("admin")
def users():
    db = get_db()
    users_list = db.execute(
        """
        SELECT
            users.*,
            COALESCE(students.full_name, faculty.full_name, users.username) AS display_name,
            students.student_number,
            faculty.faculty_number,
            faculty.department
        FROM users
        LEFT JOIN students ON students.user_id = users.id
        LEFT JOIN faculty ON faculty.user_id = users.id
        ORDER BY users.role, users.username
        """
    ).fetchall()
    return render_template("admin/users.html", users=users_list)


@admin_bp.route("/users/<int:user_id>/toggle-active", methods=["POST"])
@role_required("admin")
def toggle_user_active(user_id):
    db = get_db()
    db.execute(
        """
        UPDATE users
        SET is_active = CASE WHEN is_active = 1 THEN 0 ELSE 1 END
        WHERE id = ?
        """,
        (user_id,),
    )
    db.commit()
    return redirect(url_for("admin.users"))


@admin_bp.route("/users/<int:user_id>/reset-password", methods=["POST"])
@role_required("admin")
def reset_user_password(user_id):
    db = get_db()
    user = db.execute("SELECT username FROM users WHERE id = ?", (user_id,)).fetchone()
    if user:
        db.execute(
            """
            UPDATE users
            SET password_hash = ?, force_password_reset = 1
            WHERE id = ?
            """,
            (user["username"], user_id),
        )
        db.commit()
    return redirect(url_for("admin.users"))


@admin_bp.route("/courses", methods=["GET", "POST"])
@role_required("admin")
def courses():
    db = get_db()

    if request.method == "POST":
        form_type = request.form.get("form_type")

        if form_type == "create_section":
            course_id = request.form.get("course_id")
            if not course_id:
                cursor = db.execute(
                    """
                    INSERT INTO courses (course_code, course_title, description)
                    VALUES (?, ?, ?)
                    """,
                    (
                        request.form.get("course_code"),
                        request.form.get("course_title"),
                        request.form.get("description"),
                    ),
                )
                course_id = cursor.lastrowid

            db.execute(
                """
                INSERT INTO sections (course_id, faculty_id, section_code, room_no, term)
                VALUES (?, NULLIF(?, ''), ?, ?, ?)
                """,
                (
                    course_id,
                    request.form.get("faculty_id"),
                    request.form.get("section_code"),
                    request.form.get("room_no"),
                    request.form.get("term"),
                ),
            )

        elif form_type == "enroll_student":
            db.execute(
                """
                INSERT INTO enrollments (student_id, section_id, status)
                VALUES (?, ?, 'enrolled')
                ON CONFLICT(student_id, section_id) DO UPDATE SET status = 'enrolled'
                """,
                (
                    request.form.get("student_id"),
                    request.form.get("section_id"),
                ),
            )

        elif form_type == "drop_student":
            db.execute(
                """
                UPDATE enrollments
                SET status = 'dropped'
                WHERE student_id = ? AND section_id = ?
                """,
                (
                    request.form.get("student_id"),
                    request.form.get("section_id"),
                ),
            )

        elif form_type == "update_section":
            db.execute(
                """
                UPDATE sections
                SET faculty_id = NULLIF(?, ''),
                    room_no = ?,
                    term = ?
                WHERE id = ?
                """,
                (
                    request.form.get("faculty_id"),
                    request.form.get("room_no"),
                    request.form.get("term"),
                    request.form.get("section_id"),
                ),
            )

        elif form_type == "create_global_event":
            admin_user = get_current_user()
            db.execute(
                """
                INSERT INTO calendar_events (section_id, created_by, title, description, event_type, event_date)
                VALUES (NULL, ?, ?, ?, ?, ?)
                """,
                (
                    admin_user["id"],
                    request.form.get("title"),
                    request.form.get("description"),
                    request.form.get("event_type"),
                    request.form.get("event_date"),
                ),
            )

        db.commit()
        return redirect(url_for("admin.courses"))

    courses_list = db.execute(
        """
        SELECT
            sections.id AS section_id,
            sections.section_code,
            sections.room_no,
            sections.term,
            courses.course_code,
            courses.course_title,
            faculty.full_name AS faculty_name,
            (
                SELECT COUNT(*)
                FROM enrollments
                WHERE enrollments.section_id = sections.id
                  AND enrollments.status = 'enrolled'
            ) AS student_count
        FROM sections
        JOIN courses ON sections.course_id = courses.id
        LEFT JOIN faculty ON sections.faculty_id = faculty.id
        ORDER BY courses.course_code, sections.section_code
        """
    ).fetchall()

    base_courses = db.execute(
        "SELECT * FROM courses ORDER BY course_code"
    ).fetchall()
    faculty_list = db.execute(
        "SELECT id, full_name, faculty_number FROM faculty ORDER BY full_name"
    ).fetchall()
    student_list = db.execute(
        "SELECT id, full_name, student_number FROM students ORDER BY full_name"
    ).fetchall()
    enrollments = db.execute(
        """
        SELECT
            enrollments.student_id,
            enrollments.section_id,
            enrollments.status,
            students.full_name,
            students.student_number,
            courses.course_code,
            sections.section_code
        FROM enrollments
        JOIN students ON enrollments.student_id = students.id
        JOIN sections ON enrollments.section_id = sections.id
        JOIN courses ON sections.course_id = courses.id
        ORDER BY students.full_name, courses.course_code
        """
    ).fetchall()
    global_events = db.execute(
        """
        SELECT *
        FROM calendar_events
        WHERE section_id IS NULL
        ORDER BY event_date DESC
        """
    ).fetchall()

    return render_template(
        "admin/courses.html",
        courses=courses_list,
        base_courses=base_courses,
        faculty_list=faculty_list,
        student_list=student_list,
        enrollments=enrollments,
        global_events=global_events,
    )


@admin_bp.route("/routes", methods=["GET", "POST"])
@role_required("admin")
def routes():
    db = get_db()

    if request.method == "POST":
        form_type = request.form.get("form_type")

        if form_type == "create_route":
            db.execute(
                """
                INSERT INTO carpool_routes (route_name, description)
                VALUES (?, ?)
                """,
                (
                    request.form.get("route_name"),
                    request.form.get("description"),
                ),
            )
        elif form_type == "add_stop":
            db.execute(
                """
                INSERT INTO carpool_stops (route_id, stop_name, stop_order)
                VALUES (?, ?, ?)
                """,
                (
                    request.form.get("route_id"),
                    request.form.get("stop_name"),
                    request.form.get("stop_order"),
                ),
            )

        db.commit()
        return redirect(url_for("admin.routes"))

    routes_list = db.execute(
        "SELECT * FROM carpool_routes ORDER BY route_name"
    ).fetchall()
    stops = db.execute(
        """
        SELECT carpool_stops.*, carpool_routes.route_name
        FROM carpool_stops
        JOIN carpool_routes ON carpool_stops.route_id = carpool_routes.id
        ORDER BY carpool_routes.route_name, stop_order
        """
    ).fetchall()
    return render_template("admin/routes.html", routes=routes_list, stops=stops)


@admin_bp.route("/vehicles")
@role_required("admin")
def vehicles():
    db = get_db()
    vehicles_list = db.execute(
        """
        SELECT
            vehicles.*,
            students.full_name,
            students.student_number,
            users.username
        FROM vehicles
        JOIN students ON vehicles.student_id = students.id
        JOIN users ON students.user_id = users.id
        ORDER BY
            CASE vehicles.status
                WHEN 'pending' THEN 0
                WHEN 'approved' THEN 1
                ELSE 2
            END,
            vehicles.created_at DESC
        """
    ).fetchall()
    return render_template("admin/vehicles.html", vehicles=vehicles_list)


@admin_bp.route("/vehicles/<int:vehicle_id>/review", methods=["POST"])
@role_required("admin")
def review_vehicle(vehicle_id):
    db = get_db()
    admin_user = get_current_user()
    db.execute(
        """
        UPDATE vehicles
        SET status = ?,
            approval_note = ?,
            reviewed_by = ?,
            reviewed_at = CURRENT_TIMESTAMP
        WHERE id = ?
        """,
        (
            request.form.get("status"),
            request.form.get("approval_note"),
            admin_user["id"],
            vehicle_id,
        ),
    )
    db.commit()
    return redirect(url_for("admin.vehicles"))
