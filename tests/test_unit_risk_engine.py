"""
Unit tests that don't require a running stack.

These exercise pure-logic modules that are easy to test in isolation.
"""

import math

from workers.risk_engine import RiskScoringEngine


def test_classify_risk_boundaries():
    assert RiskScoringEngine.classify_risk(0.0) == "LOW"
    assert RiskScoringEngine.classify_risk(0.29) == "LOW"
    assert RiskScoringEngine.classify_risk(0.3) == "MEDIUM"
    assert RiskScoringEngine.classify_risk(0.59) == "MEDIUM"
    assert RiskScoringEngine.classify_risk(0.6) == "HIGH"
    assert RiskScoringEngine.classify_risk(0.79) == "HIGH"
    assert RiskScoringEngine.classify_risk(0.8) == "CRITICAL"
    assert RiskScoringEngine.classify_risk(1.0) == "CRITICAL"


def test_calculate_final_risk_weighted_and_clamped():
    # 0.4*1.0 + 0.3*1.0 + 0.3*1.0 = 1.0
    assert RiskScoringEngine.calculate_final_risk(1.0, 1.0, 1.0) == 1.0
    # 0.4*0 + 0.3*0 + 0.3*0 = 0
    assert RiskScoringEngine.calculate_final_risk(0.0, 0.0, 0.0) == 0.0
    # Mid-point
    score = RiskScoringEngine.calculate_final_risk(0.5, 0.5, 0.5)
    assert math.isclose(score, 0.5, rel_tol=1e-9)


def test_video_risk_no_face_is_high():
    risk = RiskScoringEngine.calculate_video_risk(
        {"face_detected": {"faces_found": False}}
    )
    assert risk >= 0.4


def test_video_risk_clean_signals_is_zero():
    risk = RiskScoringEngine.calculate_video_risk(
        {
            "face_detected": {"faces_found": True},
            "multiple_persons": {"multiple_persons_detected": False},
            "phone_detected": {"phone_detected": False},
            "head_movement_suspicious": {"suspicious_movement_detected": False},
        }
    )
    assert risk == 0.0


def test_audio_risk_background_voices_increases_risk():
    base = RiskScoringEngine.calculate_audio_risk({"transcription": {"text": "ok"}})
    with_bg = RiskScoringEngine.calculate_audio_risk(
        {
            "transcription": {"text": "ok"},
            "background_voices": {"background_voices_detected": True},
        }
    )
    assert with_bg > base


def test_evaluation_risk_low_quality_increases_risk():
    base = RiskScoringEngine.calculate_evaluation_risk(
        {
            "answer_quality_score": {"overall_quality_score": 80},
            "technical_accuracy": {"accuracy_score": 80},
            "communication_clarity": {"clarity_score": 80},
        }
    )
    low = RiskScoringEngine.calculate_evaluation_risk(
        {
            "answer_quality_score": {"overall_quality_score": 20},
            "technical_accuracy": {"accuracy_score": 80},
            "communication_clarity": {"clarity_score": 80},
        }
    )
    assert low > base


def test_generate_risk_report_shape():
    report = RiskScoringEngine.generate_risk_report(
        "s1",
        {"face_detected": {"faces_found": True}},
        {"transcription": {"text": "hello"}},
        {
            "answer_quality_score": {"overall_quality_score": 70},
            "technical_accuracy": {"accuracy_score": 70},
            "communication_clarity": {"clarity_score": 70},
        },
    )
    assert report["session_id"] == "s1"
    assert "final_risk_score" in report
    assert report["risk_classification"] in {"LOW", "MEDIUM", "HIGH", "CRITICAL"}
    assert "component_risks" in report
    assert "risk_factors" in report
    assert "explanation" in report
    assert "recommendation" in report


def test_multiple_persons_override_to_critical():
    report = RiskScoringEngine.generate_risk_report(
        "s1",
        {
            "face_detected": {"faces_found": True},
            "multiple_persons": {"multiple_persons_detected": True},
        },
        {"transcription": {"text": "hello"}},
        {
            "answer_quality_score": {"overall_quality_score": 90},
            "technical_accuracy": {"accuracy_score": 90},
            "communication_clarity": {"clarity_score": 90},
        },
    )

    assert report["risk_classification"] == "CRITICAL"


def test_face_absent_override_to_high():
    report = RiskScoringEngine.generate_risk_report(
        "s1",
        {
            "face_detected": {"faces_found": False},
            "multiple_persons": {"multiple_persons_detected": False},
        },
        {"transcription": {"text": "hello"}},
        {
            "answer_quality_score": {"overall_quality_score": 90},
            "technical_accuracy": {"accuracy_score": 90},
            "communication_clarity": {"clarity_score": 90},
        },
    )

    assert report["risk_classification"] == "HIGH"


def test_no_override_keeps_weighted_classification():
    report = RiskScoringEngine.generate_risk_report(
        "s1",
        {
            "face_detected": {"faces_found": True},
            "multiple_persons": {"multiple_persons_detected": False},
            "phone_detected": {"phone_detected": False},
            "head_movement_suspicious": {"suspicious_movement_detected": False},
        },
        {"transcription": {"text": "hello"}},
        {
            "answer_quality_score": {"overall_quality_score": 90},
            "technical_accuracy": {"accuracy_score": 90},
            "communication_clarity": {"clarity_score": 90},
        },
    )

    assert report["risk_classification"] == "LOW"


