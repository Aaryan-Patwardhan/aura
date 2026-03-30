"""
Shared RADIUS packet schema — used by both simulator and ingestion parser.
"""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class RadiusPacket(BaseModel):
    """Canonical RADIUS Accounting packet structure."""
    user_name: str = Field(..., alias="User-Name")
    acct_status_type: str = Field(..., alias="Acct-Status-Type")   # Start|Stop|Interim-Update
    called_station_id: str = Field(..., alias="Called-Station-Id")
    calling_station_id: Optional[str] = Field(default=None, alias="Calling-Station-Id")
    acct_input_octets: Optional[int] = Field(default=0, alias="Acct-Input-Octets")
    acct_output_octets: Optional[int] = Field(default=0, alias="Acct-Output-Octets")
    acct_session_time: Optional[int] = Field(default=None, alias="Acct-Session-Time")
    nas_ip_address: Optional[str] = Field(default="10.0.0.1", alias="NAS-IP-Address")
    event_timestamp: Optional[str] = Field(default=None, alias="Event-Timestamp")
    integrity_suspect: Optional[bool] = Field(default=False, alias="Integrity-Suspect")

    model_config = {"populate_by_name": True}

    def to_api_dict(self) -> dict:
        """Serialize using RADIUS attribute names (aliases) for the API payload."""
        return self.model_dump(by_alias=True, exclude_none=False)
