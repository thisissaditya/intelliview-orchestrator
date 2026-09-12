from workers.prompt_categorization import categorize_prompt


def test_existing_coding_category():
    assert categorize_prompt("How do I debug a Python program?") == "Coding"


def test_existing_database_category():
    assert categorize_prompt("Write a SQL query for a database table.") == "Database"


def test_existing_devops_category():
    assert categorize_prompt("How do I deploy an application using Docker?") == "DevOps"


def test_existing_interview_category():
    assert (
        categorize_prompt("What questions are asked in a technical interview?")
        == "Interview"
    )


def test_existing_ai_category():
    assert categorize_prompt("Explain deep learning and neural networks.") == "AI/ML"


def test_system_design_category():
    assert (
        categorize_prompt("Explain system design for a web application.")
        == "System Design"
    )


def test_security_category():
    assert categorize_prompt("Explain cybersecurity best practices.") == "Security"


def test_frontend_category():
    assert categorize_prompt("How do I build a React application?") == "Frontend"