def test_integrity_score_all_signals_clean_is_100():
    # No risk at all on any D2 signal -> integrity_score should be 100.
    signals = {name: 0.0 for name in RiskScoringEngine.INTEGRITY_SIGNAL_NAMES}
    score = RiskScoringEngine.calculate_integrity_score(signals)
    assert score == 100.0


def test_integrity_score_all_signals_maxed_is_0():
    # Maximum risk on every D2 signal -> integrity_score should be 0.
    signals = {name: 100.0 for name in RiskScoringEngine.INTEGRITY_SIGNAL_NAMES}
    score = RiskScoringEngine.calculate_integrity_score(signals)
    assert score == 0.0


def test_integrity_score_weighted_average_matches_expected(monkeypatch):
    # Use equal default weights (all 1.0) so the expected math is simple:
    # average risk across all 7 signals, then integrity = 100 - avg_risk.
    signals = {
        "tab_switching": 70.0,
        "browser_activity": 0.0,
        "audio_interruptions": 0.0,
        "multiple_persons": 0.0,
        "candidate_absence": 0.0,
        "gaze_deviation": 0.0,
        "background_noise": 0.0,
    }
    # avg_risk = 70 / 7 = 10 -> integrity_score = 90
    score = RiskScoringEngine.calculate_integrity_score(signals)
    assert math.isclose(score, 90.0, rel_tol=1e-9)


def test_integrity_score_respects_job_specific_weights(monkeypatch):
    import orchestrator.store as store
    from orchestrator.models import RiskWeights

    # Only tab_switching carries any weight for this job position.
    custom_weights = RiskWeights(
        tab_switching=1.0,
        browser_activity=0.0,
        audio_interruptions=0.0,
        multiple_persons=0.0,
        candidate_absence=0.0,
        gaze_deviation=0.0,
        background_noise=0.0,
    )
    monkeypatch.setattr(
        store, "get_weights_for_position", lambda job_position: custom_weights
    )

    signals = {
        "tab_switching": 30.0,
        "gaze_deviation": 100.0,  # should be ignored, its weight is 0
        "background_noise": 100.0,  # should be ignored, its weight is 0
    }
    score = RiskScoringEngine.calculate_integrity_score(
        signals, job_position="Software Engineer"
    )
    # Only tab_switching (risk=30) counts -> integrity_score = 100 - 30 = 70
    assert score == 70.0


def test_integrity_score_handles_missing_signals_gracefully():
    # Only 2 of the 7 D2 signals are available (e.g. cv_service was down);
    # fusion must not crash and should average only what it has.
    partial_signals = {
        "tab_switching": 20.0,
        "gaze_deviation": 40.0,
        # everything else missing/unavailable
    }
    score = RiskScoringEngine.calculate_integrity_score(partial_signals)
    # avg_risk = (20 + 40) / 2 = 30 -> integrity_score = 70
    assert math.isclose(score, 70.0, rel_tol=1e-9)


def test_integrity_score_handles_none_values_as_missing():
    # Signals explicitly set to None (source temporarily unavailable)
    # should be treated the same as an omitted key, not crash the fusion.
    signals = {name: None for name in RiskScoringEngine.INTEGRITY_SIGNAL_NAMES}
    signals["tab_switching"] = 10.0
    score = RiskScoringEngine.calculate_integrity_score(signals)
    assert score == 90.0


def test_integrity_score_all_signals_missing_returns_neutral_default():
    # Total absence of data must not crash; a neutral "no risk observed"
    # score is returned instead.
    score = RiskScoringEngine.calculate_integrity_score({})
    assert score == 100.0


def test_integrity_score_none_signals_dict_does_not_crash():
    # Defensive: even a None signals argument should not raise.
    score = RiskScoringEngine.calculate_integrity_score(None)
    assert score == 100.0


def test_integrity_score_clamped_to_0_100_range():
    # Out-of-range inputs should never push the result outside 0-100.
    signals = {"tab_switching": 500.0, "gaze_deviation": -50.0}
    score = RiskScoringEngine.calculate_integrity_score(signals)
    assert 0.0 <= score <= 100.0


def test_integrity_score_is_reproducible_for_same_input():
    # Same input signals must always produce the same output.
    signals = {
        "tab_switching": 15.0,
        "browser_activity": 25.0,
        "gaze_deviation": 5.0,
    }
    score_1 = RiskScoringEngine.calculate_integrity_score(signals)
    score_2 = RiskScoringEngine.calculate_integrity_score(dict(signals))
    assert score_1 == score_2


def test_multiple_persons_has_priority_over_face_absent():
    report = RiskScoringEngine.generate_risk_report(
        "s1",
        {
            "face_detected": {"faces_found": False},
            "multiple_persons": {"multiple_persons_detected": True},
        },
        {"transcription": {"text": "hello"}},
        {
            "answer_quality_score": {"overall_quality_score": 90},
            "technical_accuracy": {"accuracy_score": 90},
            "communication_clarity": {"clarity_score": 90},
        },
    )

    assert report["risk_classification"] == "CRITICAL"
