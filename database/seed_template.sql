-- UniSphere seed template for the rebuilt schema.
-- Insert in this order to satisfy foreign keys.

-- 1. Users
-- password_hash can be plain text for development, or a Werkzeug hash string.
INSERT INTO users (username, password_hash, role, is_active) VALUES
    ('student1', 'student1', 'student', 1),
    ('faculty1', 'faculty1', 'faculty', 1),
    ('admin1', 'admin1', 'admin', 1);

-- 2. Student profiles
INSERT INTO students (user_id, student_number, full_name, major, intake_term, bio) VALUES
    (1, '2026001', 'Student One', 'CSE', 'Spring 2026', 'Replace with real student profile');

-- 3. Faculty profiles
INSERT INTO faculty (user_id, faculty_number, full_name, department, office_location) VALUES
    (2, 'F-1001', 'Faculty One', 'CSE', 'Room 402');

-- 4. Courses
INSERT INTO courses (course_code, course_title, description) VALUES
    ('CSE299', 'Junior Design Lab', 'Replace with real course data');

-- 5. Sections
INSERT INTO sections (course_id, faculty_id, section_code, room_no, term) VALUES
    (1, 1, '01', 'LAB-402', 'Spring 2026');

-- 6. Enrollments
INSERT INTO enrollments (student_id, section_id, status) VALUES
    (1, 1, 'enrolled');

-- 7. Optional section content
INSERT INTO announcements (section_id, author_user_id, title, body) VALUES
    (1, 2, 'Welcome', 'Replace with real announcement content');

INSERT INTO assessments (section_id, title, description, assessment_type, due_at, max_score, created_by) VALUES
    (1, 'Assignment 1', 'Replace with real instructions', 'assignment', '2026-05-10 23:59', 100, 2);

INSERT INTO calendar_events (section_id, created_by, title, description, event_type, event_date) VALUES
    (1, 2, 'Quiz 1', 'Replace with actual quiz details', 'quiz', '2026-05-14');

-- 8. Global events
INSERT INTO calendar_events (section_id, created_by, title, description, event_type, event_date) VALUES
    (NULL, 3, 'Semester Break', 'Global academic calendar example', 'holiday', '2026-06-01');

-- 9. Carpool setup
INSERT INTO carpool_routes (route_name, description) VALUES
    ('Campus Loop A', 'Replace with actual route information');

INSERT INTO carpool_stops (route_id, stop_name, stop_order) VALUES
    (1, 'North Gate', 1),
    (1, 'Main Academic Building', 2);

-- 10. Optional vehicle and ride data
INSERT INTO vehicles (student_id, vehicle_reg_no, vehicle_type, status) VALUES
    (1, 'DHK-1234', '4door', 'approved');

INSERT INTO rides (driver_id, route_id, departure_time, available_seats, total_seats, comment, status) VALUES
    (1, 1, '2026-05-01 08:30', 3, 3, 'Morning campus trip', 'open');
