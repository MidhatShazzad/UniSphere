from models.db import get_db


def student_course_metrics(student_id, section_id, db=None):
    db = db or get_db()
    rows = db.execute(
        """
        SELECT
            assessments.assessment_type,
            grades.score,
            assessments.max_score
        FROM assessments
        LEFT JOIN grades
            ON grades.assessment_id = assessments.id
           AND grades.student_id = ?
        WHERE assessments.section_id = ?
        """,
        (student_id, section_id),
    ).fetchall()

    buckets = {
        "assignment": {"earned": 0, "possible": 0},
        "quiz": {"earned": 0, "possible": 0},
        "exam": {"earned": 0, "possible": 0},
    }

    for row in rows:
        bucket = buckets[row["assessment_type"]]
        bucket["possible"] += row["max_score"] or 0
        bucket["earned"] += row["score"] or 0

    def percentage(bucket_name):
        bucket = buckets[bucket_name]
        if not bucket["possible"]:
            return 0
        return round((bucket["earned"] / bucket["possible"]) * 100, 2)

    assignment_avg = percentage("assignment")
    quiz_avg = percentage("quiz")
    exam_avg = percentage("exam")

    attendance = db.execute(
        """
        SELECT
            SUM(CASE WHEN attendance_records.status = 'present' THEN 1 ELSE 0 END) AS present_count,
            COUNT(*) AS total_count
        FROM attendance_records
        JOIN attendance_sessions ON attendance_records.session_id = attendance_sessions.id
        WHERE attendance_records.student_id = ?
          AND attendance_sessions.section_id = ?
        """,
        (student_id, section_id),
    ).fetchone()

    attendance_pct = 0
    if attendance["total_count"]:
        attendance_pct = round(
            (attendance["present_count"] / attendance["total_count"]) * 100,
            2,
        )

    final_score = round(
        (assignment_avg * 0.3)
        + (quiz_avg * 0.2)
        + (exam_avg * 0.4)
        + (attendance_pct * 0.1),
        2,
    )

    return {
        "assignment_avg": assignment_avg,
        "quiz_avg": quiz_avg,
        "exam_avg": exam_avg,
        "attendance": attendance_pct,
        "final_score": final_score,
    }


def student_global_analytics(student_id, db=None):
    db = db or get_db()

    sections = db.execute(
        """
        SELECT
            sections.id AS section_id,
            sections.section_code,
            sections.term,
            courses.course_code,
            courses.course_title
        FROM enrollments
        JOIN sections ON enrollments.section_id = sections.id
        JOIN courses ON sections.course_id = courses.id
        WHERE enrollments.student_id = ?
          AND enrollments.status = 'enrolled'
        ORDER BY courses.course_code, sections.section_code
        """,
        (student_id,),
    ).fetchall()

    course_breakdown = []
    totals = {
        "assignment_avg": 0,
        "quiz_avg": 0,
        "exam_avg": 0,
        "attendance": 0,
        "final_score": 0,
    }

    for section in sections:
        metrics = student_course_metrics(student_id, section["section_id"], db=db)
        course_breakdown.append(
            {
                "section_id": section["section_id"],
                "course_code": section["course_code"],
                "course_title": section["course_title"],
                "section_code": section["section_code"],
                "term": section["term"],
                **metrics,
            }
        )
        for key in totals:
            totals[key] += metrics[key]

    count = len(course_breakdown) or 1
    overview = {key: round(value / count, 2) for key, value in totals.items()}

    consistency_score = round(
        (overview["attendance"] * 0.45) + (overview["assignment_avg"] * 0.25) + (overview["quiz_avg"] * 0.15) + (overview["exam_avg"] * 0.15),
        2,
    )
    momentum_score = round(
        (overview["final_score"] * 0.7) + (overview["attendance"] * 0.3),
        2,
    )

    focus_pairs = [
        ("Assignments", overview["assignment_avg"]),
        ("Quizzes", overview["quiz_avg"]),
        ("Exams", overview["exam_avg"]),
        ("Attendance", overview["attendance"]),
    ]
    focus_pairs.sort(key=lambda item: item[1])

    priorities = []
    for label, score in focus_pairs[:2]:
        if score < 70:
            priorities.append(f"Prioritize {label.lower()} first. Current performance is {score}%.")
        else:
            priorities.append(f"Maintain momentum in {label.lower()} and push it toward distinction.")

    if overview["exam_avg"] < overview["assignment_avg"]:
        priorities.append("Shift more preparation time toward exam-style revision and timed practice.")
    if overview["attendance"] < 85:
        priorities.append("Attendance is a leverage point right now. Improving it will raise the total score across every course.")

    achievements = []
    if overview["final_score"] >= 85:
        achievements.append("High Achiever")
    if overview["attendance"] >= 90:
        achievements.append("Attendance Anchor")
    if overview["assignment_avg"] >= 85:
        achievements.append("Submission Specialist")
    if not achievements:
        achievements.append("In Progress")

    upcoming = db.execute(
        """
        SELECT
            assessments.title,
            assessments.assessment_type,
            assessments.due_at,
            courses.course_code,
            sections.section_code
        FROM assessments
        JOIN sections ON assessments.section_id = sections.id
        JOIN courses ON sections.course_id = courses.id
        JOIN enrollments ON enrollments.section_id = sections.id
        WHERE enrollments.student_id = ?
          AND enrollments.status = 'enrolled'
          AND assessments.due_at IS NOT NULL
        ORDER BY assessments.due_at ASC
        LIMIT 8
        """,
        (student_id,),
    ).fetchall()

    return {
        "overview": overview,
        "consistency_score": consistency_score,
        "momentum_score": momentum_score,
        "course_breakdown": course_breakdown,
        "priorities": priorities,
        "achievements": achievements,
        "upcoming": upcoming,
    }
