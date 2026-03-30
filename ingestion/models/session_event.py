"""
Pydantic models for RADIUS accounting events.
"""
from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field, field_validator


class AcctStatusType(str, Enum):
    START = "Start"
    STOP = "Stop"
    INTERIM_UPDATE = "Interim-Update"
    ACCOUNTING_ON = "Accounting-On"
    ACCOUNTING_OFF = "Accounting-Off"


class RadiusEvent(BaseModel):
    """
    Raw RADIUS Accounting packet received from the WLC or simulator.
    Field names mirror standard RADIUS Accounting attributes (RFC 2866).
    """
    # Primary identity — institutional credential, MAC-randomization immune
    user_name: str = Field(..., alias="User-Name", description="Student institutional login (802.1X credential)")

    # Event type
    acct_status_type: AcctStatusType = Field(..., alias="Acct-Status-Type")

    # AP identifier — maps to rooms via access_points table
    called_station_id: str = Field(..., alias="Called-Station-Id", description="AP name or BSSID")

    # Byte counters (present on Stop; optional on Interim-Update per RFC 2866)
    # Default is None — see routers/radius.py for defensive guard logic
    acct_input_octets: Optional[int] = Field(default=None, alias="Acct-Input-Octets")
    acct_output_octets: Optional[int] = Field(default=None, alias="Acct-Output-Octets")

    # RFC 2869 §5.1 — Gigawords track counter wraps past 4,294,967,295 bytes (~4GB).
    # A 3-hour session at 4 Mbps accumulates ~5.4GB, wrapping the 32-bit Octets counter.
    # true_bytes = (gigawords * 4_294_967_296) + octets
    acct_input_gigawords: Optional[int] = Field(default=0, alias="Acct-Input-Gigawords")
    acct_output_gigawords: Optional[int] = Field(default=0, alias="Acct-Output-Gigawords")

    # Session duration in seconds (provided by WLC on Stop)
    acct_session_time: Optional[int] = Field(default=None, alias="Acct-Session-Time")

    # NAS / device info
    nas_ip_address: Optional[str] = Field(default=None, alias="NAS-IP-Address")
    framed_ip_address: Optional[str] = Field(default=None, alias="Framed-IP-Address")
    calling_station_id: Optional[str] = Field(default=None, alias="Calling-Station-Id", description="Client MAC address")

    # Timestamp injected by simulator or WLC syslog forwarder
    event_timestamp: Optional[datetime] = Field(default_factory=lambda: datetime.now(timezone.utc), alias="Event-Timestamp")

    # Integrity flag — set by simulator for mac_clone_attempt scenario
    integrity_suspect: Optional[bool] = Field(default=False, alias="Integrity-Suspect")

    model_config = {"populate_by_name": True}

    @field_validator("acct_input_gigawords", "acct_output_gigawords", mode="before")
    @classmethod
    def coerce_gigawords_none_to_zero(cls, v):
        """Gigawords absent from packet means zero wraps — always safe to default to 0."""
        return v if v is not None else 0

    _GIGAWORD = 4_294_967_296  # 2^32

    @property
    def bytes_downloaded_mb(self) -> float:
        """True download volume accounting for 32-bit counter wraps (RFC 2869 §5.1).

        Bytes uploaded by AP = downloaded by client.
        true_bytes = (Acct-Output-Gigawords * 2^32) + Acct-Output-Octets
        """
        octets = self.acct_output_octets or 0
        gigawords = self.acct_output_gigawords or 0
        true_bytes = (gigawords * self._GIGAWORD) + octets
        return true_bytes / (1024 * 1024)

    @property
    def bytes_uploaded_mb(self) -> float:
        """True upload volume accounting for 32-bit counter wraps (RFC 2869 §5.1).

        Bytes downloaded by AP = uploaded by client.
        true_bytes = (Acct-Input-Gigawords * 2^32) + Acct-Input-Octets
        """
        octets = self.acct_input_octets or 0
        gigawords = self.acct_input_gigawords or 0
        true_bytes = (gigawords * self._GIGAWORD) + octets
        return true_bytes / (1024 * 1024)


class SessionOpenedResponse(BaseModel):
    status: str = "session_opened"
    username: str
    ap_name: str
    room_id: Optional[int]


class SessionUpdatedResponse(BaseModel):
    status: str = "session_updated"
    username: str
    bytes_downloaded_mb: float
    bytes_uploaded_mb: float


class SessionFinalizedResponse(BaseModel):
    status: str = "session_finalized"
    username: str
    minutes_present: Optional[int]
    attendance_status: Optional[str]
    proxy_risk_score: Optional[float]


class IntegritySuspectResponse(BaseModel):
    status: str = "integrity_suspect"
    username: str
    ap_name: str
    reason: str
