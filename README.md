# Aura — Passive Attendance Intelligence

> *The college Wi-Fi infrastructure becomes the sensor. No student app. No QR codes. No GPS.*

[![Python](https://img.shields.io/badge/Python-3.11+-3776AB?style=flat&logo=python&logoColor=white)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.110+-009688?style=flat&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![Redis](https://img.shields.io/badge/Redis-7.x-DC382D?style=flat&logo=redis&logoColor=white)](https://redis.io)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-15+-4169E1?style=flat&logo=postgresql&logoColor=white)](https://postgresql.org)
[![React](https://img.shields.io/badge/React-18+-61DAFB?style=flat&logo=react&logoColor=white)](https://react.dev)
[![Docker](https://img.shields.io/badge/Docker-Compose-2496ED?style=flat&logo=docker&logoColor=white)](https://docker.com)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

---

## The Problem

Existing attendance systems fail at the infrastructure layer. They all require the student to actively cooperate with the check-in mechanism:

| Method | How it's defeated |
|---|---|
| Manual register | Signed by a friend |
| QR code | Screenshot shared in 10 seconds |
| GPS check-in | Spoofed with a VPN or fake location |
| RFID card | Card handed off to someone else |

None of these systems operate below the application layer. They trust the student to self-report presence and then try to verify it. Aura inverts this entirely.

---

## The Approach

Aura ingests **RADIUS Accounting logs** directly from the college's Wireless LAN Controller — the same infrastructure that already authenticates every device on the campus network. When a student's device associates with the access point inside a lecture room, a `RADIUS Accounting-Start` event fires automatically. When they disconnect or leave range, `Accounting-Stop` fires.

No app install. No check-in button. No student interaction. The network already knows who is where.

The primary session identifier is the **authenticated `User-Name`** (the student's institutional login), not the MAC address. This makes the system immune to MAC randomization — a real-world concern since iOS 14 and Android 10 enabled it by default — because enterprise 802.1X WiFi authentication always carries the credential-verified username in the RADIUS accounting packet regardless of what MAC the device presents.

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     RADIUS Simulator                            │
│   (mimics Wireless LAN Controller — dev/demo environment)      │
│                                                                 │
│  scenarios/normal_lecture.json                                  │
│  scenarios/bandwidth_fraud.json                                 │
│  scenarios/mac_clone_attempt.json                               │
└────────────────────────┬────────────────────────────────────────┘
                         │ UDP Syslog / RADIUS Accounting packets
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│              FastAPI Ingestion Server  (async)                  │
│                                                                 │
│  POST /ingest/radius                                            │
│  Parses: User-Name, MAC, AP-Name, RSSI, Acct-Status-Type,      │
│          Acct-Input-Octets, Acct-Output-Octets                  │
│                                                                 │
│  Dispatches session events → Redis                              │
└────────────────────────┬────────────────────────────────────────┘
                         │
          ┌──────────────┴──────────────┐
          ▼                             ▼
┌──────────────────┐         ┌──────────────────────────────────┐
│  Redis Session   │         │     Session Finalizer Worker      │
│  Manager         │         │                                  │
│                  │         │  Triggered on Accounting-Stop    │
│  Live state per  │────────▶│  Calculates minutes present      │
│  active device:  │         │  Enforces 75% time threshold     │
│                  │         │  Runs Focus Score AI model       │
│  username        │         │  Writes finalized record →       │
│  room_id         │         │  PostgreSQL                      │
│  connect_time    │         └──────────────┬───────────────────┘
│  ap_name         │                        │
│  bytes_in/out    │                        ▼
└──────────────────┘         ┌──────────────────────────────────┐
                             │         PostgreSQL                │
                             │                                  │
                             │  attendance_sessions             │
                             │  proxy_risk_score FLOAT          │
                             │  status: PRESENT/ABSENT/PARTIAL  │
                             └──────────────┬───────────────────┘
                                            │
                                            ▼
                             ┌──────────────────────────────────┐
                             │      React Admin Dashboard       │
                             │                                  │
                             │  Live room occupancy view        │
                             │  Per-student session timeline    │
                             │  AI-flagged sessions with score  │
                             │  CSV export per course           │
                             └──────────────────────────────────┘
```

### Component Breakdown

**RADIUS Simulator** — Ships with three pre-built scenario configs that generate realistic `Accounting-Start`, `Accounting-Stop`, and interim `Accounting-Interim-Update` packets, exactly as a real Cisco/Aruba WLC would emit. This is what makes the entire pipeline demoable on a single machine without real campus infrastructure.

**FastAPI Ingestion Server** — Async endpoint receiving raw RADIUS events. Parses the `User-Name` (primary key), `Called-Station-Id` (AP identifier), `Acct-Status-Type` (Start/Stop/Interim-Update), and byte counters. Dispatches session open/update/close events to Redis with sub-100ms latency.

**Redis Session Manager** — Holds the live state hash for every active device: `{username, room_id, connect_time, ap_name, bytes_in, bytes_out}`. Not a database write on every RADIUS packet — a hash update in memory. Sessions survive API server restarts. This is the component that makes real-time dashboard updates possible.

**Session Finalizer Worker** — A background process triggered on `Accounting-Stop`. Calculates exact minutes present, enforces the 75% minimum threshold (configurable per course), runs the Focus Score model on the session's bandwidth profile, and writes the finalized `attendance_sessions` record to PostgreSQL.

**Isolation Forest (Focus Score)** — The AI layer. See below.

**React Dashboard** — Live room occupancy, session timelines per student, flagged session cards with score breakdown. Role-based: Faculty view (their courses only), Admin view (full campus).

---

## The AI Feature: Focus Score

An **Isolation Forest** anomaly detector trained on three session-level features:

```
features = [bytes_downloaded_mb, bytes_uploaded_mb, session_duration_minutes]
```

Bandwidth consumption during a lecture follows a predictable distribution. A student following slides pulls 5–30MB over 50 minutes. A student streaming video pulls 400–800MB over the same window.

**Why Isolation Forest over a fixed byte threshold:**

A flat "flag if > 500MB" rule fails immediately because a 600MB session during a 3-hour lab practical is completely normal, while the same during a 45-minute theory lecture is a strong distraction signal. The anomaly boundary is *multivariate* — it depends on `(bytes, duration)` jointly. A fixed rule cannot encode this without a hardcoded lookup table per course type. Isolation Forest learns the boundary from training data implicitly, and generalizes across course types without reconfiguration.

The model outputs a `proxy_risk_score` between 0.0 and 1.0. This float is stored in `attendance_sessions.proxy_risk_score` alongside every finalized record, not just flagged ones.

---

## Why RADIUS Over Everything Else

This is the core architectural decision. Documented explicitly here for reviewers.

**QR codes** are spoofable with a screenshot. The check-in mechanism is a piece of image data that can be copied and transmitted instantly. The system is defeated the moment someone takes a screenshot.

**GPS** requires the student's active cooperation (app running, location permission granted), drains battery, and is trivially defeated with a VPN or mock location app. Android and iOS both support fake GPS at the OS level.

**Active MAC sniffing** (passive probe-request capture without authentication) raises serious privacy concerns, is blocked by MAC randomization on modern devices, and cannot reliably identify which specific human is associated with a device without an external mapping system.

**RADIUS** operates at the authentication layer. The WLC already runs it for network access control — it's existing campus infrastructure. The `User-Name` attribute in RADIUS Accounting packets carries the student's institutional credential, verified cryptographically by the 802.1X handshake before the accounting event fires. A student cannot fake this without compromising someone else's credentials, which is a different (and far harder) threat model.

**On MAC randomization specifically:** iOS 14+ and Android 10+ enable MAC randomization by default. This breaks any system that treats MAC as a stable device identifier. Aura's primary session key is `User-Name` from the authenticated RADIUS packet — MAC randomization has zero effect on this, because the randomized MAC is what the device presents at Layer 2, while the credential-verified username travels inside the 802.1X/EAP tunnel at Layer 7.

## Security Warnings

> [!WARNING]
> **Dashboard API Key Exposure (ARCH-7)**: The `VITE_AURA_API_KEY` injected into the React frontend is technically visible within developer tools to any user accessing the browser dashboard. In a true enterprise environment, access should be brokered via a tightly-coupled BFF (Backend For Frontend) managing JWT auth sessions, rather than injecting the raw ingestion key to the browser. The current setup only protects against direct unauthorized API hits off-client.

---

## Database Schema

```sql
-- Identity
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    student_id VARCHAR(20) UNIQUE NOT NULL,  -- institutional username (RADIUS User-Name)
    name VARCHAR(100),
    email VARCHAR(120),
    role VARCHAR(20) DEFAULT 'STUDENT'       -- 'STUDENT', 'FACULTY', 'ADMIN'
);

CREATE TABLE devices (
    id SERIAL PRIMARY KEY,
    user_id INT REFERENCES users(id) ON DELETE CASCADE,
    mac_address VARCHAR(17),                 -- secondary fingerprint only, not primary key
    registered_at TIMESTAMP DEFAULT NOW(),
    label VARCHAR(50)                        -- 'personal_phone', 'laptop', etc.
);

-- Physical Infrastructure
CREATE TABLE rooms (
    id SERIAL PRIMARY KEY,
    room_number VARCHAR(20) NOT NULL,
    building VARCHAR(50),
    capacity INT
);

CREATE TABLE access_points (
    ap_name VARCHAR(50) PRIMARY KEY,         -- matches RADIUS Called-Station-Id
    room_id INT REFERENCES rooms(id) ON DELETE SET NULL
);

-- Academic Schedule
CREATE TABLE schedules (
    id SERIAL PRIMARY KEY,
    course_code VARCHAR(20) NOT NULL,
    course_name VARCHAR(100),
    faculty_id INT REFERENCES users(id),
    room_id INT REFERENCES rooms(id),
    start_time TIME NOT NULL,
    end_time TIME NOT NULL,
    day_of_week INT NOT NULL,               -- 0=Monday, 6=Sunday
    min_attendance_pct INT DEFAULT 75 CHECK (min_attendance_pct BETWEEN 0 AND 100)
);

-- Finalized Records
CREATE TABLE attendance_sessions (
    id SERIAL PRIMARY KEY,
    student_id INT REFERENCES users(id),
    schedule_id INT REFERENCES schedules(id),
    date DATE NOT NULL,
    connect_time TIMESTAMP,
    disconnect_time TIMESTAMP,
    minutes_present INT,
    bytes_downloaded_mb FLOAT,
    bytes_uploaded_mb FLOAT,
    status VARCHAR(20),                     -- 'PRESENT', 'ABSENT', 'PARTIAL', 'INTEGRITY_SUSPECT'
    proxy_risk_score FLOAT,                 -- 0.0 to 1.0, Isolation Forest output
    ap_name VARCHAR(50)
);

CREATE UNIQUE INDEX unique_attendance_session ON attendance_sessions (student_id, date, COALESCE(schedule_id, -1));

-- Indexes for common query patterns
-- ... (see database/schema.sql for indexes)
```

---

## Demo Scenarios

The simulator ships with three pre-built scenarios runnable out of the box:

**`normal_lecture.json`** — 30 students, 50-minute lecture, typical bandwidth (5–25MB each). All sessions finalize as `PRESENT`. Focus scores near 0.

**`bandwidth_fraud.json`** — Same cohort, but 3 students pull 400–700MB during the session. Sessions still finalize as `PRESENT` (they were physically there), but Focus Score spikes > 0.75 and the sessions are flagged on the dashboard.

**`mac_clone_attempt.json`** — A device connects from a different AP than the registered student's typical entry point, with a mismatched `User-Name` / MAC pair. The session is flagged `INTEGRITY_SUSPECT` before it opens.

---

## Repository Structure

```
aura/
├── README.md
├── docker-compose.yml
├── .env.example
│
├── simulator/
│   ├── radius_simulator.py          # RADIUS packet generator
│   ├── radius_parser.py             # Shared packet schema
│   └── scenarios/
│       ├── normal_lecture.json
│       ├── bandwidth_fraud.json
│       └── mac_clone_attempt.json
│
├── ingestion/
│   ├── main.py                      # FastAPI app
│   ├── routers/
│   │   └── radius.py                # /ingest/radius endpoint
│   ├── parsers/
│   │   └── radius_parser.py         # RADIUS attribute extraction
│   └── models/
│       └── session_event.py         # Pydantic models
│
├── session_manager/
│   └── redis_client.py              # Session open/update/close logic
│
├── finalizer/
│   └── session_finalizer.py         # Background worker, threshold enforcement
│
├── ai/
│   ├── focus_score.py               # Isolation Forest inference
│   ├── train_model.py               # Training script
│   └── training_data/
│       └── generate_synthetic_data.py
│
├── database/
│   ├── schema.sql
│   └── seed_data.sql                # Sample users, rooms, schedules
│
├── dashboard/                       # React + Tailwind
│   ├── src/
│   │   ├── pages/
│   │   │   ├── Dashboard.jsx
│   │   │   ├── Sessions.jsx
│   │   │   └── Flagged.jsx
│   │   └── components/
│   │       ├── LiveRoomCard.jsx
│   │       ├── SessionTimeline.jsx
│   │       └── RiskScoreBadge.jsx
│   └── package.json
│
└── docs/
    ├── architecture.png
    ├── DESIGN_DECISIONS.md          # Detailed rationale for every major choice
    ├── RADIUS_PRIMER.md             # What RADIUS is and why it matters here
    └── MAC_RANDOMIZATION.md        # How and why the system handles it
```

---

## Quick Start

```bash
# Clone
git clone https://github.com/Aaryan-Patwardhan/aura
cd aura

# Configure
cp .env.example .env

# Start full stack
docker compose up --build

# In a separate terminal — run a demo scenario
python simulator/radius_simulator.py --scenario simulator/scenarios/bandwidth_fraud.json

# Dashboard
open http://localhost:3000
```

---

## Performance Targets

| Metric | Target | Notes |
|---|---|---|
| Ingestion latency | < 100ms | Per RADIUS event under 500 concurrent sessions |
| Redis session lookup | < 5ms | Hash get/set on session key |
| Session finalization | < 500ms | Includes Isolation Forest inference |
| Dashboard refresh | 5s polling | WebSocket upgrade planned |

---

## Roadmap

Features designed and documented, not yet implemented:

- **RSSI Boundary Enforcement** — Per-room fingerprint map to validate a device is physically inside the room, not in the corridor. Requires multi-AP RSSI vectors.
- **AP Hop Impossibility Detection** — Spatial-temporal constraint graph over building floor plans to detect physically impossible device transitions (MAC cloning indicator).
- **Doppelgänger Detection** — Pearson correlation of RSSI time-series between two devices. Correlation > 0.95 in a dynamic classroom environment indicates co-location (proxy attendance).
- **Behavioral Drift Detection** — Page-Hinkley change-point detection on per-student entry time and AP transition sequences. Flags long-term proxy arrangements.

These features require access to real multi-AP RSSI streams and months of real session data to train meaningfully. They are architected and documented in `docs/DESIGN_DECISIONS.md`.

---

## Tech Stack

| Layer | Technology | Reason |
|---|---|---|
| Backend API | FastAPI (Python) | Async-first, handles concurrent RADIUS event bursts cleanly |
| Session State | Redis | Sub-millisecond hash ops; sessions must survive API restarts |
| Persistent Store | PostgreSQL | Relational schedule-session joins; ACID compliance for records |
| AI | scikit-learn Isolation Forest | Multivariate anomaly detection without labeled fraud data |
| Frontend | React + Tailwind CSS | Component model fits the live-update dashboard pattern |
| Containerization | Docker Compose | Single-command reproducible demo environment |

---

## License

MIT — see [LICENSE](LICENSE)

---

*Built by [Aaryan Patwardhan](https://aaryan.daemonlabs.systems) · [DaemonCorp](https://daemonlabs.systems)*
