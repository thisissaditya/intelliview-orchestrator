"""
Risk Scoring Engine
Combines signals from all pipelines to calculate final interview risk score

Responsibilities:
- Normalize signals from different pipelines
- Generate weighted risk score (for reporting)
- Classify interview risk using a decision tree
- Generate final interview risk report

All weights and thresholds are configurable via RISK_CONFIG, a single
source of truth for every numeric constant in the scoring pipeline.

Anti-cheat integrity_score schema (D2)
---------------------------------------
The externally consumed ``integrity_score`` is an integer from 0 to 100,
where 100 means no suspicious activity was observed and 0 means the maximum
combined penalty was observed. The signal budget is:

* tab-switch: 20% (maximum 20-point penalty)
* gaze/face: 30% (maximum 30-point penalty)
* risk: 50% (maximum 50-point penalty)

The score bands are defined in ``docs/integrity-score-schema.md`` and are
the contract for backend responses and frontend interpretation. This section
documents the schema only; it does not implement the fusion algorithm.
"""

import logging
import os
from typing import Any

from workers.risk_override import RiskOverrideEngine

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Single-source risk configuration — all weights & thresholds here.
# Override via environment variables (prefix RISK_), e.g.
#   RISK_VIDEO_WEIGHT=0.4 RISK_LOW_RISK_THRESHOLD=0.3
# ---------------------------------------------------------------------------


