from pathlib import Path


OUTPUT_PATH = Path(__file__).with_name("dev_seed.sql")
PASSWORD = "unisphere"


students = [
    {"username": "MidhatShazzad", "student_number": "2210001", "full_name": "Midhat Shazzad", "major": "CSE"},
    {"username": "ArebiSarker", "student_number": "2210002", "full_name": "Arebi Sarker", "major": "CSE"},
    {"username": "AryanSami", "student_number": "2210003", "full_name": "Aryan Sami", "major": "CSE"},
]

faculty = [
    {"username": "ITN", "faculty_number": "ITN", "full_name": "Faculty ITN", "department": "CSE"},
    {"username": "SFM1", "faculty_number": "SFM1", "full_name": "Faculty SFM1", "department": "CSE"},
    {"username": "SFA", "faculty_number": "SFA", "full_name": "Faculty SFA", "department": "CSE"},
    {"username": "MSRB", "faculty_number": "MSRB", "full_name": "Faculty MSRB", "department": "Mathematics"},
    {"username": "SMSL", "faculty_number": "SMSL", "full_name": "Faculty SMSL", "department": "Language Studies"},
]

courses = [
    ("CSE115", "Intro to Programming", 25),
    ("CSE299", "Junior Design Lab", 12),
    ("CSE323", "Operating System Design", 9),
    ("CSE327", "Software Engineering", 8),
    ("CSE468", "Computer Vision", 6),
    ("CSE499", "Senior Design Lab", 5),
    ("ENG111", "Public Speaking", 20),
    ("ENG115", "Intro to Literature", 18),
    ("MAT16", "PreCalculus", 20),
    ("MAT120", "Calculus 1", 18),
    ("MAT250", "Calculus 3", 12),
    ("MAT350", "Engineering Mathematics", 8),
    ("MAT361", "Probability and Statistics", 7),
]

student_section_map = {
    "MidhatShazzad": ["CSE115-03", "ENG111-02", "MAT120-04", "CSE299-01", "CSE323-01", "CSE327-02", "CSE499-01"],
    "ArebiSarker": ["CSE115-05", "ENG115-01", "MAT16-02", "MAT120-06", "CSE299-02", "CSE327-01", "MAT361-01"],
    "AryanSami": ["CSE115-01", "ENG111-04", "MAT16-05", "MAT250-01", "MAT350-01", "CSE323-02", "CSE468-01"],
}


def sql(value):
    if value is None:
        return "NULL"
    if isinstance(value, (int, float)):
        return str(value)
    text = str(value).replace("'", "''")
    return f"'{text}'"


def section_room(index):
    prefix = "SAC" if index % 2 == 0 else "NAC"
    number = 10 + (index % 90)
    return f"{prefix}-{number}"


