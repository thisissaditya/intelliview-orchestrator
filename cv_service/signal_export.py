"""Adapter for exporting normalized CV-service signals."""

from typing import Any


def export_signals(cv_result: dict[str, Any] | None) -> dict[str, Any]:
    """Convert CV-service output into a consistent signal structure.

    The exported structure contains:
        face_count: Number of detected faces.
        gaze_off_screen: Whether off-screen gaze was detected.
        confidence: Face-detection confidence.

    Missing or invalid sections are handled safely using defaults.
    """
    if not isinstance(cv_result, dict):
        return {
            "face_count": 0,
            "gaze_off_screen": False,
            "confidence": 0.0,
        }

    face_data = cv_result.get("face_detected")
    if not isinstance(face_data, dict):
        face_data = {}

    head_data = cv_result.get("head_movement_suspicious")
    if not isinstance(head_data, dict):
        head_data = {}

    return {
        "face_count": face_data.get("face_count", 0),
        "gaze_off_screen": head_data.get(
            "gaze_off_screen",
            head_data.get("suspicious_movement_detected", False),
        ),
        "confidence": face_data.get("confidence", 0.0),
    }
