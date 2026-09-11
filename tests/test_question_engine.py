"""Tests for retrieval/question_engine.py."""

from __future__ import annotations

import logging

import pytest

from retrieval.question_engine import (
    DEFAULT_FALLBACK_QUESTIONS,
    EngineResult,
    QuestionEngine,
    RetrievedQuestion,
)


class FakeRetriever:
    """Deterministic stand-in for a real retriever (e.g. retrieval/index.py),
    injected so tests never touch FAISS / SentenceTransformer.
    """

    def __init__(self, results):
        self._results = results
        self.calls: list[tuple[str, int]] = []

    def retrieve(self, query, top_k=3):
        self.calls.append((query, top_k))
        return self._results


class ExplodingRetriever:
    def retrieve(self, query, top_k=3):
        raise RuntimeError("backend unavailable")


PYTHON_CANDIDATES = [
    {
        "question_id": "q-1",
        "text": "Explain how Python's garbage collector handles reference cycles.",
        "category": "python",
        "difficulty": "medium",
        "score": 0.9,
    },
    {
        "question_id": "q-2",
        "text": "What is the difference between a list and a tuple in Python?",
        "category": "python",
        "difficulty": "easy",
        "score": 0.8,
    },
    {
        "question_id": "q-3",
        "text": "How would you design a rate limiter for a distributed Python service?",
        "category": "system-design",
        "difficulty": "hard",
        "score": 0.7,
    },
    {
        "question_id": "q-4",
        "text": "Describe Python decorators and give a practical use case.",
        "category": "python",
        "difficulty": "medium",
        "score": 0.6,
    },
]


# ---------------------------------------------------------------------------
# Relevant retrieval
# ---------------------------------------------------------------------------
def test_relevant_retrieval_returns_candidates():
    retriever = FakeRetriever(PYTHON_CANDIDATES)
    engine = QuestionEngine(retriever, confidence_threshold=0.1)

    result = engine.get_questions(
        "python interview questions", skills=["python"], top_k=3
    )

    assert isinstance(result, EngineResult)
    assert result.used_fallback is False
    assert len(result.questions) == 3
    assert all(isinstance(q, RetrievedQuestion) for q in result.questions)
    # The retriever was actually invoked with the query.
    assert retriever.calls[0][0] == "python interview questions"


# ---------------------------------------------------------------------------
# Deterministic ranking
# ---------------------------------------------------------------------------
def test_ranking_is_deterministic_across_runs():
    retriever = FakeRetriever(PYTHON_CANDIDATES)
    engine = QuestionEngine(retriever, confidence_threshold=0.1)

    result_a = engine.get_questions("python", skills=["python"], top_k=4)
    result_b = engine.get_questions("python", skills=["python"], top_k=4)

    ids_a = [q.question_id for q in result_a.questions]
    ids_b = [q.question_id for q in result_b.questions]
    assert ids_a == ids_b

    # Higher combined score (retrieval score + skill relevance) sorts first.
    scores = [q.score for q in result_a.questions]
    assert scores == sorted(scores, reverse=True)


def test_ranking_breaks_ties_by_question_id():
    tied_candidates = [
        {
            "question_id": "z-tied",
            "text": "Question Z",
            "category": "general",
            "difficulty": "easy",
            "score": 0.5,
        },
        {
            "question_id": "a-tied",
            "text": "Question A",
            "category": "general",
            "difficulty": "easy",
            "score": 0.5,
        },
    ]
    retriever = FakeRetriever(tied_candidates)
    engine = QuestionEngine(retriever, confidence_threshold=0.0)

    result = engine.get_questions("general", top_k=2)

    # Equal scores -> deterministic tiebreak by question_id ascending.
    assert [q.question_id for q in result.questions] == ["a-tied", "z-tied"]


# ---------------------------------------------------------------------------
# Top-k
# ---------------------------------------------------------------------------
def test_top_k_limits_result_size():
    retriever = FakeRetriever(PYTHON_CANDIDATES)
    engine = QuestionEngine(retriever, confidence_threshold=0.1)

    result = engine.get_questions("python", skills=["python"], top_k=2)

    assert len(result.questions) == 2


def test_top_k_invalid_raises():
    retriever = FakeRetriever(PYTHON_CANDIDATES)
    engine = QuestionEngine(retriever)

    with pytest.raises(ValueError):
        engine.get_questions("python", top_k=0)


# ---------------------------------------------------------------------------
# Difficulty balancing
# ---------------------------------------------------------------------------
def test_difficulty_balancing_spreads_across_levels():
    retriever = FakeRetriever(PYTHON_CANDIDATES)
    engine = QuestionEngine(retriever, confidence_threshold=0.1)

    result = engine.get_questions(
        "python",
        skills=["python"],
        top_k=3,
        difficulty_balance=["easy", "medium", "hard"],
    )

    difficulties = sorted(q.difficulty.lower() for q in result.questions)
    assert difficulties == ["easy", "hard", "medium"]


