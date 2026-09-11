"""
Voice Activity Detection (VAD) Engine for Interview Audio Analysis.

Responsibilities:
- Frame-based RMS energy calculation with adaptive noise-floor estimation
- Reliable speech segment extraction and boundary detection
- Sensitivity-tuned end-of-speech detection (avoids premature cutoffs on short pauses,
  triggers speech_ended on sustained silence after speech)
"""

import logging
import math
import os
import struct
import wave
from dataclasses import dataclass
from typing import Any, TypedDict

try:
    import numpy as np

    HAS_NUMPY = True
except ImportError:
    np = None
    HAS_NUMPY = False

logger = logging.getLogger(__name__)


class VADSegmentDict(TypedDict):
    start: float
    end: float
    duration: float


class VADResult(TypedDict):
    speech_ended: bool
    total_speech_duration: float
    silence_duration: float
    vad_segments: list[VADSegmentDict]


@dataclass
class VADConfig:
    sample_rate: int = 16000
    frame_duration_ms: int = 30
    min_speech_duration_ms: int = 300
    silence_duration_ms: int = 800
    energy_threshold_scale: float = 2.5
    min_energy_threshold: float = 0.005

    @property
    def frame_size(self) -> int:
        """Number of audio samples per frame."""
        return int(self.sample_rate * (self.frame_duration_ms / 1000.0))


