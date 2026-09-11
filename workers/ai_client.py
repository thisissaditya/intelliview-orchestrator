"""
AI Client Module
Provides pluggable clients for OpenAI, Whisper, and MediaPipe/OpenCV
with automatic fallback to mocks when API keys or libraries are absent.
Includes token usage tracking for OpenAI, Gemini, and Grok calls.
"""

import logging
import os
import time
from typing import Any

from workers.tts_engine import synthesize_speech

logger = logging.getLogger(__name__)
AUDIO_MAX_RETRIES = int(os.getenv("AUDIO_MAX_RETRIES", "3"))
AUDIO_RETRY_BASE_DELAY = float(os.getenv("AUDIO_RETRY_BASE_DELAY", "0.5"))


def _retry_with_backoff(operation, operation_name: str):
    """Run a transient audio operation with bounded exponential backoff."""
    for attempt in range(1, AUDIO_MAX_RETRIES + 1):
        try:
            return operation()
        except Exception as exc:
            if attempt == AUDIO_MAX_RETRIES:
                logger.warning(
                    "%s failed after %d attempts: %s",
                    operation_name,
                    attempt,
                    exc,
                )
                break

            delay = AUDIO_RETRY_BASE_DELAY * (2 ** (attempt - 1))
            logger.warning(
                "%s failed on attempt %d/%d; retrying in %.2fs: %s",
                operation_name,
                attempt,
                AUDIO_MAX_RETRIES,
                delay,
                exc,
            )
            time.sleep(delay)

    return None


# ---------------------------------------------------------------------------
# Feature detection â€” import optional dependencies at module level so the
# rest of the codebase can branch on `HAS_OPENAI`, `HAS_WHISPER`, etc.
# ---------------------------------------------------------------------------

try:
    from openai import OpenAI

    _openai_api_key = os.getenv("OPENAI_API_KEY", "")
    if _openai_api_key:
        openai_client = OpenAI(api_key=_openai_api_key)
        HAS_OPENAI = True
        logger.info("OpenAI client initialised (API key detected)")
    else:
        openai_client = None
        HAS_OPENAI = False
        logger.info("No OPENAI_API_KEY â€” OpenAI client unavailable")
except ImportError:
    openai_client = None
    HAS_OPENAI = False
    logger.info("openai package not installed â€” OpenAI client unavailable")

try:
    import google.generativeai as genai

    _gemini_api_key = os.getenv("GEMINI_API_KEY", "")
    if _gemini_api_key:
        genai.configure(api_key=_gemini_api_key)
        gemini_model = genai.GenerativeModel("gemini-2.0-flash")
        HAS_GEMINI = True
        logger.info("Gemini client initialised (API key detected)")
    else:
        gemini_model = None
        HAS_GEMINI = False
        logger.info("No GEMINI_API_KEY â€” Gemini client unavailable")
except ImportError:
    gemini_model = None
    HAS_GEMINI = False
    logger.info("google-generativeai not installed â€” Gemini client unavailable")

try:
    from openai import OpenAI as GrokClient

    _grok_api_key = os.getenv("GROK_API_KEY", "")
    if _grok_api_key:
        grok_client = GrokClient(
            api_key=_grok_api_key,
            base_url="https://api.x.ai/v1",
        )
        HAS_GROK = True
        logger.info("Grok client initialised (API key detected)")
    else:
        grok_client = None
        HAS_GROK = False
        logger.info("No GROK_API_KEY â€” Grok client unavailable")
except ImportError:
    grok_client = None
    HAS_GROK = False
    logger.info("openai package not installed â€” Grok client unavailable")

try:
    import whisper  # type: ignore

    whisper_model_name = os.getenv("WHISPER_MODEL", "base")
    whisper_model = whisper.load_model(whisper_model_name)
    HAS_WHISPER = True
    logger.info("Whisper model loaded: %s", whisper_model_name)
except Exception:
    whisper_model = None
    HAS_WHISPER = False
    logger.info("Whisper not available â€” falling back to mock STT")

try:
    import cv2
    import mediapipe as mp  # type: ignore

    HAS_MEDIAPIPE = True
    logger.info("MediaPipe + OpenCV available")
except ImportError:
    HAS_MEDIAPIPE = False
    logger.info(
        "MediaPipe/OpenCV not installed â€” falling back to mock face detection"
    )

