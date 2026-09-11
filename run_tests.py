import os
import sys

# Add workspace to path so database module can be imported
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from database.models.candidate import Base, Candidate


def main():
    print("Setting up in-memory SQLite database for testing...")
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)

    Session = sessionmaker(bind=engine)
    session = Session()

    print("\n--- TEST 1: Distinct Candidate ---")
    print("Registering: John Doe (john.doe@example.com)")
    c1 = Candidate.register_candidate(session, "John Doe", "john.doe@example.com")
    print(f"Result: needs_review = {c1.needs_review} (Expected: False)")

    print("\n--- TEST 2: Near-Duplicate Name ---")
    print("Registering: Jon Doe (different@example.com)")
    c2 = Candidate.register_candidate(session, "Jon Doe", "different@example.com")
    print(f"Result: needs_review = {c2.needs_review} (Expected: True)")

    print("\n--- TEST 3: Near-Duplicate Email ---")
    print("Registering: Jane Smith (john.doe1@example.com)")
    c3 = Candidate.register_candidate(session, "Jane Smith", "john.doe1@example.com")
    print(f"Result: needs_review = {c3.needs_review} (Expected: True)")

    print("\n--- TEST 4: Another Distinct Candidate ---")
    print("Registering: Alice Wonderland (alice@example.com)")
    c4 = Candidate.register_candidate(session, "Alice Wonderland", "alice@example.com")
    print(f"Result: needs_review = {c4.needs_review} (Expected: False)")

    print("\nAll tests ran successfully!")


if __name__ == "__main__":
    main()
