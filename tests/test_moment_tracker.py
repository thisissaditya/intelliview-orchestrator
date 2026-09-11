import json
from unittest.mock import Mock

from orchestrator.moment_tracker import MomentTracker


def test_export_timeline_returns_ordered_json():
    redis = Mock()
    tracker = MomentTracker()
    tracker._redis = redis

    moments = [
        {
            "id": "moment_2",
            "session_id": "session_1",
            "type": "candidate_joined",
            "timestamp": "2026-08-27T10:05:00+00:00",
            "metadata": {},
        },
        {
            "id": "moment_1",
            "session_id": "session_1",
            "type": "session_start",
            "timestamp": "2026-08-27T10:00:00+00:00",
            "metadata": {},
        },
    ]

    redis.lrange.return_value = [json.dumps(m) for m in moments]

    result = tracker.export_timeline("session_1")

    timeline = json.loads(result)

    assert timeline[0]["type"] == "session_start"
    assert timeline[1]["type"] == "candidate_joined"
    assert timeline[0]["index"] == 0
    assert timeline[1]["index"] == 1
    assert timeline[0]["duration"] is None
    assert timeline[1]["duration"] == 300000.0
