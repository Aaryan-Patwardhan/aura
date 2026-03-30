"""
RADIUS attribute extraction and normalization.
"""
from __future__ import annotations

import re
from typing import Optional

from ingestion.models.session_event import RadiusEvent


# RADIUS Called-Station-Id can contain BSSID:AP-name format (Cisco/Aruba convention)
# e.g. "00:11:22:33:44:55:ap-room101-north"  or just "ap-room101-north"
_CALLED_STATION_RE = re.compile(r"(?:[0-9a-fA-F]{2}:){5}[0-9a-fA-F]{2}:(.+)$")


def normalize_ap_name(called_station_id: str) -> str:
    """
    Extract the human-readable AP name from Called-Station-Id.
    Handles both bare names and BSSID-prefixed names.
    """
    match = _CALLED_STATION_RE.match(called_station_id.strip())
    if match:
        return match.group(1).strip()
    return called_station_id.strip()


def parse_radius_event(raw: dict) -> RadiusEvent:
    """
    Parse and validate a raw RADIUS event dict into a RadiusEvent.

    Normalises the AP name in-place before validation.

    RFC 2869 §5.1 — Gigawords handling:
    Acct-Input-Gigawords and Acct-Output-Gigawords are optional attributes
    that count how many times the 32-bit Octets counter has wrapped past
    4,294,967,295 bytes. They are absent from most packets (only relevant
    for sessions exceeding ~4GB). We default them to 0 when not present so
    the model's computed properties always use the correct formula:
        true_bytes = (gigawords * 2^32) + octets
    """
    if "Called-Station-Id" in raw:
        raw["Called-Station-Id"] = normalize_ap_name(raw["Called-Station-Id"])

    # Ensure Gigawords fields are present; absent = zero wraps occurred
    raw.setdefault("Acct-Input-Gigawords", 0)
    raw.setdefault("Acct-Output-Gigawords", 0)

    return RadiusEvent.model_validate(raw)


def octets_to_mb(octets: Optional[int]) -> float:
    if not octets:
        return 0.0
    return octets / (1024 * 1024)
