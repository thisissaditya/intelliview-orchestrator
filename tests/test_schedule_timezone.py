"""
Tests for Issue #6: timezone-aware scheduling.

Covers the gaps called out in code review:
- Correct UTC storage from a local time + timezone
- Midnight-boundary edge case (date rolls over correctly)
- timezone is persisted and returned in every response
- Two different viewer timezones resolve to the correct local equivalents
  (verified indirectly: given the same stored UTC value, converting to
  two different IANA zones produces the expected, different local times)

All test dates are computed relative to "today" (30+ days out) rather
than hardcoded, so this file keeps passing regardless of when it's run —
a fixed date like "2026-08-21" eventually becomes "in the past" and starts
failing the API's own future-date validation, which isn't a real bug.

Adjust the import paths / test client fixture below to match your
project's existing test setup (conftest.py) if it differs.
"""

import uuid
from datetime import date, datetime, timedelta, timezone
from zoneinfo import ZoneInfo

import pytest
from fastapi.testclient import TestClient

from orchestrator.main import app  # adjust if your app entrypoint differs

client = TestClient(app)


def future_date(days_ahead: int = 30) -> date:
    """A date safely in the future, so 'must be in the future' validation
    never rejects test data regardless of when the suite runs."""
    return (datetime.now(timezone.utc) + timedelta(days=days_ahead)).date()


@pytest.fixture
def test_candidate():
    """Create a candidate to schedule against.

    Uses a unique email per test run so repeated runs against a
    persistent (non-rolled-back) database don't collide on the
    candidates.email UNIQUE constraint.
    """
    unique_email = f"tztest_{uuid.uuid4().hex[:8]}@example.com"
    resp = client.post(
        "/candidates",
        json={"name": "TZ Test Candidate", "email": unique_email},
    )
    assert resp.status_code in (200, 201), resp.text
    body = resp.json()
    return body.get("candidate_id", body.get("id"))


def _create_schedule(candidate_id, scheduled_at, tz_name, **extra):
    payload = {
        "candidate_id": candidate_id,
        "interviewer_id": "test-interviewer",
        "scheduled_at": scheduled_at,
        "timezone": tz_name,
        "send_email": False,
        **extra,
    }
    return client.post("/api/schedule", json=payload)


class TestUTCStorage:
    def test_ist_converts_to_correct_utc(self, test_candidate):
        """10:00 in Asia/Kolkata (UTC+5:30) should store as 04:30 UTC."""
        d = future_date(30)
        resp = _create_schedule(
            test_candidate, f"{d.isoformat()}T10:00:00", "Asia/Kolkata"
        )
        assert resp.status_code == 201, resp.text
        data = resp.json()["schedule"]
        stored = datetime.fromisoformat(data["scheduled_at"]).astimezone(timezone.utc)
        assert stored.hour == 4
        assert stored.minute == 30

    def test_new_york_converts_to_correct_utc(self, test_candidate):
        """10:00 EDT (UTC-4, northern-hemisphere summer) should store as 14:00 UTC."""
        # Use a summer date explicitly so we're testing EDT, not EST.
        d = future_date(30)
        summer_d = date(d.year + (1 if d.month > 8 else 0), 8, 15)
        resp = _create_schedule(
            test_candidate, f"{summer_d.isoformat()}T10:00:00", "America/New_York"
        )
        assert resp.status_code == 201, resp.text
        data = resp.json()["schedule"]
        stored = datetime.fromisoformat(data["scheduled_at"]).astimezone(timezone.utc)
        assert stored.hour == 14


class TestMidnightBoundary:
    def test_late_evening_pacific_rolls_to_next_utc_day(self, test_candidate):
        """
        10 PM PDT (UTC-7) must roll over to the NEXT calendar day in UTC —
        the exact off-by-one case called out in the issue's acceptance
        criteria.
        """
        d = future_date(35)
        resp = _create_schedule(
            test_candidate, f"{d.isoformat()}T22:00:00", "America/Los_Angeles"
        )
        assert resp.status_code == 201, resp.text
        data = resp.json()["schedule"]
        stored = datetime.fromisoformat(data["scheduled_at"]).astimezone(timezone.utc)
        expected_utc_date = d + timedelta(days=1)
        assert stored.date() == expected_utc_date
        assert stored.hour == 5

    def test_early_morning_kolkata_does_not_roll_back_a_day(self, test_candidate):
        """
        00:15 IST (UTC+5:30) must correctly move to the PREVIOUS calendar
        day in UTC (not stay on the same day, which would be the
        off-by-one bug this issue targets).
        """
        d = future_date(40)
        resp = _create_schedule(
            test_candidate, f"{d.isoformat()}T00:15:00", "Asia/Kolkata"
        )
        assert resp.status_code == 201, resp.text
        data = resp.json()["schedule"]
        stored = datetime.fromisoformat(data["scheduled_at"]).astimezone(timezone.utc)
        expected_utc_date = d - timedelta(days=1)
        assert stored.date() == expected_utc_date
        assert stored.hour == 18
        assert stored.minute == 45


