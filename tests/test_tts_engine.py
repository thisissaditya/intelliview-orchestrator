from unittest.mock import MagicMock, patch

import pytest

from workers.tts_engine import synthesize_speech


def test_synthesize_speech_returns_audio_bytes():
    def fake_save_to_file(_text, path):
        with open(path, "wb") as audio_file:
            audio_file.write(b"fake-wav-data")

    mock_engine = MagicMock()
    mock_engine.save_to_file.side_effect = fake_save_to_file

    with patch("workers.tts_engine.pyttsx3.init", return_value=mock_engine):
        audio = synthesize_speech("Tell me about your experience with Python.")

    assert isinstance(audio, bytes)
    assert len(audio) > 0


def test_synthesize_speech_rejects_empty_text():
    with pytest.raises(ValueError, match=r"Text must not be empty\."):
        synthesize_speech("")