try:
    import pyttsx3

    _tts_engine = pyttsx3.init()
    _tts_engine.setProperty("rate", 175)  # speaking speed (words per minute)
    _tts_engine.setProperty("volume", 1.0)  # volume 0.0 to 1.0
    HAS_TTS = True
    logger.info("pyttsx3 TTS engine initialised successfully")
except Exception:
    _tts_engine = None
    HAS_TTS = False
    logger.info("pyttsx3 not available — TTS will be skipped")


# ---------------------------------------------------------------------------
# Helper function to construct standard usage dictionary
# ---------------------------------------------------------------------------


def _build_usage_dict(
    provider: str,
    model: str,
    prompt_tokens: int = 0,
    completion_tokens: int = 0,
    total_tokens: int = 0,
) -> dict[str, Any]:
    """Helper to structure token usage and estimated cost metadata."""
    if not total_tokens:
        total_tokens = prompt_tokens + completion_tokens

    return {
        "provider": provider,
        "model": model,
        "prompt_tokens": prompt_tokens,
        "completion_tokens": completion_tokens,
        "total_tokens": total_tokens,
    }


# ---------------------------------------------------------------------------
# OpenAI helpers
# ---------------------------------------------------------------------------


def chat_completion(
    messages: list[dict[str, str]],
    *,
    model: str = "gpt-4o",
    temperature: float = 0.7,
    max_tokens: int = 1024,
) -> tuple[str | None, dict[str, Any]]:
    """
    Send a chat completion request to OpenAI.
    Returns a tuple: (content_text or None, usage_dict).
    """
    if not HAS_OPENAI:
        return None, _build_usage_dict("openai", model)
    try:
        resp = openai_client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        content = resp.choices[0].message.content

        usage = _build_usage_dict("openai", model)
        if getattr(resp, "usage", None):
            usage = _build_usage_dict(
                provider="openai",
                model=model,
                prompt_tokens=getattr(resp.usage, "prompt_tokens", 0),
                completion_tokens=getattr(resp.usage, "completion_tokens", 0),
                total_tokens=getattr(resp.usage, "total_tokens", 0),
            )

        logger.info(
            "OpenAI call finished [%s] â€” Tokens: Prompt=%d, Completion=%d, Total=%d",
            model,
            usage["prompt_tokens"],
            usage["completion_tokens"],
            usage["total_tokens"],
        )
        return content, usage
    except Exception as exc:
        logger.warning("OpenAI chat completion failed: %s", exc)
        return None, _build_usage_dict("openai", model)


# ---------------------------------------------------------------------------
# Gemini helpers
# ---------------------------------------------------------------------------


def gemini_generate(
    prompt: str,
    *,
    temperature: float = 0.7,
    max_output_tokens: int = 1024,
) -> tuple[str | None, dict[str, Any]]:
    """
    Generate text using Gemini.
    Returns a tuple: (content_text or None, usage_dict).
    """
    model_name = "gemini-2.0-flash"
    if not HAS_GEMINI:
        return None, _build_usage_dict("google", model_name)
    try:
        response = gemini_model.generate_content(
            prompt,
            generation_config=genai.types.GenerationConfig(
                temperature=temperature,
                max_output_tokens=max_output_tokens,
            ),
        )
        content = response.text

        prompt_tokens = 0
        completion_tokens = 0
        total_tokens = 0

        if hasattr(response, "usage_metadata") and response.usage_metadata:
            prompt_tokens = getattr(response.usage_metadata, "prompt_token_count", 0)
            completion_tokens = getattr(
                response.usage_metadata, "candidates_token_count", 0
            )
            total_tokens = getattr(response.usage_metadata, "total_token_count", 0)

        usage = _build_usage_dict(
            provider="google",
            model=model_name,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total_tokens,
        )

        logger.info(
            "Gemini generation finished [%s] â€” Tokens: Prompt=%d, Completion=%d, Total=%d",
            model_name,
            usage["prompt_tokens"],
            usage["completion_tokens"],
            usage["total_tokens"],
        )
        return content, usage
    except Exception as exc:
        logger.warning("Gemini generation failed: %s", exc)
        return None, _build_usage_dict("google", model_name)


