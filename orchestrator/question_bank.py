"""
Question Bank Module
Manages interview questions by category, difficulty, and usage statistics
"""

import logging
import uuid
from typing import Any

from sqlalchemy import select

from database.db import SessionLocal
from database.models import Question
from orchestrator.time_utils import utcnow

logger = logging.getLogger(__name__)

ADAPTIVE_FOLLOWUP_PROMPT = """
You are an expert interviewer conducting a cross-domain interview.

Review the original interview question and the candidate's answer.

Original question:
{original_question}

Candidate answer:
{candidate_answer}

Determine whether the candidate's answer is thin, vague, incomplete, or lacks
enough detail to adequately address the original question.

If the answer is thin or vague, generate ONE deeper follow-up question.

The follow-up must:
- Stay strictly on the topic of the original question.
- Build naturally on the candidate's answer.
- Ask for clarification, reasoning, an example, implementation details,
  trade-offs, or another relevant deeper aspect.
- Not introduce an unrelated topic.
- Not repeat the original question.
- Not score or judge the candidate.
- Not provide the answer to the candidate.

Return only a JSON object with exactly these keys:
{{
    "original_question": "string",
    "candidate_answer": "string",
    "followup_prompt": "string"
}}

If the candidate's answer is already sufficiently detailed, set
"followup_prompt" to an empty string.
""".strip()


def build_adaptive_followup_prompt(
    original_question: str,
    candidate_answer: str,
) -> str:
    """Build a prompt for generating an on-topic adaptive follow-up."""
    return ADAPTIVE_FOLLOWUP_PROMPT.format(
        original_question=original_question.strip(),
        candidate_answer=candidate_answer.strip(),
    )


ADAPTIVE_FOLLOWUP_EXAMPLES = [
    {
        "original_question": "What is the purpose of database indexing?",
        "candidate_answer": "Indexing makes database queries faster.",
        "followup_prompt": (
            "You mentioned that indexing makes queries faster. "
            "Can you explain how an index helps the database locate records "
            "more efficiently and what trade-offs indexes introduce?"
        ),
    },
    {
        "original_question": "Explain how you would design a REST API.",
        "candidate_answer": "I would use HTTP methods and endpoints.",
        "followup_prompt": (
            "You mentioned HTTP methods and endpoints. "
            "Can you explain how you would structure the endpoints for a "
            "resource and handle errors consistently in your API?"
        ),
    },
    {
        "original_question": "Tell me about a time you faced a difficult team problem.",
        "candidate_answer": "My team had some communication issues, and we solved them.",
        "followup_prompt": (
            "You mentioned that communication issues affected your team. "
            "Can you describe what specifically caused the problem and what "
            "you personally did to help the team resolve it?"
        ),
    },
    {
        "original_question": "What happens when a user enters a URL in a browser?",
        "candidate_answer": "The browser sends a request to the server and gets the page.",
        "followup_prompt": (
            "You mentioned that the browser sends a request to the server. "
            "Can you walk through what happens before the server responds, "
            "including how the browser finds the destination?"
        ),
    },
    {
        "original_question": "How would you improve the performance of a slow application?",
        "candidate_answer": "I would optimize the code and database.",
        "followup_prompt": (
            "You mentioned optimizing the code and database. "
            "How would you identify the actual performance bottleneck first, "
            "and what specific optimization would you consider after finding it?"
        ),
    },
]