def main():
    lines = []
    lines.append("DELETE FROM ride_bookings;")
    lines.append("DELETE FROM rides;")
    lines.append("DELETE FROM vehicles;")
    lines.append("DELETE FROM carpool_stops;")
    lines.append("DELETE FROM carpool_routes;")
    lines.append("DELETE FROM calendar_events;")
    lines.append("DELETE FROM messages;")
    lines.append("DELETE FROM attendance_records;")
    lines.append("DELETE FROM attendance_sessions;")
    lines.append("DELETE FROM grades;")
    lines.append("DELETE FROM submissions;")
    lines.append("DELETE FROM assessments;")
    lines.append("DELETE FROM course_materials;")
    lines.append("DELETE FROM announcements;")
    lines.append("DELETE FROM enrollments;")
    lines.append("DELETE FROM sections;")
    lines.append("DELETE FROM courses;")
    lines.append("DELETE FROM faculty;")
    lines.append("DELETE FROM students;")
    lines.append("DELETE FROM users;")
    lines.append("DELETE FROM sqlite_sequence;")
    lines.append("")

    user_rows = []
    user_id = 1
    student_user_ids = {}
    faculty_user_ids = {}
    for student in students:
        student_user_ids[student["username"]] = user_id
        user_rows.append((user_id, student["username"], PASSWORD, "student", 1))
        user_id += 1
    for member in faculty:
        faculty_user_ids[member["username"]] = user_id
        user_rows.append((user_id, member["username"], PASSWORD, "faculty", 1))
        user_id += 1
    admin_id = user_id
    user_rows.append((admin_id, "admin1", PASSWORD, "admin", 1))

    lines.append("INSERT INTO users (id, username, password_hash, role, is_active) VALUES")
    lines.extend(
        [
            "    (" + ", ".join(sql(value) for value in row) + ")" + ("," if i < len(user_rows) - 1 else ";")
            for i, row in enumerate(user_rows)
        ]
    )
    lines.append("")

    student_rows = []
    for index, student in enumerate(students, start=1):
        student_rows.append(
            (
                index,
                student_user_ids[student["username"]],
                student["student_number"],
                student["full_name"],
                student["major"],
                "Spring 2026",
                f"{student['full_name']} is enrolled in the UniSphere demo environment.",
            )
        )
    lines.append("INSERT INTO students (id, user_id, student_number, full_name, major, intake_term, bio) VALUES")
    lines.extend(
        [
            "    (" + ", ".join(sql(value) for value in row) + ")" + ("," if i < len(student_rows) - 1 else ";")
            for i, row in enumerate(student_rows)
        ]
    )
    lines.append("")

    faculty_rows = []
    for index, member in enumerate(faculty, start=1):
        faculty_rows.append(
            (
                index,
                faculty_user_ids[member["username"]],
                member["faculty_number"],
                member["full_name"],
                member["department"],
                section_room(30 + index),
            )
        )
    lines.append("INSERT INTO faculty (id, user_id, faculty_number, full_name, department, office_location) VALUES")
    lines.extend(
        [
            "    (" + ", ".join(sql(value) for value in row) + ")" + ("," if i < len(faculty_rows) - 1 else ";")
            for i, row in enumerate(faculty_rows)
        ]
    )
    lines.append("")

    course_rows = [(index, code, title, f"{title} course provisioned for the UniSphere project demo.") for index, (code, title, _count) in enumerate(courses, start=1)]
    lines.append("INSERT INTO courses (id, course_code, course_title, description) VALUES")
    lines.extend(
        [
            "    (" + ", ".join(sql(value) for value in row) + ")" + ("," if i < len(course_rows) - 1 else ";")
            for i, row in enumerate(course_rows)
        ]
    )
    lines.append("")

    section_rows = []
    section_lookup = {}
    section_id = 1
    for course_index, (course_code, _title, count) in enumerate(courses, start=1):
        for section_number in range(1, count + 1):
            label = f"{section_number:02d}"
            section_lookup[f"{course_code}-{label}"] = section_id
            faculty_id = ((section_number + course_index - 2) % len(faculty)) + 1
            section_rows.append(
                (
                    section_id,
                    course_index,
                    faculty_id,
                    label,
                    section_room(section_id),
                    "Spring 2026",
                )
            )
            section_id += 1
    lines.append("INSERT INTO sections (id, course_id, faculty_id, section_code, room_no, term) VALUES")
    lines.extend(
        [
            "    (" + ", ".join(sql(value) for value in row) + ")" + ("," if i < len(section_rows) - 1 else ";")
            for i, row in enumerate(section_rows)
        ]
    )
    lines.append("")

    enrollment_rows = []
    for student_index, student in enumerate(students, start=1):
        for key in student_section_map[student["username"]]:
            enrollment_rows.append((student_index, section_lookup[key], "enrolled"))
    lines.append("INSERT INTO enrollments (student_id, section_id, status) VALUES")
    lines.extend(
        [
            "    (" + ", ".join(sql(value) for value in row) + ")" + ("," if i < len(enrollment_rows) - 1 else ";")
            for i, row in enumerate(enrollment_rows)
        ]
    )
    lines.append("")

    announcement_rows = [
        (None, admin_id, "Semester Launch", "Welcome to the UniSphere Spring 2026 environment.", "2026-04-25 09:00:00")
    ]
    material_rows = []
    assessment_rows = []
    event_rows = [(None, admin_id, "University Innovation Week", "Cross-campus showcase and activity week.", "general", "2026-05-20")]
    attendance_session_rows = []
    attendance_record_rows = []
    submission_rows = []
    grade_rows = []
    message_rows = []

    assessment_id = 1
    session_id = 1
    ride_id = 1

    enrolled_by_section = {}
    for student_index, student in enumerate(students, start=1):
        for key in student_section_map[student["username"]]:
            enrolled_by_section.setdefault(section_lookup[key], []).append(student_index)

    for row in section_rows:
        current_section_id, course_id, faculty_id, label, _room, _term = row
        course_code = courses[course_id - 1][0]
        course_title = courses[course_id - 1][1]

        announcement_rows.append(
            (
                current_section_id,
                faculty_user_ids[faculty[faculty_id - 1]["username"]],
                f"{course_code} Section {label} Update",
                f"Stay aligned on weekly priorities and section milestones for {course_title}.",
                f"2026-04-{26 + (current_section_id % 2):02d} 10:00:00",
            )
        )
        material_rows.append(
            (
                current_section_id,
                f"{course_code} Launch Brief",
                f"Core starter resource pack for {course_code} Section {label}.",
                f"/materials/{course_code.lower()}_{label}_brief.pdf",
                faculty_user_ids[faculty[faculty_id - 1]["username"]],
                f"2026-04-{26 + (current_section_id % 2):02d} 11:00:00",
            )
        )
        for kind, max_score, offset in [("assignment", 100, 5), ("quiz", 20, 8), ("exam", 100, 14)]:
            title = f"{course_code} {kind.title()} {label}"
            assessment_rows.append(
                (
                    assessment_id,
                    current_section_id,
                    title,
                    f"{kind.title()} assessment for {course_code} Section {label}.",
                    kind,
                    f"2026-05-{offset + (current_section_id % 5):02d} 11:00",
                    max_score,
                    faculty_user_ids[faculty[faculty_id - 1]["username"]],
                    f"2026-04-{26 + (current_section_id % 2):02d} 12:00:00",
                )
            )
            for student_index in enrolled_by_section.get(current_section_id, []):
                if kind == "assignment":
                    submission_rows.append(
                        (
                            assessment_id,
                            student_index,
                            f"/submissions/{students[student_index - 1]['username'].lower()}_{course_code.lower()}_{label}_{kind}.pdf",
                            f"Submitted for {course_code} {kind}.",
                            f"2026-04-27 1{student_index}:00:00",
                        )
                    )
                base = 70 + ((student_index * 7 + current_section_id * 3 + assessment_id) % 25)
                if kind == "quiz":
                    score = round((base / 100) * 20, 2)
                else:
                    score = float(base)
                grade_rows.append(
                    (
                        assessment_id,
                        student_index,
                        faculty_user_ids[faculty[faculty_id - 1]["username"]],
                        score,
                        f"Performance feedback for {course_code} {kind}.",
                        f"2026-04-28 1{student_index}:30:00",
                    )
                )
            assessment_id += 1

        event_type = "quiz" if current_section_id % 3 == 0 else "presentation" if current_section_id % 3 == 1 else "exam"
        event_rows.append(
            (
                current_section_id,
                faculty_user_ids[faculty[faculty_id - 1]["username"]],
                f"{course_code} Milestone {label}",
                f"Scheduled {event_type} checkpoint for {course_code} Section {label}.",
                event_type,
                f"2026-05-{3 + (current_section_id % 20):02d}",
            )
        )

        if current_section_id in enrolled_by_section:
            attendance_session_rows.append((session_id, current_section_id, "2026-04-24", f"{course_code} kickoff", faculty_user_ids[faculty[faculty_id - 1]["username"]]))
            attendance_session_rows.append((session_id + 1, current_section_id, "2026-04-26", f"{course_code} guided work", faculty_user_ids[faculty[faculty_id - 1]["username"]]))
            for student_index in enrolled_by_section[current_section_id]:
                attendance_record_rows.append((session_id, student_index, "present"))
                status = "present" if (student_index + current_section_id) % 3 else "absent"
                attendance_record_rows.append((session_id + 1, student_index, status))
                message_rows.append(
                    (
                        current_section_id,
                        student_user_ids[students[student_index - 1]["username"]],
                        None,
                        f"Checking in on the current priorities for {course_code} Section {label}.",
                        f"2026-04-27 1{student_index}:15:00",
                    )
                )
            session_id += 2

    def insert_block(statement, rows):
        lines.append(statement)
        lines.extend(
            [
                "    (" + ", ".join(sql(value) for value in row) + ")" + ("," if i < len(rows) - 1 else ";")
                for i, row in enumerate(rows)
            ]
        )
        lines.append("")

    insert_block(
        "INSERT INTO announcements (section_id, author_user_id, title, body, created_at) VALUES",
        announcement_rows,
    )
    insert_block(
        "INSERT INTO course_materials (section_id, title, description, file_path, created_by, created_at) VALUES",
        material_rows,
    )
    insert_block(
        "INSERT INTO assessments (id, section_id, title, description, assessment_type, due_at, max_score, created_by, created_at) VALUES",
        assessment_rows,
    )
    insert_block(
        "INSERT INTO submissions (assessment_id, student_id, file_path, notes, submitted_at) VALUES",
        submission_rows,
    )
    insert_block(
        "INSERT INTO grades (assessment_id, student_id, graded_by, score, feedback, graded_at) VALUES",
        grade_rows,
    )
    insert_block(
        "INSERT INTO attendance_sessions (id, section_id, held_on, topic, created_by) VALUES",
        attendance_session_rows,
    )
    insert_block(
        "INSERT INTO attendance_records (session_id, student_id, status) VALUES",
        attendance_record_rows,
    )
    insert_block(
        "INSERT INTO messages (section_id, sender_user_id, recipient_user_id, body, sent_at) VALUES",
        message_rows,
    )
    insert_block(
        "INSERT INTO calendar_events (section_id, created_by, title, description, event_type, event_date) VALUES",
        event_rows,
    )

    route_rows = [
        (1, "NAC Express", "Northern academic corridor to campus"),
        (2, "SAC Loop", "Southern residential and activity corridor"),
        (3, "City Connector", "City-side pickup route feeding into campus"),
    ]
    insert_block(
        "INSERT INTO carpool_routes (id, route_name, description) VALUES",
        route_rows,
    )
    stop_rows = [
        (1, "North Gate", 1),
        (1, "NAC-24", 2),
        (1, "Main Academic Building", 3),
        (2, "South Hub", 1),
        (2, "SAC-18", 2),
        (2, "Library Plaza", 3),
        (3, "City Junction", 1),
        (3, "NAC-41", 2),
        (3, "Innovation Block", 3),
    ]
    insert_block(
        "INSERT INTO carpool_stops (route_id, stop_name, stop_order) VALUES",
        stop_rows,
    )

    vehicle_rows = [
        (1, "DHK-2201", "4door", "approved", "Approved for demo driver access.", "2026-04-26 09:00:00", admin_id, "2026-04-26 11:00:00"),
        (2, "DHK-2202", "motorcycle", "pending", "Awaiting admin review.", "2026-04-27 14:00:00", None, None),
        (3, "DHK-2203", "microbus", "approved", "Approved for route demonstrations.", "2026-04-27 15:00:00", admin_id, "2026-04-27 17:00:00"),
    ]
    insert_block(
        "INSERT INTO vehicles (student_id, vehicle_reg_no, vehicle_type, status, approval_note, created_at, reviewed_by, reviewed_at) VALUES",
        vehicle_rows,
    )
    ride_rows = [
        (1, 1, 1, "2026-04-29 08:15", 2, 3, "Morning route for the first lab block.", "open"),
        (2, 3, 2, "2026-04-29 16:40", 5, 6, "Return trip after afternoon classes.", "open"),
        (3, 1, 3, "2026-04-30 09:10", 3, 4, "Flexible pickup across the city connector.", "open"),
    ]
    insert_block(
        "INSERT INTO rides (id, driver_id, route_id, departure_time, available_seats, total_seats, comment, status) VALUES",
        ride_rows,
    )
    booking_rows = [
        (1, 2, "2026-04-27 19:00:00", "joined"),
        (2, 1, "2026-04-27 19:25:00", "joined"),
    ]
    insert_block(
        "INSERT INTO ride_bookings (ride_id, student_id, booked_at, status) VALUES",
        booking_rows,
    )

    OUTPUT_PATH.write_text("\n".join(lines), encoding="utf-8")
    print(f"Wrote {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
