# from curses import raw
import hashlib
import logging
import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any, Protocol

logger = logging.getLogger(__name__)


class QuestionRetriever(Protocol):
    def retrieve(self, query: str, top_k: int = 3) -> list[Any]:
        """Retrieve candidate question templates."""


@dataclass(frozen=True)
class RetrievedQuestion:
    question_id: str
    text: str
    category: str
    difficulty: str
    score: float
    tags: tuple[str, ...] = ()


# ---------------------------------------------------------------------------
# Static, deterministic fallback bank.
#
# Intentionally small, hand-curated, and independent of any external
# service, so the engine always has *something* deterministic to fall back
# on when semantic retrieval is empty or not confident enough. Ordering is
# fixed (insertion order) so fallback results are reproducible.
# ---------------------------------------------------------------------------
DEFAULT_FALLBACK_QUESTIONS: tuple[RetrievedQuestion, ...] = (
    RetrievedQuestion(
        question_id="fallback-001",
        text="Tell me about a challenging project you worked on and how you approached it.",
        category="general",
        difficulty="easy",
        score=0.0,
    ),
    RetrievedQuestion(
        question_id="fallback-002",
        text="Describe a time you had to debug a difficult issue in production.",
        category="general",
        difficulty="medium",
        score=0.0,
    ),
    RetrievedQuestion(
        question_id="fallback-003",
        text="How would you design a scalable system for a high-traffic application?",
        category="system-design",
        difficulty="hard",
        score=0.0,
    ),
    RetrievedQuestion(
        question_id="fallback-004",
        text="What data structure would you use to implement a cache with eviction?",
        category="data-structures",
        difficulty="medium",
        score=0.0,
    ),
    RetrievedQuestion(
        question_id="fallback-005",
        text="Explain the difference between concurrency and parallelism.",
        category="general",
        difficulty="easy",
        score=0.0,
    ),
)


@dataclass
class EngineResult:
    """Structured, final output of the question engine."""

    questions: list[RetrievedQuestion]
    used_fallback: bool
    warning: str | None = None


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------
def _normalize_text(text: str) -> str:
    """Normalize text for near-duplicate detection (case/punctuation-insensitive)."""
    text = text.strip().lower()
    text = re.sub(r"[^\w\s]", "", text)
    text = re.sub(r"\s+", " ", text)
    return text


def _stable_id(text: str) -> str:
    """Deterministically derive a question id from text when none is supplied."""
    digest = hashlib.sha1(text.encode("utf-8")).hexdigest()[:12]
    return f"gen-{digest}"


def _coerce_candidate(raw: Any) -> RetrievedQuestion | None:
    """Normalize a raw retriever result into a RetrievedQuestion.

    The injected retriever is not guaranteed to already speak
    ``RetrievedQuestion`` -- it may hand back dicts, tuples, or plain
    strings (e.g. from a vector-search layer such as ``retrieval/index.py``).
    This adapter accepts the common shapes without inventing data it can't
    infer, returning ``None`` for anything it cannot interpret as a
    question candidate.
    """
    if raw is None:
        return None

    if isinstance(raw, RetrievedQuestion):
        return raw

    if isinstance(raw, Mapping):
        text = raw.get("text") or raw.get("question") or raw.get("content")
        if not text:
            return None
        category = str(raw.get("category", "general"))
        question_id = str(raw.get("question_id") or raw.get("id") or _stable_id(text))
        difficulty = str(raw.get("difficulty", "medium"))
        raw_tags = raw.get("tags", [])
        tags = tuple(str(tag) for tag in raw_tags) if raw_tags else ()
        raw_score = raw.get("score", raw.get("similarity", 0.0))
        score = float(raw_score) if raw_score is not None else 0.0
        return RetrievedQuestion(
            question_id, str(text), category, difficulty, score, tags
        )

    if isinstance(raw, tuple | list):
        if not raw:
            return None
        text = str(raw[0])
        score = float(raw[1]) if len(raw) > 1 and raw[1] is not None else 0.0
        category = str(raw[2]) if len(raw) > 2 else "general"
        difficulty = str(raw[3]) if len(raw) > 3 else "medium"
        return RetrievedQuestion(_stable_id(text), text, category, difficulty, score)

    if isinstance(raw, str):
        return RetrievedQuestion(_stable_id(raw), raw, "general", "medium", 0.0)

    return None


def _skill_relevance(candidate: RetrievedQuestion, skills: Sequence[str]) -> float:
    """Small, deterministic keyword-overlap boost based on requested skills."""
    if not skills:
        return 0.0
    haystack = f"{candidate.text} {candidate.category}".lower()
    hits = sum(1 for skill in skills if skill and skill.lower() in haystack)
    return hits / len(skills)


def _difficulty_bonus(
    candidate: RetrievedQuestion, target_difficulty: str | None
) -> float:
    if not target_difficulty:
        return 0.0
    return 0.1 if candidate.difficulty.lower() == target_difficulty.lower() else 0.0


