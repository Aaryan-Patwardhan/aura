#!/usr/bin/env python3
"""
Aura RADIUS Simulator — replays scenario JSON files as HTTP POST events
to the ingestion API, mimicking a Wireless LAN Controller.

Usage:
    python simulator/radius_simulator.py --scenario scenarios/normal_lecture.json
    python simulator/radius_simulator.py --scenario scenarios/bandwidth_fraud.json --speed 10
    python simulator/radius_simulator.py --scenario scenarios/mac_clone_attempt.json --host localhost --port 8000
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import requests

BASE_DIR = Path(__file__).parent


def mb_to_octets(mb: float) -> int:
    return int(mb * 1024 * 1024)


def build_event_sequence(scenario: dict) -> list[dict]:
    """
    Expand a scenario JSON into an ordered list of RADIUS packets.
    Each packet has a 'delay_seconds' field — time to wait before sending.
    """
    lecture = scenario["lecture"]
    students = scenario["students"]
    duration_sec = lecture["duration_minutes"] * 60
    ap_prefix = lecture.get("ap_prefix", "ap-room101")

    events = []
    now = datetime.now(timezone.utc)

    for stu in students:
        username = stu["user_name"]
        mac = stu.get("mac", "00:00:00:00:00:00")
        bytes_dl_mb = stu.get("bytes_dl_mb", 10.0)
        bytes_ul_mb = stu.get("bytes_ul_mb", 1.0)
        late_sec = stu.get("late_seconds", 0)
        integrity_suspect = stu.get("integrity_suspect", False)

        # Per-student AP (alternates north/south for variety, or uses overridden value)
        ap_name = stu.get("called_station_id", f"{ap_prefix}-{'north' if hash(username) % 2 == 0 else 'south'}")

        student_start = now + timedelta(seconds=late_sec)
        student_end = now + timedelta(seconds=duration_sec)
        session_duration = duration_sec - late_sec

        # Accounting-Start
        events.append({
            "delay_seconds": late_sec,
            "packet": {
                "User-Name": username,
                "Acct-Status-Type": "Start",
                "Called-Station-Id": ap_name,
                "Calling-Station-Id": mac,
                "Acct-Input-Octets": 0,
                "Acct-Output-Octets": 0,
                "NAS-IP-Address": "10.0.0.1",
                "Event-Timestamp": student_start.isoformat(),
                "Integrity-Suspect": integrity_suspect,
            },
        })

        # Accounting-Interim-Update (midpoint)
        mid_sec = late_sec + session_duration // 2
        events.append({
            "delay_seconds": mid_sec,
            "packet": {
                "User-Name": username,
                "Acct-Status-Type": "Interim-Update",
                "Called-Station-Id": ap_name,
                "Calling-Station-Id": mac,
                "Acct-Input-Octets": mb_to_octets(bytes_ul_mb * 0.5),
                "Acct-Output-Octets": mb_to_octets(bytes_dl_mb * 0.5),
                "NAS-IP-Address": "10.0.0.1",
                "Event-Timestamp": (now + timedelta(seconds=mid_sec)).isoformat(),
                "Integrity-Suspect": False,
            },
        })

        # Accounting-Stop
        events.append({
            "delay_seconds": duration_sec,
            "packet": {
                "User-Name": username,
                "Acct-Status-Type": "Stop",
                "Called-Station-Id": ap_name,
                "Calling-Station-Id": mac,
                "Acct-Input-Octets": mb_to_octets(bytes_ul_mb),
                "Acct-Output-Octets": mb_to_octets(bytes_dl_mb),
                "Acct-Session-Time": session_duration,
                "NAS-IP-Address": "10.0.0.1",
                "Event-Timestamp": student_end.isoformat(),
                "Integrity-Suspect": False,
            },
        })

    # Sort by delay so events fire in chronological order
    events.sort(key=lambda e: e["delay_seconds"])
    return events


def replay(scenario: dict, base_url: str, speed: float) -> None:
    events = build_event_sequence(scenario)
    total = len(events)
    lecture = scenario["lecture"]

    print(f"\n{'─'*60}")
    print(f"  Aura RADIUS Simulator")
    print(f"  Scenario : {scenario.get('_description', 'N/A')[:80]}")
    print(f"  Course   : {lecture['course_code']}  Room: {lecture['room']}")
    print(f"  Students : {len(scenario['students'])}  Events: {total}  Speed: {speed}×")
    print(f"  Target   : {base_url}")
    print(f"{'─'*60}\n")

    prev_delay = 0.0
    ok = err = 0

    for i, entry in enumerate(events):
        actual_delay = (entry["delay_seconds"] - prev_delay) / speed
        if actual_delay > 0:
            time.sleep(actual_delay)
        prev_delay = entry["delay_seconds"]

        packet = entry["packet"]
        username = packet["User-Name"]
        status_type = packet["Acct-Status-Type"]

        try:
            api_key = os.environ.get("AURA_API_KEY", "dev_secret_key")
            headers = {"X-API-Key": api_key}
            resp = requests.post(f"{base_url}/ingest/radius", json=packet, headers=headers, timeout=10)
            resp.raise_for_status()
            result = resp.json()
            status_label = result.get("status", resp.status_code)
            score = result.get("proxy_risk_score")
            score_str = f"  score={score:.4f}" if score is not None else ""
            print(f"  [{i+1:3}/{total}] {status_type:<20} {username:<20} → {status_label}{score_str}")
            ok += 1
        except requests.RequestException as exc:
            print(f"  [{i+1:3}/{total}] {status_type:<20} {username:<20} → ERROR: {exc}")
            err += 1

    print(f"\n{'─'*60}")
    print(f"  Done. {ok} sent, {err} failed.")
    print(f"{'─'*60}\n")


def main():
    parser = argparse.ArgumentParser(description="Aura RADIUS Simulator")
    parser.add_argument("--scenario", required=True, help="Path to scenario JSON file")
    parser.add_argument("--host", default="localhost", help="Ingestion API host")
    parser.add_argument("--port", type=int, default=8000, help="Ingestion API port")
    parser.add_argument("--speed", type=float, default=60.0,
                        help="Replay speed multiplier (default 60 = 1 min lecture in ~1 sec)")
    args = parser.parse_args()

    scenario_path = Path(args.scenario)
    if not scenario_path.is_absolute():
        scenario_path = BASE_DIR / scenario_path

    if not scenario_path.exists():
        print(f"Scenario file not found: {scenario_path}", file=sys.stderr)
        sys.exit(1)

    with open(scenario_path) as f:
        scenario = json.load(f)

    base_url = f"http://{args.host}:{args.port}"
    replay(scenario, base_url, args.speed)


if __name__ == "__main__":
    main()