def gemini_chat(
    messages: list[dict[str, str]],
    *,
    temperature: float = 0.7,
    max_output_tokens: int = 1024,
) -> tuple[str | None, dict[str, Any]]:
    """
    Multi-turn chat with Gemini.
    Returns a tuple: (response_text or None, usage_dict).
    """
    model_name = "gemini-2.0-flash"
    if not HAS_GEMINI:
        return None, _build_usage_dict("google", model_name)
    try:
        chat = gemini_model.start_chat(history=[])
        response = None
        for msg in messages:
            if msg["role"] == "user":
                response = chat.send_message(msg["content"])
            elif msg["role"] == "assistant":
                pass

        content = chat.last.text if chat.last else None

        prompt_tokens = 0
        completion_tokens = 0
        total_tokens = 0

        if response and hasattr(response, "usage_metadata") and response.usage_metadata:
            prompt_tokens = getattr(response.usage_metadata, "prompt_token_count", 0)
            completion_tokens = getattr(
                response.usage_metadata, "candidates_token_count", 0
            )
            total_tokens = getattr(response.usage_metadata, "total_token_count", 0)

        usage = _build_usage_dict(
            provider="google",
            model=model_name,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total_tokens,
        )

        logger.info(
            "Gemini chat finished [%s] â€” Tokens: Prompt=%d, Completion=%d, Total=%d",
            model_name,
            usage["prompt_tokens"],
            usage["completion_tokens"],
            usage["total_tokens"],
        )
        return content, usage
    except Exception as exc:
        logger.warning("Gemini chat failed: %s", exc)
        return None, _build_usage_dict("google", model_name)


# ---------------------------------------------------------------------------
# Grok helpers
# ---------------------------------------------------------------------------


def grok_completion(
    messages: list[dict[str, str]],
    *,
    model: str = "grok-2-1212",
    temperature: float = 0.7,
    max_tokens: int = 1024,
) -> tuple[str | None, dict[str, Any]]:
    """
    Send a chat completion request to Grok.
    Returns a tuple: (content_text or None, usage_dict).
    """
    if not HAS_GROK:
        return None, _build_usage_dict("grok", model)
    try:
        resp = grok_client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        content = resp.choices[0].message.content

        usage = _build_usage_dict("grok", model)
        if getattr(resp, "usage", None):
            usage = _build_usage_dict(
                provider="grok",
                model=model,
                prompt_tokens=getattr(resp.usage, "prompt_tokens", 0),
                completion_tokens=getattr(resp.usage, "completion_tokens", 0),
                total_tokens=getattr(resp.usage, "total_tokens", 0),
            )

        logger.info(
            "Grok completion finished [%s] â€” Tokens: Prompt=%d, Completion=%d, Total=%d",
            model,
            usage["prompt_tokens"],
            usage["completion_tokens"],
            usage["total_tokens"],
        )
        return content, usage
    except Exception as exc:
        logger.warning("Grok completion failed: %s", exc)
        return None, _build_usage_dict("grok", model)


# ---------------------------------------------------------------------------
# Text-to-Speech helpers
# ---------------------------------------------------------------------------


def text_to_speech(text: str) -> bytes:
    """Convert interview question text to WAV audio bytes.

    Raises:
        ValueError: If the input text is empty.
        RuntimeError: If speech synthesis fails.
    """
    if not text or not text.strip():
        raise ValueError("TTS text must not be empty.")

    try:
        audio = synthesize_speech(text)
        if not audio:
            raise RuntimeError("TTS synthesis returned empty audio.")

        return audio
    except ValueError:
        raise
    except Exception as exc:
        logger.error("TTS synthesis failed: %s", exc)
        raise RuntimeError(f"TTS synthesis failed: {exc}") from exc


# ---------------------------------------------------------------------------
# Whisper helpers
# ---------------------------------------------------------------------------


