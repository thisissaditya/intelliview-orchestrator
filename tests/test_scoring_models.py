from workers.scoring_models import (
    ExperimentalRiskModel,
    WeightedRiskModel,
)


def test_scoring_output_ranges():
    """Test that risk scores fall within valid range (0.0 to 1.0)"""
    # Mock results for testing
    video_result = {"engagement_score": 0.8, "body_language_score": 0.7}
    audio_result = {"clarity_score": 0.9, "confidence_score": 0.85}
    evaluation_result = {"overall_score": 0.75, "accuracy": 0.8}

    # Test WeightedRiskModel
    weighted_model = WeightedRiskModel()
    report = weighted_model.generate_report(
        session_id="test-session",
        video_result=video_result,
        audio_result=audio_result,
        evaluation_result=evaluation_result,
    )

    assert "final_risk_score" in report
    assert 0.0 <= report["final_risk_score"] <= 1.0
    assert report["model"] == "weighted_model"

    # Test ExperimentalRiskModel
    experimental_model = ExperimentalRiskModel()
    report2 = experimental_model.generate_report(
        session_id="test-session-2",
        video_result=video_result,
        audio_result=audio_result,
        evaluation_result=evaluation_result,
    )

    assert "final_risk_score" in report2
    assert 0.0 <= report2["final_risk_score"] <= 1.0
    assert report2["model"] == "experimental_model"
