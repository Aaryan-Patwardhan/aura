-- =============================================================
-- Aura Database Schema
-- =============================================================

-- Identity
CREATE TABLE IF NOT EXISTS users (
    id          SERIAL PRIMARY KEY,
    student_id  VARCHAR(20) UNIQUE NOT NULL,   -- institutional username (RADIUS User-Name)
    name        VARCHAR(100),
    email       VARCHAR(120),
    role        VARCHAR(20) DEFAULT 'STUDENT'  -- 'STUDENT', 'FACULTY', 'ADMIN'
);

CREATE TABLE IF NOT EXISTS devices (
    id             SERIAL PRIMARY KEY,
    user_id        INT REFERENCES users(id) ON DELETE CASCADE,
    mac_address    VARCHAR(17),                -- secondary fingerprint only, not primary key
    registered_at  TIMESTAMP DEFAULT NOW(),
    label          VARCHAR(50)                 -- 'personal_phone', 'laptop', etc.
);

-- Physical Infrastructure
CREATE TABLE IF NOT EXISTS rooms (
    id           SERIAL PRIMARY KEY,
    room_number  VARCHAR(20) NOT NULL,
    building     VARCHAR(50),
    capacity     INT
);

CREATE TABLE IF NOT EXISTS access_points (
    ap_name  VARCHAR(50) PRIMARY KEY,          -- matches RADIUS Called-Station-Id
    room_id  INT REFERENCES rooms(id) ON DELETE SET NULL
);

-- Academic Schedule
CREATE TABLE IF NOT EXISTS schedules (
    id                  SERIAL PRIMARY KEY,
    course_code         VARCHAR(20) NOT NULL,
    course_name         VARCHAR(100),
    faculty_id          INT REFERENCES users(id),
    room_id             INT REFERENCES rooms(id),
    start_time          TIME NOT NULL,
    end_time            TIME NOT NULL,
    day_of_week         INT NOT NULL,           -- 0=Monday, 6=Sunday
    min_attendance_pct  INT DEFAULT 75
);

-- Finalized Attendance Records
CREATE TABLE IF NOT EXISTS attendance_sessions (
    id                  SERIAL PRIMARY KEY,
    student_id          INT REFERENCES users(id),
    schedule_id         INT REFERENCES schedules(id),
    date                DATE NOT NULL,
    connect_time        TIMESTAMP,
    disconnect_time     TIMESTAMP,
    minutes_present     INT,
    bytes_downloaded_mb FLOAT,
    bytes_uploaded_mb   FLOAT,
    status              VARCHAR(20),            -- 'PRESENT', 'ABSENT', 'PARTIAL', 'INTEGRITY_SUSPECT'
    proxy_risk_score    FLOAT,                  -- 0.0 to 1.0, Isolation Forest output
    ap_name             VARCHAR(50),
    UNIQUE(student_id, schedule_id, date)
);

-- Indexes for common query patterns
CREATE INDEX IF NOT EXISTS idx_attendance_date         ON attendance_sessions(date);
CREATE INDEX IF NOT EXISTS idx_attendance_student      ON attendance_sessions(student_id);
CREATE INDEX IF NOT EXISTS idx_attendance_schedule     ON attendance_sessions(schedule_id);
CREATE INDEX IF NOT EXISTS idx_attendance_proxy_score  ON attendance_sessions(proxy_risk_score);
CREATE INDEX IF NOT EXISTS idx_devices_user            ON devices(user_id);
CREATE INDEX IF NOT EXISTS idx_schedules_room          ON schedules(room_id);
CREATE INDEX IF NOT EXISTS idx_schedules_day           ON schedules(day_of_week);
