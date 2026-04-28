from flask import session

from models.db import get_db


EVENT_TYPE_COLORS = {
    "quiz": "#f4c430",
    "exam": "#f97316",
    "presentation": "#2563eb",
    "holiday": "#dc2626",
    "general": "#16a34a",
}


def get_current_user():
    username = session.get("user")
    if not username:
        return None
    db = get_db()
    return db.execute(
        "SELECT * FROM users WHERE username = ?",
        (username,),
    ).fetchone()


def get_current_student():
    user = get_current_user()
    if not user:
        return None
    db = get_db()
    return db.execute(
        """
        SELECT students.*, users.username
        FROM students
        JOIN users ON students.user_id = users.id
        WHERE students.user_id = ?
        """,
        (user["id"],),
    ).fetchone()


def get_current_faculty():
    user = get_current_user()
    if not user:
        return None
    db = get_db()
    return db.execute(
        """
        SELECT faculty.*, users.username
        FROM faculty
        JOIN users ON faculty.user_id = users.id
        WHERE faculty.user_id = ?
        """,
        (user["id"],),
    ).fetchone()


def get_section(section_id):
    db = get_db()
    return db.execute(
        """
        SELECT
            sections.*,
            courses.course_code,
            courses.course_title,
            courses.description AS course_description,
            faculty.full_name AS faculty_name
        FROM sections
        JOIN courses ON sections.course_id = courses.id
        LEFT JOIN faculty ON sections.faculty_id = faculty.id
        WHERE sections.id = ?
        """,
        (section_id,),
    ).fetchone()


def user_can_access_section(section_id):
    user = get_current_user()
    if not user:
        return False
    db = get_db()

    if user["role"] == "admin":
        return True

    if user["role"] == "faculty":
        faculty = get_current_faculty()
        if not faculty:
            return False
        row = db.execute(
            "SELECT 1 FROM sections WHERE id = ? AND faculty_id = ?",
            (section_id, faculty["id"]),
        ).fetchone()
        return row is not None

    if user["role"] == "student":
        student = get_current_student()
        if not student:
            return False
        row = db.execute(
            "SELECT 1 FROM enrollments WHERE section_id = ? AND student_id = ? AND status = 'enrolled'",
            (section_id, student["id"]),
        ).fetchone()
        return row is not None

    return False