class VoiceActivityDetector:
    """Detects voice activity and speech boundaries using RMS energy and adaptive noise floor."""

    def __init__(self, config: VADConfig | None = None):
        self.config = config or VADConfig()

    def calculate_rms(self, frame_samples: Any) -> float:
        """Calculate Root Mean Square (RMS) energy of an audio frame."""
        if HAS_NUMPY and isinstance(frame_samples, np.ndarray):
            if len(frame_samples) == 0:
                return 0.0
            if frame_samples.dtype == np.int16:
                samples = frame_samples.astype(np.float32) / 32768.0
            elif frame_samples.dtype == np.int32:
                samples = frame_samples.astype(np.float32) / 2147483648.0
            else:
                samples = frame_samples.astype(np.float32)
            return float(np.sqrt(np.mean(np.square(samples))))

        if not frame_samples:
            return 0.0

        if isinstance(frame_samples, bytes):
            count = len(frame_samples) // 2
            if count == 0:
                return 0.0
            unpacked = struct.unpack(f"<{count}h", frame_samples[: count * 2])
            float_samples = [s / 32768.0 for s in unpacked]
        elif isinstance(frame_samples, list | tuple):
            float_samples = [
                s / 32768.0 if isinstance(s, int) else float(s) for s in frame_samples
            ]
        else:
            float_samples = [float(s) for s in frame_samples]

        if not float_samples:
            return 0.0

        mean_sq = sum(s * s for s in float_samples) / len(float_samples)
        return math.sqrt(mean_sq)

    def _estimate_noise_floor(self, frames: list[Any]) -> float:
        """Estimate ambient noise floor from lowest energy frames."""
        if not frames:
            return self.config.min_energy_threshold

        rms_values = [self.calculate_rms(f) for f in frames]
        rms_values.sort()

        p20_idx = int(len(rms_values) * 0.2)
        noise_floor = (
            rms_values[p20_idx] if rms_values else self.config.min_energy_threshold
        )

        return max(
            noise_floor * self.config.energy_threshold_scale,
            self.config.min_energy_threshold,
        )

    def is_speech_frame(self, frame: Any, threshold: float | None = None) -> bool:
        """Determine whether a single frame contains speech."""
        rms = self.calculate_rms(frame)
        thresh = (
            threshold if threshold is not None else self.config.min_energy_threshold
        )
        return rms >= thresh

    def process_samples(
        self, samples: Any, sample_rate: int | None = None
    ) -> VADResult:
        """Process floating point or integer audio samples."""
        sr = sample_rate or self.config.sample_rate
        frame_size = int(sr * (self.config.frame_duration_ms / 1000.0))

        if len(samples) == 0:
            return {
                "speech_ended": False,
                "total_speech_duration": 0.0,
                "silence_duration": 0.0,
                "vad_segments": [],
            }

        frames = [
            samples[i : i + frame_size]
            for i in range(0, len(samples), frame_size)
            if len(samples[i : i + frame_size]) == frame_size
        ]

        if not frames:
            return {
                "speech_ended": False,
                "total_speech_duration": 0.0,
                "silence_duration": 0.0,
                "vad_segments": [],
            }

        threshold = self._estimate_noise_floor(frames)
        frame_duration_sec = self.config.frame_duration_ms / 1000.0
        min_speech_frames = int(
            math.ceil(
                (self.config.min_speech_duration_ms / 1000.0) / frame_duration_sec
            )
        )
        silence_target_frames = int(
            math.ceil((self.config.silence_duration_ms / 1000.0) / frame_duration_sec)
        )

        raw_speech_flags = [self.calculate_rms(f) >= threshold for f in frames]

        raw_segments: list[tuple[int, int]] = []
        in_speech = False
        start_idx = 0

        for i, is_speech in enumerate(raw_speech_flags):
            if is_speech and not in_speech:
                in_speech = True
                start_idx = i
            elif not is_speech and in_speech:
                in_speech = False
                raw_segments.append((start_idx, i))

        if in_speech:
            raw_segments.append((start_idx, len(raw_speech_flags)))

        valid_segments: list[tuple[int, int]] = []
        for start, end in raw_segments:
            duration_frames = end - start
            if duration_frames >= min_speech_frames:
                valid_segments.append((start, end))

        vad_segments: list[VADSegmentDict] = [
            {
                "start": round(start * frame_duration_sec, 3),
                "end": round(end * frame_duration_sec, 3),
                "duration": round((end - start) * frame_duration_sec, 3),
            }
            for start, end in valid_segments
        ]

        total_speech_duration = round(sum(seg["duration"] for seg in vad_segments), 3)

        speech_ended = False
        silence_duration = 0.0

        if valid_segments:
            last_speech_end_frame = valid_segments[-1][1]
            tail_silence_frames = len(raw_speech_flags) - last_speech_end_frame
            silence_duration = round(tail_silence_frames * frame_duration_sec, 3)

            if tail_silence_frames >= silence_target_frames:
                speech_ended = True

        return {
            "speech_ended": speech_ended,
            "total_speech_duration": total_speech_duration,
            "silence_duration": silence_duration,
            "vad_segments": vad_segments,
        }

    def process_audio_file(self, audio_path: str) -> VADResult:
        """Read a WAV file and process VAD."""
        if not os.path.exists(audio_path):
            logger.warning("Audio file not found for VAD: %s", audio_path)
            return {
                "speech_ended": False,
                "total_speech_duration": 0.0,
                "silence_duration": 0.0,
                "vad_segments": [],
            }

        try:
            with wave.open(audio_path, "rb") as wf:
                sr = wf.getframerate()
                sampwidth = wf.getsampwidth()
                n_channels = wf.getnchannels()
                n_frames = wf.getnframes()
                raw_bytes = wf.readframes(n_frames)

                if HAS_NUMPY:
                    if sampwidth == 2:
                        samples = np.frombuffer(raw_bytes, dtype=np.int16)
                    elif sampwidth == 4:
                        samples = np.frombuffer(raw_bytes, dtype=np.int32)
                    else:
                        samples = (
                            np.frombuffer(raw_bytes, dtype=np.uint8).astype(np.float32)
                            - 128
                        )
                    if n_channels > 1 and len(samples) > 0:
                        samples = samples[::n_channels]
                else:
                    if sampwidth == 2:
                        count = len(raw_bytes) // 2
                        samples = list(struct.unpack(f"<{count}h", raw_bytes))
                    else:
                        samples = [float(b - 128) for b in raw_bytes]
                    if n_channels > 1 and len(samples) > 0:
                        samples = samples[::n_channels]

                return self.process_samples(samples, sample_rate=sr)

        except Exception as exc:
            logger.warning(
                "VAD audio file processing failed for %s: %s", audio_path, exc
            )
            return {
                "speech_ended": False,
                "total_speech_duration": 0.0,
                "silence_duration": 0.0,
                "vad_segments": [],
            }