class TestTimezonePersistedAndReturned:
    def test_create_response_includes_timezone(self, test_candidate):
        d = future_date(45)
        resp = _create_schedule(
            test_candidate, f"{d.isoformat()}T10:00:00", "Asia/Kolkata"
        )
        assert resp.status_code == 201, resp.text
        assert resp.json()["schedule"]["timezone"] == "Asia/Kolkata"

    def test_get_schedule_returns_timezone(self, test_candidate):
        d = future_date(46)
        create_resp = _create_schedule(
            test_candidate, f"{d.isoformat()}T10:00:00", "Europe/London"
        )
        assert create_resp.status_code == 201, create_resp.text
        schedule_id = create_resp.json()["schedule"]["id"]

        get_resp = client.get(f"/api/schedule/{schedule_id}")
        assert get_resp.status_code == 200
        assert get_resp.json()["timezone"] == "Europe/London"

    def test_list_schedules_includes_timezone(self, test_candidate):
        d = future_date(47)
        create_resp = _create_schedule(
            test_candidate, f"{d.isoformat()}T10:00:00", "Asia/Tokyo"
        )
        assert create_resp.status_code == 201, create_resp.text

        list_resp = client.get("/api/schedule")
        assert list_resp.status_code == 200
        schedules = list_resp.json()["schedules"]
        assert any(s.get("timezone") == "Asia/Tokyo" for s in schedules)


class TestCrossTimezoneDisplay:
    def test_same_utc_instant_resolves_correctly_for_two_viewers(self, test_candidate):
        """
        Simulates two viewers in different timezones looking at the SAME
        stored UTC instant. Each must compute the correct, DIFFERENT local
        time for their own zone. This is the acceptance criterion
        "Two different timezones each see correct local time", verified
        at the conversion level (the frontend does the equivalent with
        Intl.DateTimeFormat).
        """
        d = future_date(30)
        resp = _create_schedule(test_candidate, f"{d.isoformat()}T14:00:00", "UTC")
        assert resp.status_code == 201, resp.text
        stored_utc = datetime.fromisoformat(resp.json()["schedule"]["scheduled_at"])

        viewer_ny_local = stored_utc.astimezone(ZoneInfo("America/New_York"))
        viewer_tokyo_local = stored_utc.astimezone(ZoneInfo("Asia/Tokyo"))

        # 14:00 UTC -> 10:00 EDT / 09:00 EST same day depending on DST
        assert viewer_ny_local.hour in (9, 10)
        assert viewer_ny_local.date() == d

        # 14:00 UTC -> 23:00 JST same day (Japan has no DST, always UTC+9)
        assert viewer_tokyo_local.hour == 23
        assert viewer_tokyo_local.date() == d

        # And they must genuinely differ from each other
        assert viewer_ny_local.hour != viewer_tokyo_local.hour


class TestTimezoneValidation:
    def test_invalid_timezone_returns_400(self, test_candidate):
        d = future_date(30)
        resp = _create_schedule(
            test_candidate, f"{d.isoformat()}T10:00:00", "Not/AZone"
        )
        assert resp.status_code == 400

    def test_abbreviation_resolves_and_stores_canonical_name(self, test_candidate):
        """
        IST should resolve via the abbreviation map AND be persisted as
        the canonical IANA name (Asia/Kolkata), not the raw "IST" string —
        the frontend's Intl.DateTimeFormat only accepts real IANA zone
        names, so storing the abbreviation verbatim would break display.
        """
        d = future_date(31)
        resp = _create_schedule(test_candidate, f"{d.isoformat()}T10:00:00", "IST")
        assert resp.status_code == 201, resp.text
        assert resp.json()["schedule"]["timezone"] == "Asia/Kolkata"
