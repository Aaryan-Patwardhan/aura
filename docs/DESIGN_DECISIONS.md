# Design Decisions

This document records the explicit rationale for every major architectural choice in Aura. It is addressed to technical reviewers and future maintainers.

---

## 1. RADIUS Over All Other Collection Methods

### Why not QR codes?
A QR code is a piece of image data. It can be screenshotted and transmitted to an absent student in under 10 seconds. There is no cryptographic binding between the QR code and the physical student scanning it. The system is defeated before it is deployed.

### Why not GPS?
GPS check-in requires the student's active cooperation: the app must be running, location permissions must be granted, and mock-location apps (available on both Android and iOS at the OS level) can trivially spoof coordinates to any desired location. Additionally, campus buildings attenuate GPS signals significantly indoors.

### Why not passive MAC sniffing?
Passive probe-request capture (capturing 802.11 management frames without connection) has several fatal problems:
1. **MAC randomization** — iOS 14+ and Android 10+ rotate the MAC address per SSID and per time interval. A sniffed MAC from a probe request cannot be reliably tied to a specific user.
2. **No identity link** — Even a stable MAC address is a device identifier, not a student identifier. An external mapping system (enrollment registration) would be required.
3. **Privacy/legal exposure** — Passive radio capture without authentication is legally murky in several jurisdictions.

### Why RADIUS?
RADIUS Accounting operates at the **authentication layer**, not the application layer. The WLC already runs RADIUS for network access control — it is existing campus infrastructure. The critical property: the `User-Name` in an 802.1X Accounting packet carries the student's **institutional credential**, verified cryptographically by the EAP handshake before the accounting event fires.

A student cannot fake a RADIUS `Accounting-Start` packet without:
1. Physically associating with the AP hardware in the room, **and**
2. Having valid 802.1X credentials

Point 2 is already enforced by the institution's RADIUS/AD infrastructure. The threat model reduces to "student gives their password to someone else," which is a credential-sharing problem, not an attendance-system problem.

---

## 2. `User-Name` as Primary Session Key (Not MAC)

The RADIUS `Called-Station-Id` (MAC address) is explicitly **not** the primary key for session identity. It is stored as a secondary fingerprint only.

**Reason:** MAC randomization. Since iOS 14 and Android 10, devices present a randomized Layer 2 MAC for every SSID association. A system that uses MAC as its identity anchor breaks silently and spectacularly when any student upgrades their phone OS.

The `User-Name` field travels inside the 802.1X/EAP tunnel at Layer 7. It is completely unaffected by what MAC the device presents at Layer 2. This is a fundamental architectural property that makes Aura immune to MAC randomization by design, not by workaround.

---

## 3. Isolation Forest for Focus Score (Not a Fixed Threshold)

### Why not a fixed byte threshold?
A rule like "flag if download > 500MB" fails immediately:
- A 600MB session during a **3-hour lab practical** is completely normal (downloading VM images, datasets).
- The same 600MB during a **45-minute theory lecture** is a strong distraction signal.

The threshold is not a function of bytes alone — it is a function of `(bytes, duration)` jointly. Any fixed rule must be a hardcoded lookup table indexed by course type. That lookup table must be maintained manually and can never generalize to novel course types.

### Why Isolation Forest?
Isolation Forest is an **unsupervised** anomaly detector. This is critical because we have no labeled fraud data — we cannot know in advance which historical sessions were genuinely distracted vs. which were legitimate high-bandwidth use cases.

Isolation Forest learns the normal distribution of `(bytes_dl, bytes_ul, duration)` from historical data and identifies sessions that are statistically difficult to isolate (i.e., anomalous). Contamination parameter = 0.10 sets the prior that ~10% of sessions in the training set are anomalous.

The model outputs a raw decision function score (higher = more normal). We invert and normalize to `[0.0, 1.0]` for the `proxy_risk_score` column.

---

## 4. Redis for Live Session State (Not PostgreSQL)

Every RADIUS `Interim-Update` event is a hash set operation on a single Redis key. Under 500 concurrent student sessions, that is ~500 hash updates per accounting interval (typically every 60–300 seconds from the WLC). 

PostgreSQL writes are ACID-transactional and involve disk I/O. Hash updates in Redis are sub-millisecond in-memory operations. The session state does not need to be durable during the session — it only needs to be finalized to PostgreSQL at `Accounting-Stop`. Redis is the correct tool.

Additionally, Redis pub/sub provides the zero-configuration channel for the finalizer worker to receive stop events without polling.

---

## 5. Separation of Ingestion and Finalization into Two Processes

The ingestion API must respond to RADIUS events in < 100ms (performance target). The finalization path includes:
1. A PostgreSQL join to resolve the matching schedule
2. Duration and threshold arithmetic
3. Isolation Forest inference (joblib model load + numpy forward pass)
4. A PostgreSQL INSERT

These operations are not compatible with a sub-100ms synchronous response path. Separating them into a subscriber worker allows the ingestion API to return immediately after publishing the stop event, while finalization happens asynchronously.

---

## 6. Schedule Matching Logic

When a `Accounting-Stop` event arrives, the finalizer maps the session to a schedule by:
1. Room ID (from the AP → room mapping in `access_points`)
2. Day of week (from the connection timestamp)
3. Time overlap with `±15 minutes` tolerance on the start time

The 15-minute tolerance handles late arrivals and early walk-ins. If no schedule matches, the session is recorded as `UNSCHEDULED` with a null `schedule_id`. This is intentional — not every device connection on campus is a lecture attendance event.

---

## 7. Roadmap Items Not Implemented

See README for detailed roadmap. Items excluded from v1 due to requiring real multi-AP infrastructure data:
- **RSSI Boundary Enforcement** — requires per-room multi-AP fingerprint maps
- **AP Hop Impossibility Detection** — requires building floor-plan spatial graph
- **Doppelgänger Detection** — requires months of correlated RSSI time-series data
- **Behavioral Drift Detection** — requires per-student baseline from weeks of history