def transcribe_audio_file(
    audio_path: str,
    vad_config: Any | None = None,
    speech_segments: list[Any] | None = None,
    raw_audio: bool = False,
) -> dict[str, Any] | None:
    """Transcribe an audio file using VAD pre-filtering and local Whisper.

    Executes VAD pre-filtering and sends ONLY extracted speech segments to Whisper:
    - Silent or near-silent audio files skip Whisper execution completely.
    - Mid-file silence is trimmed out; only speech chunk arrays are passed to Whisper.
    - Preserves timestamps aligned with the original recording.
    """
    if not HAS_WHISPER:
        return None

    try:
        from workers.vad import VoiceActivityDetector

        detector = VoiceActivityDetector(vad_config)

        if raw_audio:
            result = _retry_with_backoff(
                lambda: whisper_model.transcribe(audio_path),
                "Whisper audio transcription",
            )

            if result is None:
                return None

            return {
                "text": result.get("text", "").strip(),
                "language": result.get("language", "en"),
                "segments": result.get("segments", []),
                "silence_only": False,
                "vad_segments": [],
                "total_speech_duration": 0.0,
            }

        if speech_segments is None:
            speech_segments = detector.process_audio(audio_path)

        if len(speech_segments) == 0:
            logger.info(
                "VAD detected silence only in %s - skipping Whisper transcription.",
                audio_path,
            )
            return {
                "text": "",
                "language": "en",
                "segments": [],
                "silence_only": True,
                "vad_segments": [],
                "total_speech_duration": 0.0,
            }

        all_texts = []
        aligned_whisper_segments = []
        detected_language = "en"

        for seg in speech_segments:
            samples = getattr(seg, "audio_samples", None)

            if samples is None and os.path.exists(audio_path):
                raw_samples, sr = detector._load_samples(
                    audio_path,
                    detector.config.sample_rate,
                )

                if len(raw_samples) > 0:
                    start_sec = getattr(
                        seg,
                        "start",
                        seg.get("start", 0.0) if isinstance(seg, dict) else 0.0,
                    )
                    end_sec = getattr(
                        seg,
                        "end",
                        seg.get("end", 0.0) if isinstance(seg, dict) else 0.0,
                    )

                    start_idx = int(start_sec * sr)
                    end_idx = min(len(raw_samples), int(end_sec * sr))
                    samples = raw_samples[start_idx:end_idx]

            if samples is None or len(samples) == 0:
                continue

            seg_result = _retry_with_backoff(
                lambda samples=samples: whisper_model.transcribe(samples),
                "Whisper segment transcription",
            )

            if seg_result is None:
                continue

            seg_text = seg_result.get("text", "").strip()

            if seg_text:
                all_texts.append(seg_text)

            detected_language = seg_result.get(
                "language",
                detected_language,
            )

            seg_start = getattr(
                seg,
                "start",
                seg.get("start", 0.0) if isinstance(seg, dict) else 0.0,
            )

            for w_seg in seg_result.get("segments", []):
                aligned_w_seg = dict(w_seg)
                aligned_w_seg["start"] = round(
                    seg_start + w_seg.get("start", 0.0),
                    3,
                )
                aligned_w_seg["end"] = round(
                    seg_start + w_seg.get("end", 0.0),
                    3,
                )
                aligned_whisper_segments.append(aligned_w_seg)

        combined_text = " ".join(all_texts).strip()

        vad_summary = [
            s.to_dict() if hasattr(s, "to_dict") else s for s in speech_segments
        ]

        speech_duration = sum(
            getattr(
                s,
                "duration",
                s.get("duration", 0.0) if isinstance(s, dict) else 0.0,
            )
            for s in speech_segments
        )

        return {
            "text": combined_text,
            "language": detected_language,
            "segments": aligned_whisper_segments,
            "silence_only": not bool(combined_text),
            "vad_segments": vad_summary,
            "total_speech_duration": speech_duration,
        }

    except Exception as exc:
        logger.warning("Whisper transcription failed: %s", exc)
        return None


def detect_speaker_segments(audio_path: str) -> list[dict[str, Any]] | None:
    """Return speaker-turn segments (start, end, speaker_id).

    Falls back to simple silence-based segmentation when pyannote is not
    available.
    """
    try:
        from pyannote.audio import Pipeline  # type: ignore

        diarization = Pipeline.from_pretrained(
            "pyannote/speaker-diarization-3.1",
            use_auth_token=os.getenv("HF_TOKEN", ""),
        )
        diarization = diarization.to("cuda" if _cuda_available() else "cpu")
        hypothesis = diarization(audio_path)
        segments = []
        for turn, _, speaker in hypothesis.itertracks(yield_label=True):
            segments.append(
                {"start": turn.start, "end": turn.end, "speaker_id": speaker}
            )
        return segments
    except Exception:
        return None


def _cuda_available() -> bool:
    try:
        import torch

        return torch.cuda.is_available()
    except Exception:
        return False


# ---------------------------------------------------------------------------
# Face / vision helpers
# ---------------------------------------------------------------------------


