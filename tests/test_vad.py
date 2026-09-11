"""
Unit tests for Voice Activity Detection (VAD) engine and audio pipeline integration.
"""

import math
import os
import random
import struct
import tempfile
import wave

try:
    import numpy as np

    HAS_NUMPY = True
except ImportError:
    np = None
    HAS_NUMPY = False


from workers.audio_pipeline import detect_voice_activity, run_audio_analysis
from workers.vad import VADConfig, VoiceActivityDetector


def create_synthetic_wav(
    pattern: list[tuple[str, float]], sample_rate: int = 16000
) -> str:
    """Create a temporary WAV file with synthetic speech (sine wave) and silence.

    Pattern is a list of (type, duration_seconds) where type is 'speech' or 'silence'.
    """
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
        tmp_path = tmp.name

    total_samples = []
    for ptype, duration in pattern:
        num_samples = int(sample_rate * duration)
        if ptype == "speech":
            if HAS_NUMPY:
                t = np.linspace(0, duration, num_samples, endpoint=False)
                sine = (0.1414 * np.sin(2 * np.pi * 440 * t) * 32767).astype(np.int16)
                total_samples.extend(sine.tolist())
            else:
                for i in range(num_samples):
                    t = i / sample_rate
                    sample_val = int(0.1414 * math.sin(2 * math.pi * 440 * t) * 32767)
                    total_samples.append(sample_val)
        else:
            if HAS_NUMPY:
                zeros = (np.random.normal(0, 10, num_samples)).astype(np.int16)
                total_samples.extend(zeros.tolist())
            else:
                for _ in range(num_samples):
                    total_samples.append(random.randint(-10, 10))

    raw_bytes = struct.pack(f"<{len(total_samples)}h", *total_samples)

    with wave.open(tmp_path, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(raw_bytes)

    return tmp_path


def test_speech_and_silence_frame_detection():
    """Test individual speech vs silence frame classification."""
    detector = VoiceActivityDetector()

    # Generate 30ms speech frame (480 samples)
    if HAS_NUMPY:
        t = np.linspace(0, 0.03, 480, endpoint=False)
        speech_frame = (0.1414 * np.sin(2 * np.pi * 440 * t) * 32767).astype(np.int16)
        silence_frame = np.random.normal(0, 5, 480).astype(np.int16)
    else:
        speech_frame = [
            int(0.1414 * math.sin(2 * math.pi * 440 * (i / 16000)) * 32767)
            for i in range(480)
        ]
        silence_frame = [random.randint(-5, 5) for _ in range(480)]

    assert detector.is_speech_frame(speech_frame) is True
    assert detector.is_speech_frame(silence_frame) is False


def test_short_pause_does_not_trigger_end_of_speech():
    """Test that a short 300 ms pause after speech does NOT trigger speech_ended."""
    wav_path = create_synthetic_wav([("speech", 1.0), ("silence", 0.3)])

    try:
        detector = VoiceActivityDetector()
        result = detector.process_audio_file(wav_path)

        assert result["speech_ended"] is False
        assert result["total_speech_duration"] >= 0.9
        assert len(result["vad_segments"]) == 1
    finally:
        if os.path.exists(wav_path):
            os.remove(wav_path)


def test_sustained_silence_triggers_end_of_speech():
    """Test that sustained silence >= 800 ms after speech triggers speech_ended=True."""
    wav_path = create_synthetic_wav([("speech", 1.0), ("silence", 0.9)])

    try:
        detector = VoiceActivityDetector()
        result = detector.process_audio_file(wav_path)

        assert result["speech_ended"] is True
        assert result["total_speech_duration"] >= 0.9
        assert result["silence_duration"] >= 0.8
        assert len(result["vad_segments"]) == 1
    finally:
        if os.path.exists(wav_path):
            os.remove(wav_path)


def test_initial_silence_does_not_trigger_end_of_speech():
    """Test that audio with silence only produces speech_ended=False."""
    wav_path = create_synthetic_wav([("silence", 2.0)])

    try:
        detector = VoiceActivityDetector()
        result = detector.process_audio_file(wav_path)

        assert result["speech_ended"] is False
        assert result["total_speech_duration"] == 0.0
        assert result["vad_segments"] == []
    finally:
        if os.path.exists(wav_path):
            os.remove(wav_path)


def test_short_acoustic_artifacts_filtered():
    """Test that noise clicks shorter than min_speech_duration (300 ms) are ignored."""
    # 150ms noise click followed by 1.0s silence
    wav_path = create_synthetic_wav([("speech", 0.15), ("silence", 1.0)])

    try:
        detector = VoiceActivityDetector(config=VADConfig(min_speech_duration_ms=300))
        result = detector.process_audio_file(wav_path)

        assert result["speech_ended"] is False
        assert result["total_speech_duration"] == 0.0
        assert result["vad_segments"] == []
    finally:
        if os.path.exists(wav_path):
            os.remove(wav_path)


def test_speech_segment_duration_metrics():
    """Test metrics structure and calculation for multi-turn speech."""
    wav_path = create_synthetic_wav(
        [("speech", 0.8), ("silence", 0.4), ("speech", 1.2), ("silence", 1.0)]
    )

    try:
        detector = VoiceActivityDetector()
        result = detector.process_audio_file(wav_path)

        assert result["speech_ended"] is True
        assert len(result["vad_segments"]) == 2
        assert result["total_speech_duration"] >= 1.8
        assert result["silence_duration"] >= 0.9
    finally:
        if os.path.exists(wav_path):
            os.remove(wav_path)


def test_audio_pipeline_integration():
    """Test integration of VAD within workers/audio_pipeline.py."""
    wav_path = create_synthetic_wav([("speech", 1.2), ("silence", 1.0)])

    try:
        vad_result = detect_voice_activity(wav_path)
        assert "speech_ended" in vad_result
        assert "total_speech_duration" in vad_result
        assert "silence_duration" in vad_result
        assert "vad_segments" in vad_result
        assert vad_result["speech_ended"] is True

        analysis = run_audio_analysis(wav_path)
        assert "vad_analysis" in analysis
        assert analysis["vad_analysis"]["speech_ended"] is True
    finally:
        if os.path.exists(wav_path):
            os.remove(wav_path)
