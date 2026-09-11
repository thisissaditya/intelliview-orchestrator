from orchestrator.question_bank import (
    get_personalized_questions,
    set_retrieval_provider,
)


class MockRetrievalProvider:
    def __init__(self, results=None, error=None):
        self.results = results or []
        self.error = error

    def retrieve(
        self,
        candidate_id,
        resume_text,
        jd_text,
        count=5,
    ):
        if self.error:
            raise self.error

        return self.results[:count]


def test_rag_pipeline_retrieves_personalized_questions():
    provider = MockRetrievalProvider(
        results=[
            "Explain your Python experience.",
            "How have you used SQL in projects?",
            "Describe your experience with machine learning.",
        ]
    )

    set_retrieval_provider(provider)

    result = get_personalized_questions(
        candidate_id="candidate-1",
        resume_text="Python developer with SQL experience",
        jd_text="Looking for Python and SQL skills",
        count=2,
    )

    assert len(result) == 2
    assert "Python" in result[0]
    assert "SQL" in result[1]

    set_retrieval_provider(None)


def test_rag_pipeline_falls_back_when_retrieval_fails(monkeypatch):
    provider = MockRetrievalProvider(error=RuntimeError("retrieval unavailable"))

    set_retrieval_provider(provider)

    legacy_questions = [
        {"question_id": "q1", "text": "Tell me about yourself."},
        {"question_id": "q2", "text": "Explain your project."},
    ]

    monkeypatch.setattr(
        "orchestrator.question_bank.question_bank.get_questions",
        lambda limit=5: legacy_questions[:limit],
    )

    result = get_personalized_questions(
        candidate_id="candidate-1",
        resume_text="Python developer",
        jd_text="Python developer required",
        count=2,
    )

    assert result == legacy_questions

    set_retrieval_provider(None)


def test_rag_pipeline_respects_count():
    provider = MockRetrievalProvider(
        results=[
            "Question 1",
            "Question 2",
            "Question 3",
            "Question 4",
            "Question 5",
        ]
    )

    set_retrieval_provider(provider)

    result = get_personalized_questions(
        candidate_id="candidate-1",
        resume_text="Python SQL",
        jd_text="Backend developer",
        count=3,
    )

    assert len(result) == 3

    set_retrieval_provider(None)
