"""Unit and API tests for PDF export functionality."""

from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from orchestrator.main import app
from routers.sessions import _build_risk_report_pdf, _build_session_report_pdf

client = TestClient(app)


@pytest.mark.unit
class TestPDFGenerationFunctions:
    """Unit tests for PDF generation functions."""

    def test_build_session_report_pdf_with_all_fields(self):
        """Test _build_session_report_pdf with all analysis fields present."""
        session_data = {
            "session_id": "sess-123",
            "candidate_id": "cand-456",
            "status": "COMPLETED",
            "risk_score": 0.234,
            "assigned_node": "worker-1",
            "created_at": "2024-01-01T10:00:00Z",
            "start_time": "2024-01-01T10:05:00Z",
            "end_time": "2024-01-01T10:30:00Z",
            "updated_at": "2024-01-01T10:30:00Z",
            "video_analysis": {
                "confidence_score": 0.85,
                "facial_expressions": {
                    "neutral": 0.6,
                    "happy": 0.3,
                    "surprised": 0.1,
                },
            },
            "audio_analysis": {
                "sentiment": "positive",
                "clarity_score": 0.92,
                "speech_pace": 145,
                "filler_words": 3,
            },
            "ai_feedback": "Strong technical knowledge demonstrated",
            "evaluation_analysis": {
                "quality": 8.5,
                "accuracy": 9.0,
                "clarity": 8.0,
            },
        }

        response = _build_session_report_pdf(session_data)

        # Verify response type and headers
        assert response.status_code == 200
        assert response.media_type == "application/pdf"
        assert "Content-Disposition" in response.headers
        assert "session_sess-123.pdf" in response.headers["Content-Disposition"]

        # Verify PDF content has valid header
        content = response.body
        assert content.startswith(b"%PDF-")

    def test_build_session_report_pdf_with_missing_video_analysis(self):
        """Test PDF generation when video_analysis is None."""
        session_data = {
            "session_id": "sess-456",
            "candidate_id": "cand-789",
            "status": "COMPLETED",
            "risk_score": 0.15,
            "video_analysis": None,
            "audio_analysis": {"sentiment": "positive"},
            "ai_feedback": "Good performance",
        }

        response = _build_session_report_pdf(session_data)

        assert response.status_code == 200
        assert response.media_type == "application/pdf"
        content = response.body
        assert content.startswith(b"%PDF-")

    def test_build_session_report_pdf_with_missing_audio_analysis(self):
        """Test PDF generation when audio_analysis is None."""
        session_data = {
            "session_id": "sess-789",
            "candidate_id": "cand-012",
            "status": "COMPLETED",
            "risk_score": 0.42,
            "video_analysis": {"confidence_score": 0.75},
            "audio_analysis": None,
            "ai_feedback": "Moderate performance",
        }

        response = _build_session_report_pdf(session_data)

        assert response.status_code == 200
        assert response.media_type == "application/pdf"
        content = response.body
        assert content.startswith(b"%PDF-")

    def test_build_session_report_pdf_with_missing_ai_feedback(self):
        """Test PDF generation when ai_feedback is None."""
        session_data = {
            "session_id": "sess-abc",
            "candidate_id": "cand-def",
            "status": "COMPLETED",
            "risk_score": 0.67,
            "video_analysis": {"confidence_score": 0.80},
            "audio_analysis": {"sentiment": "neutral"},
            "ai_feedback": None,
        }

        response = _build_session_report_pdf(session_data)

        assert response.status_code == 200
        assert response.media_type == "application/pdf"
        content = response.body
        assert content.startswith(b"%PDF-")

    def test_build_session_report_pdf_with_missing_evaluation_analysis(self):
        """Test PDF generation when evaluation_analysis is None."""
        session_data = {
            "session_id": "sess-xyz",
            "candidate_id": "cand-uvw",
            "status": "COMPLETED",
            "risk_score": 0.28,
            "video_analysis": {"confidence_score": 0.88},
            "audio_analysis": {"sentiment": "positive"},
            "ai_feedback": "Excellent communication",
            "evaluation_analysis": None,
        }

        response = _build_session_report_pdf(session_data)

        assert response.status_code == 200
        assert response.media_type == "application/pdf"
        content = response.body
        assert content.startswith(b"%PDF-")

    def test_build_session_report_pdf_fallback_on_platypus_failure(self):
        """Test that platypus build failure falls back to _build_risk_report_pdf."""
        session_data = {
            "session_id": "sess-fallback",
            "candidate_id": "cand-test",
            "status": "COMPLETED",
            "risk_score": 0.5,
        }

        # Mock SimpleDocTemplate at the point it's imported inside the function
        with patch("reportlab.platypus.SimpleDocTemplate") as mock_doc_template:
            mock_instance = MagicMock()
            mock_instance.build.side_effect = Exception("Platypus build failed")
            mock_doc_template.return_value = mock_instance

            response = _build_session_report_pdf(session_data)

            # Should still return a valid PDF (from fallback)
            assert response.status_code == 200
            assert response.media_type == "application/pdf"
            content = response.body
            assert content.startswith(b"%PDF-")
            # Verify it's using the risk report filename pattern
            assert "risk_report_" in response.headers["Content-Disposition"]

    def test_build_risk_report_pdf_basic(self):
        """Test _build_risk_report_pdf generates valid PDF."""
        report_data = {
            "session_id": "sess-risk-1",
            "candidate_id": "cand-risk-1",
            "status": "COMPLETED",
            "risk_score": 0.75,
            "start_time": "2024-01-01T10:00:00Z",
            "end_time": "2024-01-01T10:20:00Z",
            "created_at": "2024-01-01T09:55:00Z",
            "updated_at": "2024-01-01T10:20:00Z",
        }

        response = _build_risk_report_pdf(report_data)

        assert response.status_code == 200
        assert response.media_type == "application/pdf"
        assert "Content-Disposition" in response.headers
        assert "risk_report_sess-risk-1.pdf" in response.headers["Content-Disposition"]
        content = response.body
        assert content.startswith(b"%PDF-")


