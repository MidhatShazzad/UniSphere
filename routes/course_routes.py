from flask import Blueprint, abort, redirect, render_template, request, url_for

from models.db import get_db
from utils.decorators import role_required
from utils.analytics import student_course_metrics
from utils.helpers import (
    get_current_faculty,
    get_current_student,
    get_current_user,
    get_section,
    user_can_access_section,
)

course_bp = Blueprint("course", __name__)


def enrolled_students(section_id):
    db = get_db()
    return db.execute(
        """
        SELECT
            students.id,
            students.full_name,
            students.student_number
        FROM enrollments
        JOIN students ON enrollments.student_id = students.id
        WHERE enrollments.section_id = ?
          AND enrollments.status = 'enrolled'
        ORDER BY students.full_name
        """,
        (section_id,),
    ).fetchall()


def section_context(section_id):
    db = get_db()
    section = get_section(section_id)
    if not section or not user_can_access_section(section_id):
        abort(404)

    announcements = db.execute(
        """
        SELECT announcements.*, users.username AS author_name
        FROM announcements
        JOIN users ON announcements.author_user_id = users.id
        WHERE announcements.section_id = ?
        ORDER BY announcements.created_at DESC
        """,
        (section_id,),
    ).fetchall()

    materials = db.execute(
        """
        SELECT course_materials.*, users.username AS creator_name
        FROM course_materials
        JOIN users ON course_materials.created_by = users.id
        WHERE course_materials.section_id = ?
        ORDER BY course_materials.created_at DESC
        """,
        (section_id,),
    ).fetchall()

    assessments = db.execute(
        """
        SELECT
            assessments.*,
            (
                SELECT COUNT(*)
                FROM submissions
                WHERE submissions.assessment_id = assessments.id
            ) AS submission_count
        FROM assessments
        WHERE assessments.section_id = ?
        ORDER BY
            CASE assessments.assessment_type
                WHEN 'assignment' THEN 0
                WHEN 'quiz' THEN 1
                ELSE 2
            END,
            assessments.due_at ASC,
            assessments.id DESC
        """,
        (section_id,),
    ).fetchall()

    messages = db.execute(
        """
        SELECT
            messages.*,
            users.username AS sender_name
        FROM messages
        JOIN users ON messages.sender_user_id = users.id
        WHERE messages.section_id = ?
        ORDER BY messages.sent_at DESC
        LIMIT 30
        """,
        (section_id,),
    ).fetchall()

    events = db.execute(
        """
        SELECT *
        FROM calendar_events
        WHERE section_id = ?
        ORDER BY event_date ASC, title ASC
        """,
        (section_id,),
    ).fetchall()

    return {
        "section": section,
        "announcements": announcements,
        "materials": materials,
        "assessments": assessments,
        "messages": messages,
        "events": events,
    }

@course_bp.route("/course/<int:section_id>")
@role_required("student", "faculty", "admin")
def course_home(section_id):
    db = get_db()
    context = section_context(section_id)
    user = get_current_user()

    students = enrolled_students(section_id)
    submissions = []
    submissions_by_assessment = {}
    grades_by_assessment = {}
    metrics = None
    student_grades = []

    if user["role"] == "student":
        student = get_current_student()
        submissions = db.execute(
            """
            SELECT *
            FROM submissions
            WHERE student_id = ?
              AND assessment_id IN (
                  SELECT id FROM assessments WHERE section_id = ?
              )
            """,
            (student["id"], section_id),
        ).fetchall()
        grades = db.execute(
            """
            SELECT grades.*, assessments.title, assessments.assessment_type, assessments.max_score
            FROM grades
            JOIN assessments ON grades.assessment_id = assessments.id
            WHERE grades.student_id = ?
              AND assessments.section_id = ?
            ORDER BY assessments.due_at ASC
            """,
            (student["id"], section_id),
        ).fetchall()
        submissions_by_assessment = {
            submission["assessment_id"]: submission for submission in submissions
        }
        grades_by_assessment = {grade["assessment_id"]: grade for grade in grades}
        metrics = student_course_metrics(student["id"], section_id)
        student_grades = grades

    elif user["role"] in {"faculty", "admin"}:
        grade_rows = db.execute(
            """
            SELECT *
            FROM grades
            WHERE assessment_id IN (
                SELECT id FROM assessments WHERE section_id = ?
            )
            """,
            (section_id,),
        ).fetchall()
        grades_by_assessment = {}
        for grade in grade_rows:
            grades_by_assessment.setdefault(grade["assessment_id"], {})[grade["student_id"]] = grade

        submissions = db.execute(
            """
            SELECT
                submissions.*,
                students.full_name,
                students.student_number,
                assessments.title AS assessment_title
            FROM submissions
            JOIN students ON submissions.student_id = students.id
            JOIN assessments ON submissions.assessment_id = assessments.id
            WHERE assessments.section_id = ?
            ORDER BY submissions.submitted_at DESC
            """,
            (section_id,),
        ).fetchall()

    return render_template(
        "course/course_home.html",
        **context,
        students=students,
        submissions=submissions,
        submissions_by_assessment=submissions_by_assessment,
        grades_by_assessment=grades_by_assessment,
        metrics=metrics,
        student_grades=student_grades,
    )