def detect_faces_in_frame(
    frame_bytes: bytes | None = None, frame_path: str = ""
) -> dict[str, Any] | None:
    """Detect faces in a single frame using MediaPipe.

    Accepts raw bytes or a file path. Returns dict with face_count,
    bounding boxes, and confidence, or None if unavailable.
    """
    if not HAS_MEDIAPIPE:
        return None
    try:
        if frame_bytes:
            import numpy as np

            arr = np.frombuffer(frame_bytes, dtype=np.uint8)
            image = cv2.imdecode(arr, cv2.IMREAD_COLOR)
        elif frame_path:
            image = cv2.imread(frame_path)
        else:
            return None
        if image is None:
            return None

        rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        with mp.solutions.face_detection.FaceDetection(
            model_selection=1, min_detection_confidence=0.5
        ) as fd:
            results = fd.process(rgb)
            detections = []
            if results.detections:
                for det in results.detections:
                    bbox = det.location_data.relative_bounding_box
                    detections.append(
                        {
                            "x": bbox.xmin,
                            "y": bbox.ymin,
                            "w": bbox.width,
                            "h": bbox.height,
                            "confidence": det.score[0],
                        }
                    )
            return {"face_count": len(detections), "faces": detections}
    except Exception as exc:
        logger.warning("MediaPipe face detection failed: %s", exc)
        return None


def detect_hand_gaze(
    frame_bytes: bytes | None = None, frame_path: str = ""
) -> dict[str, Any] | None:
    """Detect hand/palm positions that may indicate phone use, using MediaPipe Hands."""
    if not HAS_MEDIAPIPE:
        return None
    try:
        if frame_bytes:
            import numpy as np

            arr = np.frombuffer(frame_bytes, dtype=np.uint8)
            image = cv2.imdecode(arr, cv2.IMREAD_COLOR)
        elif frame_path:
            image = cv2.imread(frame_path)
        else:
            return None
        if image is None:
            return None

        rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        with mp.solutions.hands.Hands(
            static_image_mode=True, max_num_hands=4, min_detection_confidence=0.5
        ) as hands:
            results = hands.process(rgb)
            hand_count = 0
            if results.multi_hand_landmarks:
                hand_count = len(results.multi_hand_landmarks)
            return {
                "hands_detected": hand_count,
                "possibly_holding_phone": hand_count >= 2,
            }
    except Exception as exc:
        logger.warning("MediaPipe hand detection failed: %s", exc)
        return None


def speak_text(text: str) -> bool:
    """
    Convert text to speech using pyttsx3 (local, no API key required).

    This is the v1 TTS provider. It runs entirely offline and requires
    no external dependency or API key.

    Args:
        text: The question or text string to be spoken aloud.

    Returns:
        True if speech synthesis succeeded, False otherwise.

    Upgrade path:
        For v2, replace pyttsx3 with a cloud TTS provider such as:
        - Google Cloud Text-to-Speech (natural voices, SSML support)
        - AWS Polly (low latency, neural voices)
        - ElevenLabs (most natural, emotion-aware)
        See docs/tts-upgrade-path.md for full trade-off comparison.
    """
    if not HAS_TTS:
        logger.warning("TTS unavailable — pyttsx3 not installed")
        return False

    if not text or not text.strip():
        logger.warning("speak_text() called with empty text — skipping")
        return False

    try:
        _tts_engine.say(text)
        _tts_engine.runAndWait()
        logger.info("TTS spoke successfully: %.50s...", text)
        return True
    except Exception as exc:
        logger.warning("TTS speak_text() failed: %s", exc)
        return False


# ----------------------------------------------
# TTS (Text-to-Speech) — pyttsx3 local provider
# ----------------------------------------------


def speak_text_to_file(text: str, output_path: str) -> bool:
    """
    Save synthesized speech to an audio file (.mp3 or .wav).

    Useful when the frontend needs to play audio from a URL
    instead of triggering local system speakers.

    Args:
        text: Text to synthesize.
        output_path: File path to save audio (e.g. 'output.mp3')

    Returns:
        True if file was saved successfully, False otherwise.
    """
    if not HAS_TTS:
        logger.warning("TTS unavailable — pyttsx3 not installed")
        return False

    if not text or not text.strip():
        logger.warning("speak_text_to_file() called with empty text — skipping")
        return False

    try:
        _tts_engine.save_to_file(text, output_path)
        _tts_engine.runAndWait()
        logger.info("TTS audio saved to: %s", output_path)
        return True
    except Exception as exc:
        logger.warning("TTS save_to_file() failed: %s", exc)
        return False