# ---------------------------------------------------------------------------
# Engine
# ---------------------------------------------------------------------------
class QuestionEngine:
    """Deterministic retrieval, ranking, and fallback engine for question
    templates.

    The retriever (and optionally a fallback bank / logger) are injected so
    the engine has no hard-coded dependency on any specific embedding or
    search backend -- in production this would typically be
    ``retrieval.index.retrieve``, wrapped to satisfy ``QuestionRetriever``.
    """

    def __init__(
        self,
        retriever: QuestionRetriever,
        fallback_questions: Sequence[RetrievedQuestion] | None = None,
        confidence_threshold: float = 0.2,
        logger_: logging.Logger | None = None,
    ) -> None:
        self._retriever = retriever
        self._fallback_questions = tuple(
            fallback_questions or DEFAULT_FALLBACK_QUESTIONS
        )
        self._confidence_threshold = confidence_threshold
        self._logger = logger_ or logger

    # -- public API ---------------------------------------------------
    def get_questions(
        self,
        query: str,
        skills: Sequence[str] | None = None,
        top_k: int = 5,
        difficulty_balance: Sequence[str] | None = None,
        target_difficulty: str | None = None,
        confidence_threshold: float | None = None,
        retrieval_pool: int | None = None,
    ) -> EngineResult:
        """Retrieve, score, re-rank, deduplicate, and (if needed) fall back
        to a static bank, producing a final question set of size <= top_k
        with no duplicate ids.
        """
        if top_k <= 0:
            raise ValueError("top_k must be a positive integer")

        threshold = (
            self._confidence_threshold
            if confidence_threshold is None
            else confidence_threshold
        )
        skills = list(skills or [])
        pool_size = retrieval_pool or max(top_k * 4, 10)

        raw_candidates = self._safe_retrieve(query, pool_size)
        candidates = self._score_and_filter(
            raw_candidates, skills, target_difficulty, threshold
        )

        if not candidates:
            reason = (
                "empty_retrieval"
                if not raw_candidates
                else "below_confidence_threshold"
            )
            warning = self._emit_fallback_warning(query, reason)
            selected = self._select(
                list(self._fallback_questions), top_k, difficulty_balance
            )
            return EngineResult(questions=selected, used_fallback=True, warning=warning)

        selected = self._select(candidates, top_k, difficulty_balance)
        return EngineResult(questions=selected, used_fallback=False, warning=None)

    # -- internals ------------------------------------------------------
    def _safe_retrieve(self, query: str, pool_size: int) -> list[Any]:
        try:
            results = self._retriever.retrieve(query, top_k=pool_size)
        except Exception as exc:  # defensive: retriever is an external dependency
            self._logger.warning(
                "question_engine.retrieval_failed query=%r error=%s", query, exc
            )
            return []
        return list(results) if results else []

    def _score_and_filter(
        self,
        raw_candidates: list[Any],
        skills: Sequence[str],
        target_difficulty: str | None,
        threshold: float,
    ) -> list[RetrievedQuestion]:
        scored: list[RetrievedQuestion] = []
        for raw in raw_candidates:
            candidate = _coerce_candidate(raw)
            if candidate is None:
                continue
            relevance = _skill_relevance(candidate, skills)
            bonus = _difficulty_bonus(candidate, target_difficulty)
            combined_score = candidate.score + relevance + bonus
            if combined_score < threshold:
                continue
            scored.append(
                RetrievedQuestion(
                    candidate.question_id,
                    candidate.text,
                    candidate.category,
                    candidate.difficulty,
                    combined_score,
                )
            )
        # Deterministic ranking: highest score first, question_id as a
        # stable tiebreaker so equal-score candidates always sort the same.
        scored.sort(key=lambda q: (-q.score, q.question_id))
        return scored

    def _select(
        self,
        candidates: list[RetrievedQuestion],
        top_k: int,
        difficulty_balance: Sequence[str] | None,
    ) -> list[RetrievedQuestion]:
        deduped = self._dedupe(candidates)
        if not difficulty_balance:
            return deduped[:top_k]
        return self._balance_by_difficulty(deduped, top_k, difficulty_balance)

    @staticmethod
    def _dedupe(candidates: list[RetrievedQuestion]) -> list[RetrievedQuestion]:
        """Remove duplicate ids and closely overlapping (near-duplicate) text,
        preserving the incoming (already ranked) order.
        """
        seen_ids: set[str] = set()
        seen_text: set[str] = set()
        result: list[RetrievedQuestion] = []
        for candidate in candidates:
            if candidate.question_id in seen_ids:
                continue
            normalized = _normalize_text(candidate.text)
            if normalized in seen_text:
                continue
            seen_ids.add(candidate.question_id)
            seen_text.add(normalized)
            result.append(candidate)
        return result

    @staticmethod
    def _balance_by_difficulty(
        candidates: list[RetrievedQuestion],
        top_k: int,
        difficulty_balance: Sequence[str],
    ) -> list[RetrievedQuestion]:
        """Round-robin selection across the requested difficulty order so the
        final set is as balanced as available candidates allow, falling back
        to remaining candidates (regardless of difficulty) to fill any
        leftover slots deterministically.
        """
        buckets: dict[str, list[RetrievedQuestion]] = {}
        for candidate in candidates:
            buckets.setdefault(candidate.difficulty.lower(), []).append(candidate)

        order = [d.lower() for d in difficulty_balance]
        selected: list[RetrievedQuestion] = []
        selected_ids: set[str] = set()

        progressed = True
        while len(selected) < top_k and progressed:
            progressed = False
            for difficulty in order:
                if len(selected) >= top_k:
                    break
                for item in buckets.get(difficulty, []):
                    if item.question_id not in selected_ids:
                        selected.append(item)
                        selected_ids.add(item.question_id)
                        progressed = True
                        break

        if len(selected) < top_k:
            for candidate in candidates:
                if len(selected) >= top_k:
                    break
                if candidate.question_id not in selected_ids:
                    selected.append(candidate)
                    selected_ids.add(candidate.question_id)

        return selected

    def _emit_fallback_warning(self, query: str, reason: str) -> str:
        message = f"question_engine.fallback_triggered reason={reason} query={query!r}"
        self._logger.warning(message)
        return message
