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
    Normalizes the AP name in-place before validation.
    """
    if "Called-Station-Id" in raw:
        raw["Called-Station-Id"] = normalize_ap_name(raw["Called-Station-Id"])
    return RadiusEvent.model_validate(raw)


def octets_to_mb(octets: Optional[int]) -> float:
    if not octets:
        return 0.0
    return octets / (1024 * 1024)