class RiskScoringEngine:
    """
    Calculates comprehensive risk scores from interview analysis results.
    Reads numeric constants dynamically from environment variables.
    """

    @classmethod
    def get_pipeline_weights(cls) -> tuple[float, float, float]:
        return (
            float(os.getenv("RISK_VIDEO_WEIGHT", "0.4")),
            float(os.getenv("RISK_AUDIO_WEIGHT", "0.3")),
            float(os.getenv("RISK_EVALUATION_WEIGHT", "0.3")),
        )

    @classmethod
    def get_thresholds(cls) -> tuple[float, float, float]:
        return (
            float(os.getenv("RISK_LOW_RISK_THRESHOLD", "0.3")),
            float(os.getenv("RISK_MEDIUM_RISK_THRESHOLD", "0.6")),
            float(os.getenv("RISK_HIGH_RISK_THRESHOLD", "0.8")),
        )

    @classmethod
    def get_video_factors(cls) -> dict[str, float]:
        return {
            "multiple_persons": float(os.getenv("RISK_VIDEO_MULTIPLE_PERSONS", "0.35")),
            "phone_detected": float(os.getenv("RISK_VIDEO_PHONE_DETECTED", "0.25")),
            "suspicious_head_movement": float(
                os.getenv("RISK_VIDEO_SUSPICIOUS_HEAD", "0.20")
            ),
            "no_face_detected": float(os.getenv("RISK_VIDEO_NO_FACE", "0.45")),
        }

    @classmethod
    def get_audio_factors(cls) -> dict[str, float]:
        return {
            "background_voices": float(
                os.getenv("RISK_AUDIO_BACKGROUND_VOICES", "0.35")
            ),
            "suspicious_pattern": float(
                os.getenv("RISK_AUDIO_SUSPICIOUS_PATTERN", "0.25")
            ),
            "no_transcription": float(os.getenv("RISK_AUDIO_NO_TRANSCRIPTION", "0.40")),
        }

    @classmethod
    def get_evaluation_factors(cls) -> dict[str, float]:
        return {
            "low_quality_answers": float(os.getenv("RISK_EVAL_LOW_QUALITY", "0.30")),
            "low_accuracy": float(os.getenv("RISK_EVAL_LOW_ACCURACY", "0.40")),
            "poor_communication": float(
                os.getenv("RISK_EVAL_POOR_COMMUNICATION", "0.20")
            ),
            "hallucination": float(os.getenv("RISK_EVAL_HALLUCINATION", "0.30")),
        }

    @classmethod
    def calculate_video_risk(cls, video_result: dict[str, Any]) -> float:
        """Calculate risk score from video analysis."""
        risk_score = 0.0
        factors = cls.get_video_factors()

        if video_result.get("multiple_persons", {}).get("multiple_persons_detected"):
            risk_score += factors["multiple_persons"]

        if video_result.get("phone_detected", {}).get("phone_detected"):
            risk_score += factors["phone_detected"]

        if video_result.get("head_movement_suspicious", {}).get(
            "suspicious_movement_detected"
        ):
            risk_score += factors["suspicious_head_movement"]

        if not video_result.get("face_detected", {}).get("faces_found"):
            risk_score += factors["no_face_detected"]

        return min(risk_score, 1.0)

    @classmethod
    def calculate_audio_risk(cls, audio_result: dict[str, Any]) -> float:
        """Calculate risk score from audio analysis."""
        risk_score = 0.0
        factors = cls.get_audio_factors()

        if audio_result.get("background_voices", {}).get("background_voices_detected"):
            risk_score += factors["background_voices"]

        if audio_result.get("suspicious_conversation", {}).get(
            "suspicious_pattern_detected"
        ):
            risk_score += factors["suspicious_pattern"]

        if not audio_result.get("transcription", {}).get("text"):
            risk_score += factors["no_transcription"]

        return min(risk_score, 1.0)

    @classmethod
    def calculate_evaluation_risk(cls, evaluation_result: dict[str, Any]) -> float:
        """Calculate risk score from answer evaluation."""
        risk_score = 0.0
        factors = cls.get_evaluation_factors()

        quality_score = evaluation_result.get("answer_quality_score", {}).get(
            "overall_quality_score", 50
        )
        accuracy_score = evaluation_result.get("technical_accuracy", {}).get(
            "accuracy_score", 50
        )
        clarity_score = evaluation_result.get("communication_clarity", {}).get(
            "clarity_score", 50
        )
        hallucination_flagged = evaluation_result.get("hallucination_check", {}).get(
            "is_hallucination", False
        )

        if quality_score < 40:
            risk_score += factors["low_quality_answers"]
        if accuracy_score < 40:
            risk_score += factors["low_accuracy"]
        if clarity_score < 40:
            risk_score += factors["poor_communication"]
        if hallucination_flagged:
            risk_score += factors["hallucination"]

        return min(risk_score, 1.0)

    @classmethod
    def count_video_flags(cls, video_result: dict[str, Any] | None) -> int:
        """Count discrete cheat-signal flags set in a video analysis result.

        This mirrors the same boolean checks used in ``calculate_video_risk``,
        but returns a plain integer count rather than a weighted score. It is
        used as the ``cv_flags`` input to the integrity-score fusion (see
        ``workers/integrity_score.py``), which is surfaced live through the
        session-status API as new video signal data comes in.
        """
        if not video_result:
            return 0

        flags = 0

        if video_result.get("multiple_persons", {}).get("multiple_persons_detected"):
            flags += 1

        if video_result.get("phone_detected", {}).get("phone_detected"):
            flags += 1

        if video_result.get("head_movement_suspicious", {}).get(
            "suspicious_movement_detected"
        ):
            flags += 1

        # Default to True (no flag) when face-detection data simply hasn't
        # arrived yet for this frame/stage, so a partially-populated
        # mid-session result doesn't get penalized for missing data.
        if not video_result.get("face_detected", {}).get("faces_found", True):
            flags += 1

        return flags

    @classmethod
    def calculate_final_risk(
        cls, video_risk: float, audio_risk: float, evaluation_risk: float
    ) -> float:
        """Calculate final combined risk score using weighted average."""
        video_weight, audio_weight, eval_weight = cls.get_pipeline_weights()
        final_risk = (
            video_weight * video_risk
            + audio_weight * audio_risk
            + eval_weight * evaluation_risk
        )
        return round(min(max(final_risk, 0.0), 1.0), 3)

        # ------------------------------------------------------------------

    # D3: Integrity score fusion
    #
    # Combines the D2-defined anti-cheat signals (tab_switching,
    # browser_activity, audio_interruptions, multiple_persons,
    # candidate_absence, gaze_deviation, background_noise) into a single
    # 0-100 integrity_score using a weighted average. Weights come from
    # D2's RiskWeights schema (orchestrator/models.py), fetched per job
    # position via orchestrator.store.get_weights_for_position(), and are
    # normalized at scoring time so they do not need to sum to 1.
    #
    # Signal collection itself (tab-switch tracking, gaze/face detection,
    # etc.) is out of scope here -- this function only fuses whatever
    # values it is given.
    # ------------------------------------------------------------------

    # D2 signal names this fusion function understands, in a fixed order.
    INTEGRITY_SIGNAL_NAMES: tuple[str, ...] = (
        "tab_switching",
        "browser_activity",
        "audio_interruptions",
        "multiple_persons",
        "candidate_absence",
        "gaze_deviation",
        "background_noise",
    )

    @classmethod
    def calculate_integrity_score(
        cls,
        signals: dict,
        job_position: str | None = None,
    ) -> float:
        """
        Fuse D2 anti-cheat signals into a single integrity_score (0-100).

        Args:
            signals: mapping of D2 signal names (see
                INTEGRITY_SIGNAL_NAMES) to a 0-100 "risk level" for that
                signal, where higher means more suspicious/riskier
                (e.g. {"tab_switching": 20.0, "gaze_deviation": 5.0}).
                A signal may be omitted or set to None if that source is
                temporarily unavailable (partial data) -- it is simply
                excluded from the average rather than causing an error.
            job_position: optional job position name. When given, D2's
                per-position weights are looked up via
                orchestrator.store.get_weights_for_position(); otherwise
                the D2 default weights (all 1.0) are used.

        Returns:
            A float in [0, 100], rounded to 2 decimals. 100 means no
            risk detected across the available signals; 0 means maximum
            combined risk. If every signal is missing/unavailable, a
            neutral 100.0 ("no risk observed") is returned rather than
            raising, since fusion should never crash on missing data.
        """
        # Local import avoids a hard/circular dependency between the
        # workers package and the orchestrator package at module load
        # time; only needed when a job_position lookup is requested.
        from orchestrator.models import RiskWeights
        from orchestrator.store import get_weights_for_position

        weights = (
            get_weights_for_position(job_position) if job_position else RiskWeights()
        )
        weight_by_signal = {
            name: getattr(weights, name) for name in cls.INTEGRITY_SIGNAL_NAMES
        }

        weighted_risk_sum = 0.0
        total_weight = 0.0

        for name in cls.INTEGRITY_SIGNAL_NAMES:
            raw_value = signals.get(name) if signals else None
            if raw_value is None:
                # Missing/partial signal: skip it gracefully instead of
                # crashing or treating it as zero risk.
                continue
            try:
                risk_value = float(raw_value)
            except (TypeError, ValueError):
                # Defensively skip malformed values the same way as
                # missing ones, rather than raising.
                continue
            risk_value = min(max(risk_value, 0.0), 100.0)

            weight = weight_by_signal[name]
            weighted_risk_sum += weight * risk_value
            total_weight += weight

        if total_weight <= 0:
            # No usable signals at all -> neutral default, never crash.
            return 100.0

        avg_risk = weighted_risk_sum / total_weight
        integrity_score = 100.0 - avg_risk
        return round(min(max(integrity_score, 0.0), 100.0), 2)

    @staticmethod
    def _apply_critical_rule_overrides(
        final_risk: float, risk_classification: str
    ) -> float:
        """Apply rule-based overrides to the linear combined risk score."""
        if risk_classification == "CRITICAL":
            return max(final_risk, 0.95)
        if risk_classification == "HIGH":
            return max(final_risk, 0.8)
        if risk_classification == "MEDIUM":
            return max(final_risk, 0.6)
        return final_risk

    @classmethod
    def classify(cls, video: dict, audio: dict, evaluation: dict) -> str:
        """Compatibility method for tests."""
        if video.get("multiple_persons", {}).get("multiple_persons_detected", False):
            return "CRITICAL"
        if not video.get("face_detected", {}).get("faces_found", True):
            return "HIGH"
        if video.get("phone_detected", {}).get("phone_detected", False):
            return "HIGH"

        bg_voice = audio.get("background_voices", {}).get(
            "background_voices_detected", False
        )
        conv = audio.get("suspicious_conversation", {}).get(
            "suspicious_pattern_detected", False
        )

        if bg_voice and conv:
            return "HIGH"
        if bg_voice:
            return "MEDIUM"

        if (
            evaluation.get("answer_quality_score", {}).get("overall_quality_score", 100)
            < 40
        ):
            return "MEDIUM"

        return "LOW"

    @classmethod
    def classify_risk(cls, risk_score: float) -> str:
        """Classify risk level based on score."""
        low, med, high = cls.get_thresholds()
        if risk_score < low:
            return "LOW"
        if risk_score < med:
            return "MEDIUM"
        if risk_score < high:
            return "HIGH"
        return "CRITICAL"

    @staticmethod
    def generate_risk_report(
        session_id: str,
        video_result: dict[str, Any],
        audio_result: dict[str, Any],
        evaluation_result: dict[str, Any],
    ) -> dict[str, Any]:
        """Generate comprehensive risk report from all analysis results."""
        logger.info(f"Generating risk report for session {session_id}")

        video_risk = RiskScoringEngine.calculate_video_risk(video_result)
        audio_risk = RiskScoringEngine.calculate_audio_risk(audio_result)
        evaluation_risk = RiskScoringEngine.calculate_evaluation_risk(evaluation_result)
        final_risk = RiskScoringEngine.calculate_final_risk(
            video_risk, audio_risk, evaluation_risk
        )
        risk_classification = RiskScoringEngine.classify_risk(final_risk)

        override = RiskOverrideEngine.evaluate(
            video_result,
            audio_result,
            evaluation_result,
        )

        if override is not None:
            logger.info(
                "Risk classification overridden from %s to %s",
                risk_classification,
                override,
            )
            risk_classification = override

        risk_factors = RiskScoringEngine._identify_risk_factors(
            video_result, audio_result, evaluation_result
        )

        report = {
            "session_id": session_id,
            "final_risk_score": final_risk,
            "risk_classification": risk_classification,
            "component_risks": {
                "video_risk": video_risk,
                "audio_risk": audio_risk,
                "evaluation_risk": evaluation_risk,
            },
            "risk_factors": risk_factors,
            "explanation": RiskScoringEngine._generate_explanation(
                risk_classification,
                risk_factors,
            ),
            "recommendation": RiskScoringEngine._generate_recommendation(
                risk_classification,
            ),
        }

        logger.info(
            f"Risk report generated: {risk_classification} (score: {final_risk})"
        )
        return report

    @staticmethod
    def _identify_risk_factors(
        video_result: dict[str, Any],
        audio_result: dict[str, Any],
        evaluation_result: dict[str, Any],
    ) -> list:
        """Identify specific risk factors from analysis results."""
        risk_factors = []

        if not video_result.get("face_detected", {}).get("faces_found"):
            risk_factors.append("Candidate face not detected")
        if video_result.get("multiple_persons", {}).get("multiple_persons_detected"):
            risk_factors.append("Multiple persons detected in frame")
        if video_result.get("phone_detected", {}).get("phone_detected"):
            risk_factors.append("Mobile phone detected")
        if video_result.get("head_movement_suspicious", {}).get(
            "suspicious_movement_detected"
        ):
            risk_factors.append("Suspicious head movement detected")

        if audio_result.get("background_voices", {}).get("background_voices_detected"):
            risk_factors.append("Background voices detected - possible external help")
        if audio_result.get("suspicious_conversation", {}).get(
            "suspicious_pattern_detected"
        ):
            risk_factors.append("Suspicious conversation pattern detected")
        if not audio_result.get("transcription", {}).get("text"):
            risk_factors.append("No speech detected during interview")

        quality_score = evaluation_result.get("answer_quality_score", {}).get(
            "overall_quality_score", 50
        )
        accuracy_score = evaluation_result.get("technical_accuracy", {}).get(
            "accuracy_score", 50
        )

        if quality_score < 40:
            risk_factors.append("Low answer quality detected")
        if accuracy_score < 40:
            risk_factors.append("Low technical accuracy detected")
        if evaluation_result.get("hallucination_check", {}).get("is_hallucination"):
            risk_factors.append("Fabricated or unsupported claims detected in response")

        return risk_factors

    @staticmethod
    def _generate_explanation(risk_classification: str, risk_factors: list) -> str:
        """Generate a human-readable explanation of the risk assessment."""
        if not risk_factors:
            return "No significant risk factors detected."
        factor_text = "; ".join(risk_factors)
        return f"Risk classification: {risk_classification}. Factors: {factor_text}"

    @staticmethod
    def _generate_recommendation(risk_classification: str) -> str:
        """Generate recommendation based on risk classification."""
        recommendations = {
            "LOW": "Candidate appears genuine. Proceed with hiring consideration.",
            "MEDIUM": "Monitor candidate responses. Further verification may be needed.",
            "HIGH": "Multiple concerning factors detected. Recommend interview review.",
            "CRITICAL": "Significant fraud indicators detected. Recommend rejection or investigation.",
        }
        return recommendations.get(risk_classification, "Review interview manually.")