@course_bp.route("/course/<int:section_id>/announcement/create", methods=["POST"])
@role_required("faculty", "admin")
def create_announcement(section_id):
    if not user_can_access_section(section_id) and get_current_user()["role"] != "admin":
        abort(403)
    db = get_db()
    user = get_current_user()
    db.execute(
        """
        INSERT INTO announcements (section_id, author_user_id, title, body)
        VALUES (?, ?, ?, ?)
        """,
        (
            section_id,
            user["id"],
            request.form.get("title"),
            request.form.get("body"),
        ),
    )
    db.commit()
    return redirect(url_for("course.course_home", section_id=section_id))


@course_bp.route("/course/<int:section_id>/material/create", methods=["POST"])
@role_required("faculty", "admin")
def create_material(section_id):
    if not user_can_access_section(section_id) and get_current_user()["role"] != "admin":
        abort(403)
    db = get_db()
    user = get_current_user()
    db.execute(
        """
        INSERT INTO course_materials (section_id, title, description, file_path, created_by)
        VALUES (?, ?, ?, ?, ?)
        """,
        (
            section_id,
            request.form.get("title"),
            request.form.get("description"),
            request.form.get("file_path"),
            user["id"],
        ),
    )
    db.commit()
    return redirect(url_for("course.course_home", section_id=section_id))


@course_bp.route("/course/<int:section_id>/assessment/create", methods=["POST"])
@role_required("faculty", "admin")
def create_assessment(section_id):
    if not user_can_access_section(section_id) and get_current_user()["role"] != "admin":
        abort(403)
    db = get_db()
    user = get_current_user()
    db.execute(
        """
        INSERT INTO assessments (
            section_id, title, description, assessment_type, due_at, max_score, created_by
        )
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            section_id,
            request.form.get("title"),
            request.form.get("description"),
            request.form.get("assessment_type"),
            request.form.get("due_at"),
            request.form.get("max_score"),
            user["id"],
        ),
    )
    db.commit()
    return redirect(url_for("course.course_home", section_id=section_id))


@course_bp.route("/course/<int:section_id>/assessment/<int:assessment_id>/submit", methods=["POST"])
@role_required("student")
def submit_assignment(section_id, assessment_id):
    db = get_db()
    student = get_current_student()

    if not user_can_access_section(section_id):
        abort(403)

    db.execute(
        """
        INSERT INTO submissions (assessment_id, student_id, file_path, notes)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(assessment_id, student_id) DO UPDATE SET
            file_path = excluded.file_path,
            notes = excluded.notes,
            submitted_at = CURRENT_TIMESTAMP
        """,
        (
            assessment_id,
            student["id"],
            request.form.get("file_path"),
            request.form.get("notes"),
        ),
    )
    db.commit()
    return redirect(url_for("course.course_home", section_id=section_id))


@course_bp.route("/course/<int:section_id>/assessment/<int:assessment_id>/grade", methods=["POST"])
@role_required("faculty", "admin")
def grade_assessment(section_id, assessment_id):
    if not user_can_access_section(section_id) and get_current_user()["role"] != "admin":
        abort(403)

    db = get_db()
    user = get_current_user()
    db.execute(
        """
        INSERT INTO grades (assessment_id, student_id, graded_by, score, feedback)
        VALUES (?, ?, ?, ?, ?)
        ON CONFLICT(assessment_id, student_id) DO UPDATE SET
            graded_by = excluded.graded_by,
            score = excluded.score,
            feedback = excluded.feedback,
            graded_at = CURRENT_TIMESTAMP
        """,
        (
            assessment_id,
            request.form.get("student_id"),
            user["id"],
            request.form.get("score"),
            request.form.get("feedback"),
        ),
    )
    db.commit()
    return redirect(url_for("course.course_home", section_id=section_id))


@course_bp.route("/course/<int:section_id>/message", methods=["POST"])
@role_required("student", "faculty", "admin")
def send_message(section_id):
    if not user_can_access_section(section_id) and get_current_user()["role"] != "admin":
        abort(403)

    db = get_db()
    user = get_current_user()
    db.execute(
        """
        INSERT INTO messages (section_id, sender_user_id, body)
        VALUES (?, ?, ?)
        """,
        (
            section_id,
            user["id"],
            request.form.get("message"),
        ),
    )
    db.commit()
    return redirect(url_for("course.course_home", section_id=section_id))


@course_bp.route("/course/<int:section_id>/calendar/add", methods=["POST"])
@role_required("faculty", "admin")
def add_course_event(section_id):
    if not user_can_access_section(section_id) and get_current_user()["role"] != "admin":
        abort(403)

    db = get_db()
    user = get_current_user()
    db.execute(
        """
        INSERT INTO calendar_events (section_id, created_by, title, description, event_type, event_date)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            section_id,
            user["id"],
            request.form.get("title"),
            request.form.get("description"),
            request.form.get("event_type"),
            request.form.get("event_date"),
        ),
    )
    db.commit()
    return redirect(url_for("course.course_home", section_id=section_id))


