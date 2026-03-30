-- =============================================================
-- Aura Seed Data
-- =============================================================

-- Admin user
INSERT INTO users (student_id, name, email, role) VALUES
('admin001',    'System Admin',         'admin@college.edu',         'ADMIN');

-- Faculty (5)
INSERT INTO users (student_id, name, email, role) VALUES
('fac.sharma',  'Prof. Rajan Sharma',   'r.sharma@college.edu',      'FACULTY'),
('fac.kapoor',  'Prof. Meena Kapoor',   'm.kapoor@college.edu',      'FACULTY'),
('fac.nair',    'Prof. Vijay Nair',     'v.nair@college.edu',        'FACULTY'),
('fac.desai',   'Prof. Priya Desai',    'p.desai@college.edu',       'FACULTY'),
('fac.iyer',    'Prof. Suresh Iyer',    's.iyer@college.edu',        'FACULTY');

-- Students (30) — student_id matches RADIUS User-Name
INSERT INTO users (student_id, name, email, role) VALUES
('stu.arjun01', 'Arjun Mehta',          'arjun.mehta@college.edu',   'STUDENT'),
('stu.priya02', 'Priya Krishnan',        'priya.k@college.edu',       'STUDENT'),
('stu.rahul03', 'Rahul Patel',           'rahul.p@college.edu',       'STUDENT'),
('stu.sneha04', 'Sneha Joshi',           'sneha.j@college.edu',       'STUDENT'),
('stu.amit05',  'Amit Verma',            'amit.v@college.edu',        'STUDENT'),
('stu.divya06', 'Divya Nair',            'divya.n@college.edu',       'STUDENT'),
('stu.karan07', 'Karan Singh',           'karan.s@college.edu',       'STUDENT'),
('stu.anita08', 'Anita Das',             'anita.d@college.edu',       'STUDENT'),
('stu.rohit09', 'Rohit Choudhary',       'rohit.c@college.edu',       'STUDENT'),
('stu.pooja10', 'Pooja Reddy',           'pooja.r@college.edu',       'STUDENT'),
('stu.nikhil11','Nikhil Gupta',          'nikhil.g@college.edu',      'STUDENT'),
('stu.kavya12', 'Kavya Pillai',          'kavya.p@college.edu',       'STUDENT'),
('stu.aakash13','Aakash Tiwari',         'aakash.t@college.edu',      'STUDENT'),
('stu.meera14', 'Meera Shah',            'meera.s@college.edu',       'STUDENT'),
('stu.varun15', 'Varun Bose',            'varun.b@college.edu',       'STUDENT'),
('stu.isha16',  'Isha Malhotra',         'isha.m@college.edu',        'STUDENT'),
('stu.siddh17', 'Siddharth Rao',         'siddh.r@college.edu',       'STUDENT'),
('stu.shruti18','Shruti Agarwal',        'shruti.a@college.edu',      'STUDENT'),
('stu.vivek19', 'Vivek Menon',           'vivek.m@college.edu',       'STUDENT'),
('stu.neha20',  'Neha Saxena',           'neha.s@college.edu',        'STUDENT'),
('stu.sameer21','Sameer Khan',           'sameer.k@college.edu',      'STUDENT'),
('stu.tanvi22', 'Tanvi Bhatt',           'tanvi.b@college.edu',       'STUDENT'),
('stu.harsh23', 'Harsh Pandey',          'harsh.p@college.edu',       'STUDENT'),
('stu.riya24',  'Riya Ghosh',            'riya.g@college.edu',        'STUDENT'),
('stu.ankur25', 'Ankur Sinha',           'ankur.s@college.edu',       'STUDENT'),
('stu.lata26',  'Lata Nambiar',          'lata.n@college.edu',        'STUDENT'),
('stu.dhruv27', 'Dhruv Jain',            'dhruv.j@college.edu',       'STUDENT'),
('stu.sonia28', 'Sonia Chauhan',         'sonia.c@college.edu',       'STUDENT'),
('stu.yash29',  'Yash Dixit',            'yash.d@college.edu',        'STUDENT'),
('stu.maya30',  'Maya Kulkarni',         'maya.k@college.edu',        'STUDENT');

-- Rooms (10)
INSERT INTO rooms (room_number, building, capacity) VALUES
('101', 'Engineering Block A', 60),
('102', 'Engineering Block A', 60),
('201', 'Engineering Block A', 80),
('202', 'Engineering Block A', 80),
('301', 'Engineering Block B', 40),
('302', 'Engineering Block B', 40),
('Lab-1', 'Lab Block',        30),
('Lab-2', 'Lab Block',        30),
('Seminar-1', 'Main Block',   120),
('Seminar-2', 'Main Block',   120);

-- Access Points (20) — ap_name matches RADIUS Called-Station-Id
INSERT INTO access_points (ap_name, room_id) VALUES
('ap-room101-north', 1), ('ap-room101-south', 1),
('ap-room102-north', 2), ('ap-room102-south', 2),
('ap-room201-north', 3), ('ap-room201-south', 3),
('ap-room202-north', 4), ('ap-room202-south', 4),
('ap-room301-main',  5),
('ap-room302-main',  6),
('ap-lab1-east',     7), ('ap-lab1-west',  7),
('ap-lab2-east',     8), ('ap-lab2-west',  8),
('ap-sem1-front',    9), ('ap-sem1-rear',  9),
('ap-sem2-front',   10), ('ap-sem2-rear', 10),
('ap-corridor-a',  NULL),
('ap-corridor-b',  NULL);

-- Schedules (5 courses)
-- faculty_id values: fac.sharma=2, fac.kapoor=3, fac.nair=4, fac.desai=5, fac.iyer=6
-- room_id: 101=1, 102=2, 201=3, 202=4, Lab-1=7
INSERT INTO schedules (course_code, course_name, faculty_id, room_id, start_time, end_time, day_of_week, min_attendance_pct)
SELECT 'CS301', 'Data Structures & Algorithms', u.id, 1, '09:00', '09:50', 1, 75
FROM users u WHERE u.student_id = 'fac.sharma';

INSERT INTO schedules (course_code, course_name, faculty_id, room_id, start_time, end_time, day_of_week, min_attendance_pct)
SELECT 'CS401', 'Operating Systems', u.id, 2, '10:00', '10:50', 1, 75
FROM users u WHERE u.student_id = 'fac.kapoor';

INSERT INTO schedules (course_code, course_name, faculty_id, room_id, start_time, end_time, day_of_week, min_attendance_pct)
SELECT 'CS501', 'Computer Networks', u.id, 3, '11:00', '11:50', 2, 75
FROM users u WHERE u.student_id = 'fac.nair';

INSERT INTO schedules (course_code, course_name, faculty_id, room_id, start_time, end_time, day_of_week, min_attendance_pct)
SELECT 'CS601', 'Machine Learning', u.id, 4, '14:00', '14:50', 3, 75
FROM users u WHERE u.student_id = 'fac.desai';

INSERT INTO schedules (course_code, course_name, faculty_id, room_id, start_time, end_time, day_of_week, min_attendance_pct)
SELECT 'CS701', 'Cloud Computing Lab', u.id, 7, '09:00', '11:50', 4, 75
FROM users u WHERE u.student_id = 'fac.iyer';
