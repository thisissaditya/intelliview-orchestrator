from cv_service.signal_export import export_signals


def test_export_signals_with_valid_cv_result():
    cv_result = {
        "face_detected": {
            "faces_found": True,
            "face_count": 2,
            "confidence": 0.91,
        },
        "head_movement_suspicious": {
            "suspicious_movement_detected": True,
            "head_turns_count": 2,
            "avg_gaze_deviation": 0.4,
        },
    }

    result = export_signals(cv_result)

    assert result == {
        "face_count": 2,
        "gaze_off_screen": True,
        "confidence": 0.91,
    }


def test_export_signals_with_missing_sections():
    result = export_signals({})

    assert result == {
        "face_count": 0,
        "gaze_off_screen": False,
        "confidence": 0.0,
    }


def test_export_signals_with_none():
    result = export_signals(None)

    assert result == {
        "face_count": 0,
        "gaze_off_screen": False,
        "confidence": 0.0,
    }


def test_export_signals_with_invalid_nested_sections():
    cv_result = {
        "face_detected": None,
        "head_movement_suspicious": None,
    }

    result = export_signals(cv_result)

    assert result == {
        "face_count": 0,
        "gaze_off_screen": False,
        "confidence": 0.0,
    }


def test_export_signals_prefers_gaze_off_screen_when_available():
    cv_result = {
        "face_detected": {
            "face_count": 1,
            "confidence": 0.95,
        },
        "head_movement_suspicious": {
            "gaze_off_screen": True,
            "suspicious_movement_detected": False,
        },
    }

    result = export_signals(cv_result)

    assert result["face_count"] == 1
    assert result["gaze_off_screen"] is True
    assert result["confidence"] == 0.95
