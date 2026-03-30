import pytest
from pydantic import ValidationError

from ingestion.models.session_event import AcctStatusType, RadiusEvent
from ingestion.parsers.radius_parser import parse_radius_event

def test_parse_valid_start_event():
    raw = {
        "User-Name": "student_123",
        "Acct-Status-Type": "Start",
        "Called-Station-Id": "ap-01",
    }
    event = parse_radius_event(raw)
    assert event.user_name == "student_123"
    assert event.acct_status_type == AcctStatusType.START
    assert event.called_station_id == "ap-01"
    assert event.acct_input_octets is None
    assert event.acct_output_octets is None


def test_parse_valid_stop_event():
    raw = {
        "User-Name": "student_123",
        "Acct-Status-Type": "Stop",
        "Called-Station-Id": "ap-01",
        "Acct-Input-Octets": 5000000,
        "Acct-Output-Octets": 20000000,
        "Acct-Session-Time": 3600,
    }
    event = parse_radius_event(raw)
    assert event.acct_status_type == AcctStatusType.STOP
    assert event.acct_input_octets == 5000000
    assert event.acct_session_time == 3600


def test_missing_required_fields_raises_validation_error():
    raw = {
        "User-Name": "student_123",
        # Missing Acct-Status-Type
        "Called-Station-Id": "ap-01",
    }
    with pytest.raises(ValidationError):
        parse_radius_event(raw)


def test_gigawords_computation_mb():
    raw = {
        "User-Name": "student_123",
        "Acct-Status-Type": "Interim-Update",
        "Called-Station-Id": "ap-01",
        "Acct-Input-Octets": 1048576,       # 1 MB
        "Acct-Output-Octets": 2097152,      # 2 MB
        "Acct-Input-Gigawords": 1,          # + 4096 MB
        "Acct-Output-Gigawords": 0,         # 0
    }
    event = parse_radius_event(raw)
    # Uploaded = Input = 4096 + 1 = 4097
    assert event.bytes_uploaded_mb == 4097.0
    # Downloaded = Output = 0 + 2 = 2
    assert event.bytes_downloaded_mb == 2.0
