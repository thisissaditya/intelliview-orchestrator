from datetime import datetime, timezone
from unittest.mock import patch

from orchestrator.time_utils import utcnow


def test_utcnow_returns_timezone_aware_datetime():
    result = utcnow()

    assert isinstance(result, datetime)
    assert result.tzinfo == timezone.utc


def test_utcnow_returns_utc_time():
    expected = datetime(2026, 8, 26, 10, 0, 0, tzinfo=timezone.utc)

    with patch("orchestrator.time_utils.datetime") as mock_datetime:
        mock_datetime.now.return_value = expected

        result = utcnow()

    assert result == expected
    assert result.tzinfo == timezone.utc


def test_utcnow_during_spring_forward_dst():
    """
    Test utcnow() around the US Eastern spring-forward DST transition.

    On March 8, 2026, clocks in US Eastern time move forward
    from 2:00 AM to 3:00 AM.

    utcnow() should continue returning an unambiguous UTC datetime.
    """
    expected = datetime(2026, 3, 8, 7, 0, 0, tzinfo=timezone.utc)

    with patch("orchestrator.time_utils.datetime") as mock_datetime:
        mock_datetime.now.return_value = expected

        result = utcnow()

    assert result == expected
    assert result.tzinfo == timezone.utc
    assert result.utcoffset().total_seconds() == 0


def test_utcnow_during_fall_back_dst():
    """
    Test utcnow() around the US Eastern fall-back DST transition.

    On November 1, 2026, clocks in US Eastern time move backward,
    causing the local 1:00 AM hour to occur twice.

    UTC should remain unambiguous.
    """
    expected = datetime(2026, 11, 1, 6, 0, 0, tzinfo=timezone.utc)

    with patch("orchestrator.time_utils.datetime") as mock_datetime:
        mock_datetime.now.return_value = expected

        result = utcnow()

    assert result == expected
    assert result.tzinfo == timezone.utc
    assert result.utcoffset().total_seconds() == 0
