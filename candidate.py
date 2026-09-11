import difflib

# pyrefly: ignore [missing-import]
from sqlalchemy import Boolean, Column, Integer, String

# pyrefly: ignore [missing-import]
from sqlalchemy.orm import declarative_base

Base = declarative_base()


class Candidate(Base):
    """
    Candidate model representing a registered candidate.
    """

    __tablename__ = "candidates"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, nullable=False)
    email = Column(String, nullable=False)
    needs_review = Column(
        Boolean, default=False, doc="Flagged if a near-duplicate exists"
    )

    @staticmethod
    def is_near_duplicate(session, new_name, new_email, threshold=0.85):
        """
        Detects if a new candidate's name or email is suspiciously similar to an existing one.

        Args:
            session: SQLAlchemy DB session.
            new_name (str): The name of the new candidate.
            new_email (str): The email of the new candidate.
            threshold (float): Similarity threshold (0.0 to 1.0).

        Returns:
            bool: True if a near-duplicate exists, False otherwise.
        """
        # Note: In a production environment with a massive dataset,
        # doing this purely in-memory over all records might be slow.
        # A DB-native fuzzy search (like pg_trgm in PostgreSQL) is recommended for scale.
        existing_candidates = session.query(Candidate).all()

        new_name_lower = new_name.lower().strip()
        new_email_lower = new_email.lower().strip()

        for existing in existing_candidates:
            existing_name = existing.name.lower().strip()
            existing_email = existing.email.lower().strip()

            # Exact email matches are always considered duplicates/near-duplicates
            if existing_email == new_email_lower:
                return True

            name_similarity = difflib.SequenceMatcher(
                None, new_name_lower, existing_name
            ).ratio()
            email_similarity = difflib.SequenceMatcher(
                None, new_email_lower, existing_email
            ).ratio()

            if name_similarity >= threshold or email_similarity >= threshold:
                return True

        return False

    @classmethod
    def register_candidate(cls, session, name, email):
        """
        Creates a new candidate and flags for review if it looks like a duplicate.
        """
        needs_review = cls.is_near_duplicate(session, name, email)

        new_candidate = cls(name=name, email=email, needs_review=needs_review)

        session.add(new_candidate)
        session.commit()
        return new_candidate
