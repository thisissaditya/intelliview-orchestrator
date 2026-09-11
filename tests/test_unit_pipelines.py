"""Unit tests for the AI pipeline stubs.

These verify the pluggable contracts still hold: each pipeline returns the
shape the RiskScoringEngine consumes, and the seeded deterministic outputs
let end-to-end risk classification thresholds fire.
"""

from workers.audio_pipeline import (
    calculate_audio_risk_score,
    detect_background_voices,
    detect_suspicious_conversation,
    run_audio_analysis,
    transcribe_speech,
)
from workers.evaluation_pipeline import (
    evaluate_answer_quality,
    evaluate_answers,
    evaluate_communication,
    evaluate_technical_accuracy,
    generate_feedback,
)
from workers.video_pipeline import (
    calculate_video_risk_score,
    detect_face,
    detect_mobile_phone,
    detect_multiple_persons,
    detect_suspicious_head_movement,
    run_video_analysis,
)


def test_video_pipeline_runs_end_to_end():
    out = run_video_analysis("abc123")
    for key in (
        "session_id",
        "face_detected",
        "head_movement_suspicious",
        "phone_detected",
        "multiple_persons",
        "risk_score",
    ):
        assert key in out
    assert 0.0 <= out["risk_score"] <= 1.0


def test_video_pipeline_is_deterministic_per_session():
    a = run_video_analysis("session-X")
    b = run_video_analysis("session-X")
    assert a == b


def test_audio_pipeline_returns_expected_shape():
    out = run_audio_analysis("s-audio")
    for key in (
        "session_id",
        "transcription",
        "background_voices",
        "suspicious_conversation",
        "risk_score",
    ):
        assert key in out
    assert 0.0 <= out["risk_score"] <= 1.0


def test_audio_pipeline_variation_across_sessions():
    samples = {run_audio_analysis(f"sess-{i}")["risk_score"] for i in range(20)}
    assert len(samples) > 1, "Expected deterministic-but-varied outputs"


def test_evaluation_pipeline_returns_inverse_risk():
    out = evaluate_answers("s-eval")
    assert 0.0 <= out["risk_score"] <= 1.0
    assert "answer_quality_score" in out
    assert "feedback" in out


def test_video_risk_accumulates_signals():
    high_risk_input = {
        "face_detected": {"faces_found": False},
        "head_movement_suspicious": {"suspicious_movement_detected": True},
        "phone_detected": {"phone_detected": True},
        "multiple_persons": {"multiple_persons_detected": True},
    }
    score = calculate_video_risk_score(high_risk_input)
    assert score >= 0.9  # multiple + phone + movement + no_face -> clamped at 1.0


def test_audio_risk_handles_empty_transcription():
    out = {
        "transcription": {"text": ""},
        "background_voices": {"background_voices_detected": False},
        "suspicious_conversation": {"suspicious_pattern_detected": False},
    }
    assert calculate_audio_risk_score(out) >= 0.3


def test_helper_functions_return_dicts():
    for fn, sid in [
        (detect_face, "x"),
        (detect_suspicious_head_movement, "x"),
        (detect_mobile_phone, "x"),
        (detect_multiple_persons, "x"),
        (transcribe_speech, "x"),
        (detect_background_voices, "x"),
        (detect_suspicious_conversation, "x"),
        (evaluate_answer_quality, "x"),
        (evaluate_technical_accuracy, "x"),
        (evaluate_communication, "x"),
        (generate_feedback, "x"),
    ]:
        assert isinstance(fn(sid), dict)


def test_video_pipeline_handles_corrupt_input(monkeypatch):
    """Corrupt/invalid video input should return a clean error, not crash."""
    from workers import video_pipeline

    def broken_detect_face(session_id):
        raise ValueError("Corrupt video file")

    monkeypatch.setattr(video_pipeline, "detect_face", broken_detect_face)

    result = video_pipeline.run_video_analysis("test-session-corrupt")

    assert result["error"] == "corrupt_or_unreadable_video"
    assert "session_id" in result
    assert result["risk_score"] == 0.0
