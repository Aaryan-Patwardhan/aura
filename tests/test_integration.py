import json
import pytest
from unittest.mock import AsyncMock, patch

from ingestion.models.session_event import AcctStatusType, RadiusEvent
from ingestion.parsers.radius_parser import parse_radius_event
import session_manager.redis_client

@pytest.fixture
def mock_radius_packet():
    return {
        "User-Name": "test_student",
        "Acct-Status-Type": "Start",
        "Called-Station-Id": "ap-zone-1",
    }

def test_parse_radius_event(mock_radius_packet):
    """Test standard RADIUS parsing handles Start packets predictably."""
    event = parse_radius_event(mock_radius_packet)
    assert event.user_name == "test_student"
    assert event.acct_status_type == AcctStatusType.START
    assert event.called_station_id == "ap-zone-1"
    assert event.bytes_downloaded_mb == 0.0

@pytest.mark.asyncio
async def test_session_manager_open_closes_gracefully():
    """Mock test proving Redis session bindings map keys cleanly."""
    with patch("session_manager.redis_client._get_redis") as mock_redis:
        mock_instance = AsyncMock()
        mock_redis.return_value = mock_instance
        
        from session_manager.redis_client import session_open, session_close
        
        await session_open("test", 1, "2023-01-01T00:00:00", "ap-1")
        mock_instance.hset.assert_called_once()
        mock_instance.sadd.assert_called_once()

        mock_instance.hgetall.return_value = {
            "username": "test",
            "room_id": "1",
            "bytes_downloaded_mb": "10.0",
            "bytes_uploaded_mb": "5.0",
        }
        
        # Pipeline execution simulation mappings
        from unittest.mock import MagicMock
        pipeline_mock = AsyncMock()
        mock_instance.pipeline = MagicMock(return_value=pipeline_mock)

        session = await session_close("test")
        assert session["username"] == "test"
        assert session["room_id"] == 1
        assert session["bytes_downloaded_mb"] == 10.0