class QuestionBank:
    """Manages interview question storage, retrieval, and usage tracking"""

    CATEGORIES = ["technical", "behavioral", "situational"]
    DIFFICULTIES = ["easy", "medium", "hard"]

    def __init__(self):
        pass

    def add_question(
        self,
        text: str,
        category: str,
        difficulty: str = "medium",
        tags: list[str] | None = None,
    ) -> dict[str, Any]:
        """Add a new question to the bank"""
        category = category.strip().lower()
        difficulty = difficulty.strip().lower()

        if category not in self.CATEGORIES:
            raise ValueError(
                f"Invalid category: {category}. Must be one of: {self.CATEGORIES}"
            )
        if difficulty not in self.DIFFICULTIES:
            raise ValueError(
                f"Invalid difficulty: {difficulty}. Must be one of: {self.DIFFICULTIES}"
            )

        question_id = f"q_{uuid.uuid4().hex[:12]}"
        now = utcnow()

        db = SessionLocal()
        try:
            question = Question(
                question_id=question_id,
                text=text,
                category=category,
                difficulty=difficulty,
                tags=tags or [],
                usage_count=0,
                avg_score=None,
                created_at=now,
                updated_at=now,
            )
            db.add(question)
            db.commit()

            logger.info(f"Added question {question_id} [{category}/{difficulty}]")
            return {
                "question_id": question_id,
                "text": text,
                "category": category,
                "difficulty": difficulty,
                "tags": tags or [],
                "usage_count": 0,
                "avg_score": None,
                "created_at": now.isoformat(),
            }
        except Exception as e:
            db.rollback()
            logger.error(f"Error adding question: {e}")
            raise
        finally:
            db.close()

    def get_questions(
        self,
        category: str | None = None,
        difficulty: str | None = None,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        """List questions with optional filters"""
        db = SessionLocal()
        try:
            stmt = select(Question)
            if category:
                stmt = stmt.where(Question.category == category.strip().lower())
            if difficulty:
                stmt = stmt.where(Question.difficulty == difficulty.strip().lower())
            stmt = stmt.order_by(Question.created_at.desc()).limit(limit)
            rows = db.execute(stmt).scalars().all()

            return [
                {
                    "question_id": r.question_id,
                    "text": r.text,
                    "category": r.category,
                    "difficulty": r.difficulty,
                    "tags": r.tags or [],
                    "usage_count": r.usage_count,
                    "avg_score": r.avg_score,
                    "created_at": r.created_at.isoformat() if r.created_at else None,
                }
                for r in rows
            ]
        finally:
            db.close()

    def get_question(self, question_id: str) -> dict[str, Any] | None:
        """Get a single question by ID"""
        db = SessionLocal()
        try:
            q = db.execute(
                select(Question).where(Question.question_id == question_id)
            ).scalar_one_or_none()
            if not q:
                return None
            return {
                "question_id": q.question_id,
                "text": q.text,
                "category": q.category,
                "difficulty": q.difficulty,
                "tags": q.tags or [],
                "usage_count": q.usage_count,
                "avg_score": q.avg_score,
                "created_at": q.created_at.isoformat() if q.created_at else None,
            }
        finally:
            db.close()

    def get_next_question(
        self,
        category: str | None = None,
        exclude_ids: list[str] | None = None,
    ) -> dict[str, Any] | None:
        """Get next question, preferring less-used ones, optional category filter"""
        exclude_ids = exclude_ids or []
        db = SessionLocal()
        try:
            stmt = select(Question)
            if category:
                stmt = stmt.where(Question.category == category.strip().lower())
            stmt = stmt.order_by(Question.usage_count.asc(), Question.created_at.desc())
            rows = db.execute(stmt).scalars().all()

            for q in rows:
                if q.question_id not in exclude_ids:
                    return {
                        "question_id": q.question_id,
                        "text": q.text,
                        "category": q.category,
                        "difficulty": q.difficulty,
                        "tags": q.tags or [],
                        "usage_count": q.usage_count,
                    }
            return None
        finally:
            db.close()

    def record_usage(self, question_id: str, score: float | None = None) -> bool:
        """Increment usage count and optionally update running average score"""
        db = SessionLocal()
        try:
            q = db.execute(
                select(Question).where(Question.question_id == question_id)
            ).scalar_one_or_none()
            if not q:
                return False

            q.usage_count = (q.usage_count or 0) + 1
            if score is not None:
                if q.avg_score is None:
                    q.avg_score = score
                else:
                    count = q.usage_count
                    q.avg_score = ((q.avg_score * (count - 1)) + score) / count
            q.updated_at = utcnow()
            db.commit()
            return True
        except Exception as e:
            db.rollback()
            logger.error(f"Error recording usage for {question_id}: {e}")
            return False
        finally:
            db.close()


question_bank = QuestionBank()


class RetrievalProvider:
    """Adapter interface for personalized question retrieval."""

    def retrieve(
        self,
        candidate_id: str,
        resume_text: str,
        jd_text: str,
        count: int = 5,
    ) -> list[Any]:
        raise NotImplementedError


class DefaultRetrievalProvider(RetrievalProvider):
    """Adapter around the existing retrieval index."""

    def retrieve(
        self,
        candidate_id: str,
        resume_text: str,
        jd_text: str,
        count: int = 5,
    ) -> list[Any]:
        from retrieval.index import retrieve

        query = (
            f"Candidate: {candidate_id}\n"
            f"Resume:\n{resume_text}\n"
            f"Job Description:\n{jd_text}"
        )

        return retrieve(query, top_k=count)


_retrieval_provider: RetrievalProvider | None = None


def set_retrieval_provider(provider: RetrievalProvider | None) -> None:
    """Configure the retrieval provider used for personalized questions."""
    global _retrieval_provider
    _retrieval_provider = provider


def _legacy_questions(count: int) -> list[dict[str, Any]]:
    """Return questions from the legacy database question bank."""
    try:
        return question_bank.get_questions(limit=count)
    except Exception as exc:
        logger.warning("Legacy question bank unavailable: %s", exc)
        return []


def get_personalized_questions(
    candidate_id: str,
    resume_text: str,
    jd_text: str,
    count: int = 5,
) -> list[Any]:
    """
    Retrieve candidate-specific interview questions.

    Retrieval failures are intentionally isolated so an interview can
    continue using the legacy question bank.
    """
    if count <= 0:
        return []

    provider = _retrieval_provider or DefaultRetrievalProvider()

    try:
        results = provider.retrieve(
            candidate_id=candidate_id,
            resume_text=resume_text,
            jd_text=jd_text,
            count=count,
        )

        if results:
            return results[:count]

        logger.warning("Retrieval returned no questions; using legacy bank.")
    except Exception as exc:
        logger.warning("Personalized retrieval failed: %s", exc)

    return _legacy_questions(count)
