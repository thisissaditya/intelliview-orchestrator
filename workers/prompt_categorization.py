"""
Prompt Categorization Module

Automatically classifies prompts based on their intent.
"""

import re

PROMPT_CATEGORIES = {
    "Coding": [
        "python",
        "java",
        "c++",
        "program",
        "algorithm",
        "function",
        "debug",
        "code",
        "script",
    ],
    "Database": ["sql", "mysql", "postgres", "database", "query", "join", "table"],
    "DevOps": ["docker", "kubernetes", "jenkins", "ci/cd", "linux", "deployment"],
    "Interview": ["interview", "hr", "technical", "behavioral", "question"],
    "AI/ML": [
        "machine learning",
        "deep learning",
        "neural",
        "llm",
        "transformer",
        "tensorflow",
        "pytorch",
    ],
}


def categorize_prompt(prompt: str) -> str:
    """
    Categorize the prompt based on keywords.
    """

    text = prompt.lower()

    for category, keywords in PROMPT_CATEGORIES.items():
        for keyword in keywords:
            if re.search(rf"\b{re.escape(keyword)}\b", text):
                return category

    return "General"
