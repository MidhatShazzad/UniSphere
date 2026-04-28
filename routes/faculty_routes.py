from flask import Blueprint, render_template

from models.db import get_db
from utils.decorators import role_required
from utils.helpers import get_current_faculty

faculty_bp = Blueprint("faculty", __name__)


def faculty_sections(faculty_id):
    db = get_db()
    return db.execute(
        """
        SELECT
            sections.id,
            sections.section_code,
            sections.room_no,
            sections.term,
            courses.course_code,
            courses.course_title,
            (
                SELECT COUNT(*)
                FROM enrollments
                WHERE enrollments.section_id = sections.id
                  AND enrollments.status = 'enrolled'
            ) AS student_count
        FROM sections
        JOIN courses ON sections.course_id = courses.id
        WHERE sections.faculty_id = ?
        ORDER BY courses.course_code, sections.section_code
        """,
        (faculty_id,),
    ).fetchall()


@faculty_bp.route("/dashboard")
@role_required("faculty")
def dashboard():
    db = get_db()
    faculty = get_current_faculty()
    sections = faculty_sections(faculty["id"])

    recent_announcements = db.execute(
        """
        SELECT announcements.*, courses.course_code, sections.section_code
        FROM announcements
        JOIN sections ON announcements.section_id = sections.id
        JOIN courses ON sections.course_id = courses.id
        WHERE sections.faculty_id = ?
        ORDER BY announcements.created_at DESC
        LIMIT 6
        """,
        (faculty["id"],),
    ).fetchall()

    return render_template(
        "faculty/dashboard.html",
        faculty=faculty,
        courses=sections,
        recent_announcements=recent_announcements,
    )


@faculty_bp.route("/courses")
@role_required("faculty")
def courses():
    faculty = get_current_faculty()
    return render_template(
        "faculty/courses.html",
        faculty=faculty,
        courses=faculty_sections(faculty["id"]),
    )