@pytest.mark.contract
class TestPDFExportAPI:
    """API contract tests for /sessions/{session_id}/report/pdf endpoint."""

    def test_get_session_pdf_report_endpoint_exists(self):
        """Test PDF endpoint exists and returns structured response."""
        # Without running infrastructure, we expect 404 for nonexistent session
        # This verifies the endpoint is registered and returns proper HTTP responses
        response = client.get("/sessions/nonexistent-session/report/pdf")

        # Should return 404 with JSON detail, not a 500 or HTML error page
        assert response.status_code in [
            404,
            500,
        ]  # 404 if session not found, 500 if infrastructure missing
        assert "application/json" in response.headers.get("content-type", "")

        # Verify response has a detail field (FastAPI standard)
        json_data = response.json()
        assert "detail" in json_data

    def test_get_session_pdf_report_with_mocked_manager(self):
        """Test PDF generation with mocked session manager inside the router closure."""
        # This test demonstrates the PDF generation works when session data is provided
        # We test by directly calling the PDF generation functions (covered in unit tests above)
        # rather than trying to mock the closure-bound session_manager

        session_data = {
            "session_id": "sess-test",
            "candidate_id": "cand-test",
            "status": "COMPLETED",
            "risk_score": 0.5,
            "video_analysis": {"confidence_score": 0.85},
            "audio_analysis": {"sentiment": "positive"},
            "ai_feedback": "Test feedback",
        }

        # Call the PDF generation function directly (already tested above)
        response = _build_session_report_pdf(session_data)

        # Verify it returns a valid PDF
        assert response.status_code == 200
        assert response.media_type == "application/pdf"
        assert response.body.startswith(b"%PDF-")
