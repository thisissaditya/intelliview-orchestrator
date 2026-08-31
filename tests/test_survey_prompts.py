"""Tests for the post-interview candidate NPS survey prompts."""

import pytest

from workers.prompts import (
    CANDIDATE_SURVEY_PROMPT,
    SURVEY_EXTRACTION_PROMPT,
    nps_category,
)

# ---------------------------------------------------------------------------
# Template formatting — pure Python, always runs
# ---------------------------------------------------------------------------


def test_candidate_survey_prompt_formats_without_error():
    """CANDIDATE_SURVEY_PROMPT must accept {company_name} without KeyError."""
    result = CANDIDATE_SURVEY_PROMPT.format(company_name="Acme Corp")
    assert "Acme Corp" in result


def test_candidate_survey_prompt_contains_company_name_twice():
    """The template references {company_name} in both the question and the
    redirect rule, so it should appear at least twice after formatting."""
    result = CANDIDATE_SURVEY_PROMPT.format(company_name="TestCo")
    assert result.count("TestCo") >= 2


def test_survey_extraction_prompt_formats_without_error():
    """SURVEY_EXTRACTION_PROMPT must accept {candidate_reply} without KeyError."""
    result = SURVEY_EXTRACTION_PROMPT.format(candidate_reply="9 - loved the process")
    assert "9 - loved the process" in result


def test_survey_extraction_prompt_contains_json_braces():
    """After formatting, the extraction prompt must still contain literal
    JSON braces from the example shape — i.e. the doubled braces resolved."""
    result = SURVEY_EXTRACTION_PROMPT.format(candidate_reply="placeholder")
    assert '"nps_score"' in result
    assert '"verbatim"' in result
    assert '"declined"' in result
    assert '"notes"' in result


# ---------------------------------------------------------------------------
# nps_category helper — pure Python, always runs
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("score", "expected"),
    [
        (10, "promoter"),
        (9, "promoter"),
        (8, "passive"),
        (7, "passive"),
        (6, "detractor"),
        (5, "detractor"),
        (3, "detractor"),
        (0, "detractor"),
        (None, None),
    ],
)
def test_nps_category(score, expected):
    assert nps_category(score) == expected


# ---------------------------------------------------------------------------
# Extraction expectations — these document the intended mapping.
# The extraction itself requires a model call; pure-Python tests above
# validate the template and helper without one.
# ---------------------------------------------------------------------------

EXTRACTION_CASES = [
    {
        "reply": "9 - the questions were relevant to the JD",
        "expected_nps_score": 9,
        "expected_declined": False,
    },
    {
        "reply": "I'd say eight. Bit rushed at the end.",
        "expected_nps_score": 8,
        "expected_declined": False,
    },
    {
        "reply": "8/10",
        "expected_nps_score": 8,
        "expected_declined": False,
    },
    {
        "reply": "Honestly a 3. The audio kept cutting out.",
        "expected_nps_score": 3,
        "expected_declined": False,
    },
    {
        "reply": "That was great, thanks!",
        "expected_nps_score": None,
        "expected_declined": False,
    },
    {
        "reply": "10/10 would do again",
        "expected_nps_score": 10,
        "expected_declined": False,
    },
    {
        "reply": "11 out of 10!!",
        "expected_nps_score": 10,
        "expected_declined": False,
    },
    {
        "reply": "maybe 7 or 8",
        "expected_nps_score": 7,
        "expected_declined": False,
    },
    {
        "reply": "rather not say",
        "expected_nps_score": None,
        "expected_declined": True,
    },
    {
        "reply": "zero. worst process I've been through",
        "expected_nps_score": 0,
        "expected_declined": False,
    },
]


@pytest.mark.parametrize(
    "case",
    EXTRACTION_CASES,
    ids=[c["reply"][:40] for c in EXTRACTION_CASES],
)
def test_extraction_prompt_formats_with_each_reply(case):
    """Ensure the extraction template can be formatted with every test reply."""
    result = SURVEY_EXTRACTION_PROMPT.format(candidate_reply=case["reply"])
    assert case["reply"] in result


@pytest.mark.parametrize(
    "case",
    EXTRACTION_CASES,
    ids=[c["reply"][:40] for c in EXTRACTION_CASES],
)
def test_nps_category_matches_expected_score(case):
    """Verify nps_category returns the correct bucket for expected scores."""
    score = case["expected_nps_score"]
    category = nps_category(score)

    if score is None:
        assert category is None
    elif score >= 9:
        assert category == "promoter"
    elif score >= 7:
        assert category == "passive"
    else:
        assert category == "detractor"
