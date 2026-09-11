"""
Scoring Models

Provides a pluggable interface for risk scoring models.

Model A:
    Existing weighted RiskScoringEngine.

Model B:
    Experimental weighted model used for A/B testing.

Future models only need to inherit BaseRiskScoringModel.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from workers.risk_engine import RiskScoringEngine


class BaseRiskScoringModel(ABC):
    """
    Abstract interface for every risk scoring model.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Unique model name."""

    @abstractmethod
    def generate_report(
        self,
        session_id: str,
        video_result: dict[str, Any],
        audio_result: dict[str, Any],
        evaluation_result: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Generate a complete risk report.
        """


class WeightedRiskModel(BaseRiskScoringModel):
    """
    Production model.

    Uses the existing RiskScoringEngine without modification.
    """

    @property
    def name(self) -> str:
        return "weighted_model"

    def generate_report(
        self,
        session_id: str,
        video_result: dict[str, Any],
        audio_result: dict[str, Any],
        evaluation_result: dict[str, Any],
    ) -> dict[str, Any]:

        report = RiskScoringEngine.generate_risk_report(
            session_id=session_id,
            video_result=video_result,
            audio_result=audio_result,
            evaluation_result=evaluation_result,
        )

        report["model"] = self.name

        return report


class ExperimentalRiskModel(BaseRiskScoringModel):
    """
    Experimental scoring model.

    Uses different pipeline weights so researchers can compare
    against the production implementation.
    """

    VIDEO_WEIGHT = 0.30
    AUDIO_WEIGHT = 0.20
    EVALUATION_WEIGHT = 0.50

    @property
    def name(self) -> str:
        return "experimental_model"

    def generate_report(
        self,
        session_id: str,
        video_result: dict[str, Any],
        audio_result: dict[str, Any],
        evaluation_result: dict[str, Any],
    ) -> dict[str, Any]:

        video_risk = RiskScoringEngine.calculate_video_risk(video_result)

        audio_risk = RiskScoringEngine.calculate_audio_risk(audio_result)

        evaluation_risk = RiskScoringEngine.calculate_evaluation_risk(evaluation_result)

        final_risk = (
            self.VIDEO_WEIGHT * video_risk
            + self.AUDIO_WEIGHT * audio_risk
            + self.EVALUATION_WEIGHT * evaluation_risk
        )

        final_risk = round(min(max(final_risk, 0.0), 1.0), 3)

        classification = RiskScoringEngine.classify_risk(final_risk)

        report = {
            "session_id": session_id,
            "model": self.name,
            "final_risk_score": final_risk,
            "risk_classification": classification,
            "component_risks": {
                "video_risk": video_risk,
                "audio_risk": audio_risk,
                "evaluation_risk": evaluation_risk,
            },
            "risk_factors": RiskScoringEngine._identify_risk_factors(
                video_result,
                audio_result,
                evaluation_result,
            ),
            "recommendation": RiskScoringEngine._generate_recommendation(
                classification
            ),
        }

        return report


# ---------------------------------------------------------------------------
# Analytics helpers
# ---------------------------------------------------------------------------


class EvaluationAnalytics:
    """
    Helpers for deriving analytics information from existing evaluation data.

    These methods do not modify or recalculate the existing risk score.
    """

    PASS_RISK_THRESHOLD = 0.6

    @classmethod
    def is_pass(cls, risk_score: float | int | None) -> bool:
        """Return True when an existing risk score represents a passing result."""
        if risk_score is None:
            return False

        try:
            return float(risk_score) < cls.PASS_RISK_THRESHOLD
        except (TypeError, ValueError):
            return False

    @classmethod
    def is_fail(cls, risk_score: float | int | None) -> bool:
        """Return True when an existing risk score represents a failing result."""
        if risk_score is None:
            return False

        try:
            return float(risk_score) >= cls.PASS_RISK_THRESHOLD
        except (TypeError, ValueError):
            return False

    @classmethod
    def extract_weak_areas(
        cls,
        evaluation_result: dict[str, Any] | None,
    ) -> list[str]:
        """
        Extract weak areas from already-generated evaluation results.

        Sources:
        - technical_accuracy.knowledge_gaps
        - feedback.improvements
        """
        if not evaluation_result:
            return []

        weak_areas: list[str] = []

        technical_accuracy = evaluation_result.get(
            "technical_accuracy",
            {},
        )

        if isinstance(technical_accuracy, dict):
            knowledge_gaps = technical_accuracy.get(
                "knowledge_gaps",
                [],
            )

            if isinstance(knowledge_gaps, list):
                weak_areas.extend(
                    str(item).strip() for item in knowledge_gaps if str(item).strip()
                )

        feedback = evaluation_result.get(
            "feedback",
            {},
        )

        if isinstance(feedback, dict):
            improvements = feedback.get(
                "improvements",
                [],
            )

            if isinstance(improvements, list):
                weak_areas.extend(
                    str(item).strip() for item in improvements if str(item).strip()
                )

        return weak_areas

    @classmethod
    def calculate_pass_rate(
        cls,
        sessions: list[dict[str, Any]] | None,
    ) -> float:
        """
        Calculate pass rate from existing session risk scores.

        A session passes when its existing risk score is below
        PASS_RISK_THRESHOLD.

        Returns:
            Pass rate as a percentage from 0 to 100.
        """
        if not sessions:
            return 0.0

        valid_scores = [
            session.get("risk_score")
            for session in sessions
            if session.get("risk_score") is not None
        ]

        if not valid_scores:
            return 0.0

        passed = sum(1 for score in valid_scores if cls.is_pass(score))

        return round(
            (passed / len(valid_scores)) * 100,
            2,
        )

    @classmethod
    def aggregate_weak_areas(
        cls,
        sessions: list[dict[str, Any]] | None,
    ) -> list[dict[str, Any]]:
        """
        Aggregate weak areas from existing evaluation results.

        Returns:
            [
                {"topic": "systems design depth", "count": 3},
                {"topic": "communication", "count": 2},
            ]
        """
        if not sessions:
            return []

        counts: dict[str, int] = {}

        for session in sessions:
            evaluation_result = session.get(
                "evaluation_analysis",
                session.get("evaluation_result"),
            )

            weak_areas = cls.extract_weak_areas(evaluation_result)

            for area in weak_areas:
                topic = area.strip()

                if not topic:
                    continue

                counts[topic] = counts.get(topic, 0) + 1

        return [
            {
                "topic": topic,
                "count": count,
            }
            for topic, count in sorted(
                counts.items(),
                key=lambda item: (-item[1], item[0].lower()),
            )
        ]