def test_difficulty_balancing_fills_remaining_slots_when_unbalanced():
    # Only "easy" and "medium" difficulties available; balance requests
    # "easy", "medium", "hard" -- "hard" bucket is empty so the engine
    # should still deterministically fill top_k from what's available.
    candidates = [
        {
            "question_id": "e1",
            "text": "Easy one",
            "category": "general",
            "difficulty": "easy",
            "score": 0.9,
        },
        {
            "question_id": "e2",
            "text": "Easy two",
            "category": "general",
            "difficulty": "easy",
            "score": 0.8,
        },
        {
            "question_id": "m1",
            "text": "Medium one",
            "category": "general",
            "difficulty": "medium",
            "score": 0.7,
        },
    ]
    retriever = FakeRetriever(candidates)
    engine = QuestionEngine(retriever, confidence_threshold=0.1)

    result = engine.get_questions(
        "general", top_k=3, difficulty_balance=["easy", "medium", "hard"]
    )

    assert len(result.questions) == 3
    assert {q.question_id for q in result.questions} == {"e1", "e2", "m1"}


# ---------------------------------------------------------------------------
# Confidence threshold
# ---------------------------------------------------------------------------
def test_confidence_threshold_filters_low_scoring_candidates():
    candidates = [
        {
            "question_id": "low-1",
            "text": "Low confidence question",
            "category": "general",
            "difficulty": "easy",
            "score": 0.05,
        },
    ]
    retriever = FakeRetriever(candidates)
    engine = QuestionEngine(retriever, confidence_threshold=0.5)

    result = engine.get_questions("general", top_k=3)

    # Below threshold -> no usable candidates -> fallback engages.
    assert result.used_fallback is True


def test_confidence_threshold_can_be_overridden_per_call():
    candidates = [
        {
            "question_id": "mid-1",
            "text": "Medium confidence question",
            "category": "general",
            "difficulty": "easy",
            "score": 0.3,
        },
    ]
    retriever = FakeRetriever(candidates)
    engine = QuestionEngine(retriever, confidence_threshold=0.5)

    # Default threshold (0.5) would reject this candidate...
    default_result = engine.get_questions("general", top_k=1)
    assert default_result.used_fallback is True

    # ...but a lower per-call threshold should let it through.
    override_result = engine.get_questions("general", top_k=1, confidence_threshold=0.1)
    assert override_result.used_fallback is False
    assert override_result.questions[0].question_id == "mid-1"


# ---------------------------------------------------------------------------
# Fallback: empty retrieval
# ---------------------------------------------------------------------------
def test_fallback_triggered_when_retrieval_is_empty():
    retriever = FakeRetriever([])
    engine = QuestionEngine(retriever)

    result = engine.get_questions("anything", top_k=3)

    assert result.used_fallback is True
    assert len(result.questions) == 3
    fallback_ids = {q.question_id for q in DEFAULT_FALLBACK_QUESTIONS}
    assert all(q.question_id in fallback_ids for q in result.questions)


def test_fallback_triggered_when_retriever_raises():
    engine = QuestionEngine(ExplodingRetriever())

    result = engine.get_questions("anything", top_k=2)

    assert result.used_fallback is True
    assert len(result.questions) == 2


# ---------------------------------------------------------------------------
# Fallback: confidence too low
# ---------------------------------------------------------------------------
def test_fallback_triggered_when_confidence_too_low():
    candidates = [
        {
            "question_id": "weak-1",
            "text": "Weak candidate",
            "category": "general",
            "difficulty": "easy",
            "score": 0.01,
        },
        {
            "question_id": "weak-2",
            "text": "Another weak candidate",
            "category": "general",
            "difficulty": "medium",
            "score": 0.02,
        },
    ]
    retriever = FakeRetriever(candidates)
    engine = QuestionEngine(retriever, confidence_threshold=0.9)

    result = engine.get_questions("general", top_k=2)

    assert result.used_fallback is True
    assert result.warning is not None
    assert "below_confidence_threshold" in result.warning


# ---------------------------------------------------------------------------
# Deterministic fallback ordering
# ---------------------------------------------------------------------------
def test_fallback_ordering_is_deterministic():
    engine = QuestionEngine(FakeRetriever([]))

    result_a = engine.get_questions("x", top_k=5)
    result_b = engine.get_questions("y", top_k=5)

    ids_a = [q.question_id for q in result_a.questions]
    ids_b = [q.question_id for q in result_b.questions]
    assert ids_a == ids_b
    assert ids_a == [q.question_id for q in DEFAULT_FALLBACK_QUESTIONS[:5]]