@course_bp.route("/course/<int:section_id>/attendance")
@role_required("faculty", "admin")
def attendance_page(section_id):
    if not user_can_access_section(section_id) and get_current_user()["role"] != "admin":
        abort(403)

    db = get_db()
    students = enrolled_students(section_id)
    previous_sessions = db.execute(
        """
        SELECT *
        FROM attendance_sessions
        WHERE section_id = ?
        ORDER BY held_on DESC, id DESC
        LIMIT 10
        """,
        (section_id,),
    ).fetchall()

    return render_template(
        "course/attendance.html",
        students=students,
        section_id=section_id,
        previous_sessions=previous_sessions,
    )


@course_bp.route("/course/<int:section_id>/attendance/submit", methods=["POST"])
@role_required("faculty", "admin")
def submit_attendance(section_id):
    if not user_can_access_section(section_id) and get_current_user()["role"] != "admin":
        abort(403)

    db = get_db()
    user = get_current_user()
    cursor = db.execute(
        """
        INSERT INTO attendance_sessions (section_id, held_on, topic, created_by)
        VALUES (?, ?, ?, ?)
        """,
        (
            section_id,
            request.form.get("held_on"),
            request.form.get("topic"),
            user["id"],
        ),
    )
    session_id = cursor.lastrowid

    for student in enrolled_students(section_id):
        db.execute(
            """
            INSERT INTO attendance_records (session_id, student_id, status)
            VALUES (?, ?, ?)
            """,
            (
                session_id,
                student["id"],
                request.form.get(f"status_{student['id']}", "absent"),
            ),
        )

    db.commit()
    return redirect(url_for("course.attendance_page", section_id=section_id))


@course_bp.route("/course/<int:section_id>/analytics")
@role_required("student", "faculty", "admin")
def course_analytics(section_id):
    if not user_can_access_section(section_id) and get_current_user()["role"] != "admin":
        abort(403)

    db = get_db()
    section = get_section(section_id)
    student = get_current_student()
    faculty = get_current_faculty()

    if student:
        metrics = student_course_metrics(student["id"], section_id)
        return render_template(
            "course/analytics.html",
            section=section,
            metrics=metrics,
            rows=None,
        )

    rows = []
    for enrolled_student in enrolled_students(section_id):
        metrics = student_course_metrics(enrolled_student["id"], section_id)
        rows.append(
            {
                "full_name": enrolled_student["full_name"],
                "student_number": enrolled_student["student_number"],
                "assignment_avg": metrics["assignment_avg"],
                "quiz_avg": metrics["quiz_avg"],
                "exam_avg": metrics["exam_avg"],
                "attendance": metrics["attendance"],
                "final_score": metrics["final_score"],
            }
        )

    return render_template(
        "course/analytics.html",
        section=section,
        metrics=None,
        rows=rows,
        faculty=faculty,
    )
