import numpy as np

from workers.audio_pipeline import StreamingWhisperTranscriber


def test_streaming_waits_for_complete_chunk(monkeypatch):
    calls = []

    def fake_transcribe(audio, raw_audio=False):
        calls.append(audio)
        return {
            "text": "hello",
            "language": "en",
            "segments": [],
        }

    monkeypatch.setattr(
        "workers.ai_client.transcribe_audio_file",
        fake_transcribe,
    )

    transcriber = StreamingWhisperTranscriber(
        sample_rate=16000,
        chunk_duration_ms=5000,
    )

    result = transcriber.add_chunk(np.zeros(16000 * 2, dtype=np.float32))

    assert result == []
    assert calls == []


def test_streaming_transcribes_complete_chunk(monkeypatch):
    calls = []

    def fake_transcribe(audio, raw_audio=False):
        calls.append(audio)
        return {
            "text": "hello",
            "language": "en",
            "segments": [],
        }

    monkeypatch.setattr(
        "workers.ai_client.transcribe_audio_file",
        fake_transcribe,
    )

    transcriber = StreamingWhisperTranscriber(
        sample_rate=16000,
        chunk_duration_ms=5000,
    )

    result = transcriber.add_chunk(np.zeros(16000 * 5, dtype=np.float32))

    assert len(result) == 1
    assert result[0]["text"] == "hello"
    assert len(calls) == 1
    assert len(calls[0]) == 16000 * 5


def test_streaming_keeps_remaining_audio_buffered(monkeypatch):
    calls = []

    def fake_transcribe(audio, raw_audio=False):
        calls.append(audio)
        return {
            "text": "chunk",
            "language": "en",
            "segments": [],
        }

    monkeypatch.setattr(
        "workers.ai_client.transcribe_audio_file",
        fake_transcribe,
    )

    transcriber = StreamingWhisperTranscriber(
        sample_rate=16000,
        chunk_duration_ms=5000,
    )

    result = transcriber.add_chunk(np.zeros(16000 * 7, dtype=np.float32))

    assert len(result) == 1
    assert len(calls) == 1
    assert len(calls[0]) == 16000 * 5


def test_streaming_finish_transcribes_remaining_audio(monkeypatch):
    def fake_transcribe(audio, raw_audio=False):
        return {
            "text": "remaining",
            "language": "en",
            "segments": [],
        }

    monkeypatch.setattr(
        "workers.ai_client.transcribe_audio_file",
        fake_transcribe,
    )

    transcriber = StreamingWhisperTranscriber(
        sample_rate=16000,
        chunk_duration_ms=5000,
    )

    transcriber.add_chunk(np.zeros(16000 * 2, dtype=np.float32))
    result = transcriber.finish()

    assert len(result) == 1
    assert result[0]["text"] == "remaining"


def test_streaming_empty_chunk_is_ignored(monkeypatch):
    calls = []

    def fake_transcribe(audio, raw_audio=False):
        calls.append(audio)
        return {
            "text": "hello",
            "language": "en",
            "segments": [],
        }

    monkeypatch.setattr(
        "workers.ai_client.transcribe_audio_file",
        fake_transcribe,
    )

    transcriber = StreamingWhisperTranscriber()

    result = transcriber.add_chunk(np.array([], dtype=np.float32))

    assert result == []
    assert calls == []