def test_custom_fallback_bank_is_respected_and_deterministic():
    custom_fallback = (
        RetrievedQuestion("custom-1", "Custom Q1", "general", "easy", 0.0),
        RetrievedQuestion("custom-2", "Custom Q2", "general", "medium", 0.0),
    )
    engine = QuestionEngine(FakeRetriever([]), fallback_questions=custom_fallback)

    result = engine.get_questions("anything", top_k=2)

    assert [q.question_id for q in result.questions] == ["custom-1", "custom-2"]


# ---------------------------------------------------------------------------
# Duplicate removal
# ---------------------------------------------------------------------------
def test_duplicate_question_ids_are_removed():
    candidates = [
        {
            "question_id": "dup-1",
            "text": "What is a hash map?",
            "category": "general",
            "difficulty": "easy",
            "score": 0.9,
        },
        {
            "question_id": "dup-1",
            "text": "What is a hash map?",
            "category": "general",
            "difficulty": "easy",
            "score": 0.9,
        },
    ]
    retriever = FakeRetriever(candidates)
    engine = QuestionEngine(retriever, confidence_threshold=0.1)

    result = engine.get_questions("general", top_k=5)

    assert len(result.questions) == 1


def test_near_duplicate_text_is_removed():
    candidates = [
        {
            "question_id": "nd-1",
            "text": "What is a Hash Map?",
            "category": "general",
            "difficulty": "easy",
            "score": 0.9,
        },
        {
            "question_id": "nd-2",
            "text": "what is a hash map",
            "category": "general",
            "difficulty": "easy",
            "score": 0.85,
        },
        {
            "question_id": "nd-3",
            "text": "Explain binary search trees.",
            "category": "general",
            "difficulty": "medium",
            "score": 0.7,
        },
    ]
    retriever = FakeRetriever(candidates)
    engine = QuestionEngine(retriever, confidence_threshold=0.1)

    result = engine.get_questions("general", top_k=5)

    ids = {q.question_id for q in result.questions}
    assert len(result.questions) == 2
    assert "nd-3" in ids
    # Only the higher-scored duplicate ("nd-1") should survive.
    assert "nd-1" in ids
    assert "nd-2" not in ids


# ---------------------------------------------------------------------------
# Final result structure
# ---------------------------------------------------------------------------
def test_final_result_has_no_duplicate_ids_and_valid_fields():
    retriever = FakeRetriever(PYTHON_CANDIDATES)
    engine = QuestionEngine(retriever, confidence_threshold=0.1)

    result = engine.get_questions("python", skills=["python"], top_k=4)

    ids = [q.question_id for q in result.questions]
    assert len(ids) == len(set(ids))
    for question in result.questions:
        assert isinstance(question.question_id, str) and question.question_id
        assert isinstance(question.text, str) and question.text
        assert isinstance(question.category, str) and question.category
        assert isinstance(question.difficulty, str) and question.difficulty
        assert isinstance(question.score, float)


def test_engine_result_reports_fallback_flag_correctly():
    ok_retriever = FakeRetriever(PYTHON_CANDIDATES)
    ok_engine = QuestionEngine(ok_retriever, confidence_threshold=0.1)
    ok_result = ok_engine.get_questions("python", skills=["python"], top_k=1)
    assert ok_result.used_fallback is False
    assert ok_result.warning is None

    empty_engine = QuestionEngine(FakeRetriever([]))
    empty_result = empty_engine.get_questions("python", top_k=1)
    assert empty_result.used_fallback is True
    assert empty_result.warning is not None


# ---------------------------------------------------------------------------
# Structured fallback warning / logging
# ---------------------------------------------------------------------------
def test_fallback_emits_structured_warning_log(caplog):
    engine = QuestionEngine(FakeRetriever([]))

    with caplog.at_level(logging.WARNING, logger="retrieval.question_engine"):
        result = engine.get_questions("no results here", top_k=2)

    assert result.used_fallback is True
    assert any("fallback_triggered" in record.message for record in caplog.records)
    assert any("empty_retrieval" in record.message for record in caplog.records)
    assert result.warning is not None and "fallback_triggered" in result.warning


def test_non_fallback_path_does_not_emit_fallback_warning(caplog):
    retriever = FakeRetriever(PYTHON_CANDIDATES)
    engine = QuestionEngine(retriever, confidence_threshold=0.1)

    with caplog.at_level(logging.WARNING, logger="retrieval.question_engine"):
        result = engine.get_questions("python", skills=["python"], top_k=2)

    assert result.used_fallback is False
    assert not any("fallback_triggered" in record.message for record in caplog.records)
