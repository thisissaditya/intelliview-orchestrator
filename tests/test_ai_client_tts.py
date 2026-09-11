from unittest.mock import patch

import pytest

from workers.ai_client import text_to_speech


def test_text_to_speech_success():
    expected_audio = b"fake-wav-audio"

    with patch(
        "workers.ai_client.synthesize_speech",
        return_value=expected_audio,
    ) as mock_tts:
        result = text_to_speech("Tell me about yourself.")

    assert result == expected_audio
    mock_tts.assert_called_once_with("Tell me about yourself.")


def test_text_to_speech_empty_text():
    with patch("workers.ai_client.synthesize_speech") as mock_tts:
        with pytest.raises(ValueError, match="must not be empty"):
            text_to_speech("")

    mock_tts.assert_not_called()


def test_text_to_speech_failure():
    with patch(
        "workers.ai_client.synthesize_speech",
        side_effect=RuntimeError("TTS failed"),
    ):
        with pytest.raises(RuntimeError, match="TTS synthesis failed"):
            text_to_speech("Tell me about yourself.")


def test_text_to_speech_empty_audio():
    with patch(
        "workers.ai_client.synthesize_speech",
        return_value=b"",
    ):
        with pytest.raises(RuntimeError, match="empty audio"):
            text_to_speech("Tell me about yourself.")
