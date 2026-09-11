import os
import tempfile

import pyttsx3


def synthesize_speech(text: str) -> bytes:
    """Convert text to speech and return the generated WAV audio as bytes."""
    if not text or not text.strip():
        raise ValueError("Text must not be empty.")

    engine = pyttsx3.init()

    try:
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_file:
            audio_path = temp_file.name

        engine.save_to_file(text, audio_path)
        engine.runAndWait()
        engine.stop()

        with open(audio_path, "rb") as audio_file:
            return audio_file.read()

    finally:
        if os.path.exists(audio_path):
            os.remove(audio_path)
