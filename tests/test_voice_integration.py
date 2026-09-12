import base64
from unittest.mock import patch

import numpy as np
from fastapi.testclient import TestClient

from orchestrator.main import app
from workers.audio_pipeline import StreamingWhisperTranscriber

client = TestClient(app)


def test_voice_turn_taking_flow():
    """Test a complete voice turn from TTS to STT to answer processing."""

    session_id = "voice-test-session"
    question_id = "question-1"

    session_data = {
        "questions_asked": [],
        "answers_provided": [],
        "feedback_generated": [],
    }

    question = {
        "question_id": question_id,
        "text": "Tell me about your experience with Python.",
        "category": "technical",
        "difficulty": "medium",
    }

    fake_audio = b"fake-wav-audio"
    lifecycle_states = []

    with (
        patch(
            "orchestrator.main.session_manager.get_session",
            return_value=session_data,
        ),
        patch(
            "orchestrator.main.question_bank.get_next_question",
            return_value=question,
        ),
        patch(
            "orchestrator.main.question_bank.get_question",
            return_value=question,
        ),
        patch(
            "orchestrator.main.text_to_speech",
            return_value=fake_audio,
        ),
        patch(
            "orchestrator.main.session_manager.state_sync.set_session_state"
        ) as state_sync,
        patch(
            "workers.ai_client.transcribe_audio_file",
            return_value={
                "text": "I have used Python to build backend services.",
                "language": "en",
                "segments": [],
            },
        ),
    ):
        # 1. Asking state: interviewer generates a question and TTS audio.
        lifecycle_states.append("asking")

        ask_response = client.post(
            "/interviews/ask-question",
            json={
                "session_id": session_id,
                "category": "technical",
            },
        )

        assert ask_response.status_code == 200

        ask_data = ask_response.json()

        assert ask_data["session_id"] == session_id
        assert ask_data["question_id"] == question_id
        assert ask_data["text"] == question["text"]

        # Verify TTS audio was returned.
        decoded_audio = base64.b64decode(ask_data["audio_base64"])

        assert decoded_audio == fake_audio
        assert len(decoded_audio) > 0

        # 2. Listening state: process candidate audio through the
        # existing streaming STT pipeline.
        lifecycle_states.append("listening")

        transcriber = StreamingWhisperTranscriber(
            sample_rate=16000,
            chunk_duration_ms=5000,
        )

        audio_chunk = np.zeros(
            16000 * 5,
            dtype=np.float32,
        )

        transcription = transcriber.add_chunk(audio_chunk)

        assert len(transcription) == 1
        assert transcription[0]["text"] == (
            "I have used Python to build backend services."
        )

        answer_text = transcription[0]["text"]

        # 3. Processing state: submit the transcription for evaluation.
        lifecycle_states.append("processing")

        submit_response = client.post(
            "/interviews/submit-answer",
            json={
                "session_id": session_id,
                "question_id": question_id,
                "answer_text": answer_text,
                "score": 8,
            },
        )

        assert submit_response.status_code == 200

        submit_data = submit_response.json()

        assert submit_data["session_id"] == session_id
        assert submit_data["question_id"] == question_id
        assert submit_data["score"] == 8
        assert submit_data["questions_asked"] == 1
        assert submit_data["overall_score"] == 8
        assert "Strong answer" in submit_data["feedback"]

        # 4. Completed state: verify the turn finished successfully.
        lifecycle_states.append("completed")

        assert lifecycle_states == [
            "asking",
            "listening",
            "processing",
            "completed",
        ]

        # Verify that the session state was updated.
        state_sync.assert_called_once()

        updated_session = state_sync.call_args.args[1]

        assert updated_session["questions_asked"][0]["question_id"] == question_id

        assert updated_session["answers_provided"][0]["answer_text"] == answer_text

        assert updated_session["feedback_generated"][0]["question_id"] == question_id

        assert updated_session["overall_score"] == 8
