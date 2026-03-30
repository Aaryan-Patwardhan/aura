"""
Pydantic models for RADIUS accounting events.
"""
from __future__ import annotations

from datetime import datetime
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

    # Byte counters (present on Stop and Interim-Update)
    acct_input_octets: Optional[int] = Field(default=0, alias="Acct-Input-Octets")
    acct_output_octets: Optional[int] = Field(default=0, alias="Acct-Output-Octets")

    # Session duration in seconds (provided by WLC on Stop)
    acct_session_time: Optional[int] = Field(default=None, alias="Acct-Session-Time")

    # NAS / device info
    nas_ip_address: Optional[str] = Field(default=None, alias="NAS-IP-Address")
    framed_ip_address: Optional[str] = Field(default=None, alias="Framed-IP-Address")
    calling_station_id: Optional[str] = Field(default=None, alias="Calling-Station-Id", description="Client MAC address")

    # Timestamp injected by simulator or WLC syslog forwarder
    event_timestamp: Optional[datetime] = Field(default_factory=datetime.utcnow, alias="Event-Timestamp")

    # Integrity flag — set by simulator for mac_clone_attempt scenario
    integrity_suspect: Optional[bool] = Field(default=False, alias="Integrity-Suspect")

    model_config = {"populate_by_name": True}

    @field_validator("acct_input_octets", "acct_output_octets", mode="before")
    @classmethod
    def coerce_none_to_zero(cls, v):
        return v if v is not None else 0

    @property
    def bytes_downloaded_mb(self) -> float:
        """Bytes uploaded by AP = downloaded by client."""
        return (self.acct_output_octets or 0) / (1024 * 1024)

    @property
    def bytes_uploaded_mb(self) -> float:
        """Bytes downloaded by AP = uploaded by client."""
        return (self.acct_input_octets or 0) / (1024 * 1024)


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


class LiveSessionInfo(BaseModel):
    username: str
    room_id: Optional[int]
    ap_name: str
    connect_time: str
    bytes_downloaded_mb: float
    bytes_uploaded_mb: float
