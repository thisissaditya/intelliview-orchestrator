"""
Prompt templates for the automated interview preparation platform.

This module contains prompt definitions only.
It intentionally does not contain LLM clients, API wrappers, or
prompt-execution logic.
"""

# ---------------------------------------------------------------------------
# Evaluation Prompts
# ---------------------------------------------------------------------------

QUALITY_EVALUATION_PROMPT = (
    "You are an expert technical interviewer. "
    "Evaluate this candidate answer. "
    "Return a JSON object with keys: overall_quality_score (0-100), "
    "relevance (0-1), completeness (0-1), clarity (0-1), feedback (string)."
)

TECHNICAL_ACCURACY_PROMPT = (
    "You are a technical interviewer evaluating a candidate's answer. "
    "Return a JSON object with keys: accuracy_score (0-100), "
    "correct_concepts_count (int), incorrect_concepts_count (int), "
    "knowledge_gaps (list of strings)."
)

COMMUNICATION_EVALUATION_PROMPT = (
    "Evaluate the candidate's communication quality. "
    "Return a JSON object with keys: clarity_score (0-100), "
    "professionalism (0-100), confidence_level (0-1), "
    "pace_appropriateness (0-1)."
)


# ---------------------------------------------------------------------------
# Junior System Design Prompt Templates
# ---------------------------------------------------------------------------

JUNIOR_SYSTEM_DESIGN_SCALABILITY_PROMPT = (
    "Generate one junior-level system-design interview question focused "
    "on foundational scalability. The question should ask the candidate "
    "to reason about a simple application starting with a single server "
    "and explain when and why it should move toward a multi-tier or "
    "multi-server architecture. Include basic load balancing and "
    "horizontal scaling considerations. Keep the expected architecture "
    "simple and avoid advanced distributed-system concepts."
)

JUNIOR_SYSTEM_DESIGN_DATA_PROMPT = (
    "Generate one junior-level system-design interview question focused "
    "on basic data-storage decisions. The scenario should require the "
    "candidate to choose between a relational database and a NoSQL "
    "database and explain the reasoning behind the choice. The question "
    "may also involve a basic caching layer using Redis or Memcached. "
    "Keep the scale and requirements realistic for a junior engineer "
    "and avoid advanced consistency models, distributed transactions, "
    "or multi-region database architectures."
)

JUNIOR_SYSTEM_DESIGN_API_PROMPT = (
    "Generate one junior-level system-design interview question focused "
    "on designing and protecting a simple API. The question should test "
    "fundamental API rate limiting, basic load balancing, caching, and "
    "request-handling concepts. The candidate should explain where these "
    "components fit in the architecture and what problems they solve. "
    "Keep the problem bounded and avoid advanced event-driven systems, "
    "distributed transactions, multi-region replication, or complex "
    "failure-handling strategies."
)


# ---------------------------------------------------------------------------
# Senior System Design Prompt Templates
# ---------------------------------------------------------------------------

SENIOR_SYSTEM_DESIGN_DISTRIBUTED_PROMPT = (
    "Generate one senior-level system-design interview question involving "
    "a large-scale distributed system. The question must require the "
    "candidate to analyze architectural trade-offs involving throughput, "
    "latency, availability, consistency, and partition tolerance. Include "
    "a scenario where CAP theorem considerations and failure-domain "
    "isolation matter. The candidate should justify trade-offs rather "
    "than simply name technologies."
)

SENIOR_SYSTEM_DESIGN_MULTIREGION_PROMPT = (
    "Generate one senior-level system-design interview question involving "
    "a globally distributed, multi-region system. Require the candidate "
    "to reason about cross-region replication, consistency models, "
    "regional failures, asynchronous processing, event-driven "
    "backpressure, and recovery behavior. Include competing latency, "
    "availability, correctness, and operational-cost requirements. "
    "The question should require the candidate to clarify ambiguous "
    "business requirements before finalizing the architecture."
)

SENIOR_SYSTEM_DESIGN_TRANSACTIONS_PROMPT = (
    "Generate one senior-level system-design interview question involving "
    "multiple services that must coordinate state changes reliably at "
    "large scale. Require discussion of distributed transactions, "
    "idempotency, retries, partial failures, consistency guarantees, "
    "failure-domain isolation, and asynchronous event processing. "
    "Introduce ambiguous or competing business constraints such as "
    "cost versus latency or consistency versus availability. The "
    "candidate should identify assumptions, discuss alternatives, and "
    "justify the final architecture based on explicit trade-offs."
)


# ---------------------------------------------------------------------------
# System Design Prompt Registry
# ---------------------------------------------------------------------------

SYSTEM_DESIGN_PROMPT_CONFIGS = [
    {
        "domain": "system-design",
        "seniority": "junior",
        "prompt_template": JUNIOR_SYSTEM_DESIGN_SCALABILITY_PROMPT,
    },
    {
        "domain": "system-design",
        "seniority": "junior",
        "prompt_template": JUNIOR_SYSTEM_DESIGN_DATA_PROMPT,
    },
    {
        "domain": "system-design",
        "seniority": "junior",
        "prompt_template": JUNIOR_SYSTEM_DESIGN_API_PROMPT,
    },
    {
        "domain": "system-design",
        "seniority": "senior",
        "prompt_template": SENIOR_SYSTEM_DESIGN_DISTRIBUTED_PROMPT,
    },
    {
        "domain": "system-design",
        "seniority": "senior",
        "prompt_template": SENIOR_SYSTEM_DESIGN_MULTIREGION_PROMPT,
    },
    {
        "domain": "system-design",
        "seniority": "senior",
        "prompt_template": SENIOR_SYSTEM_DESIGN_TRANSACTIONS_PROMPT,
    },
]
PRODUCT_MANAGEMENT_PROMPTS = [
    {
        "domain": "product",
        "prompt_template": (
            "A food-delivery app can build only two of these four features this quarter: "
            "faster checkout, restaurant loyalty rewards, scheduled delivery, and a "
            "personalized home feed. Prioritize the features and explain your decision. "
            "Consider user impact, business value, strategic alignment, engineering effort, "
            "and trade-offs."
        ),
        "rubric_hint": (
            "Evaluate whether the candidate clearly defines the product goal and target "
            "users, establishes prioritization criteria, compares impact against effort, "
            "makes an explicit ranking, explains trade-offs, and states key assumptions."
        ),
    },
    {
        "domain": "product",
        "prompt_template": (
            "A ride-sharing app has budget to improve only one of three areas: reducing "
            "driver cancellation, improving rider pickup accuracy, or adding a loyalty "
            "program. As the product manager, prioritize one initiative and explain how "
            "you would decide between the options."
        ),
        "rubric_hint": (
            "Evaluate problem framing, identification of affected users, prioritization "
            "criteria, expected customer and business impact, effort or feasibility "
            "considerations, trade-off reasoning, and clarity of the final recommendation."
        ),
    },
    {
        "domain": "product",
        "prompt_template": (
            "You are the product manager for a music streaming app. Monthly active users "
            "are stable, but 30-day retention has fallen from 40% to 30%. Identify the "
            "metrics you would examine to diagnose the decline and explain how each metric "
            "would help you find the underlying problem."
        ),
        "rubric_hint": (
            "Evaluate whether the candidate distinguishes the north-star metric from "
            "diagnostic metrics, considers retention cohorts and segments, identifies "
            "activation and engagement metrics, proposes meaningful breakdowns, and "
            "connects metric changes to actionable hypotheses."
        ),
    },
    {
        "domain": "product",
        "prompt_template": (
            "A mobile payments product has increased new-user sign-ups by 25%, but the "
            "percentage of users completing their first payment has decreased. As the "
            "product manager, define the key metrics and funnel stages you would analyze "
            "to understand what is happening and decide what to improve first."
        ),
        "rubric_hint": (
            "Evaluate funnel understanding, metric selection, conversion analysis, "
            "segmentation, identification of possible drop-off points, prioritization "
            "of investigation areas, and the ability to turn metrics into product actions."
        ),
    },
    {
        "domain": "product",
        "prompt_template": (
            "Estimate the number of food-delivery orders placed in a large Indian city "
            "on an average day. State your assumptions, build a simple estimation model, "
            "calculate the estimate step by step, and explain which assumptions have the "
            "largest effect on the result."
        ),
        "rubric_hint": (
            "Evaluate whether the candidate defines the scope, uses reasonable and "
            "explicit assumptions, breaks the estimate into logical components, performs "
            "consistent calculations, checks the result for plausibility, and identifies "
            "the assumptions most sensitive to the final estimate."
        ),
    },
]

SDE_PROMPT_TEMPLATES = [
    {
        "domain": "sde",
        "difficulty": "easy",
        "prompt_template": (
            "Role: Act as an experienced Software Engineering interviewer. "
            "Context: Generate one technical SDE interview question for a candidate "
            "at an easy difficulty level. Focus on fundamental programming, "
            "object-oriented programming, basic data structures, databases, "
            "debugging, or core software engineering concepts. "
            "Constraints: The question must be clear, practical, and suitable for "
            "an entry-level SDE interview. Vary the topic and question style across "
            "generations. Do not repeat or closely rephrase previously generated "
            "questions. Do not provide the answer or explanation. Return only the "
            "interview question."
        ),
    },
    {
        "domain": "sde",
        "difficulty": "medium",
        "prompt_template": (
            "Role: Act as an experienced Software Engineering interviewer. "
            "Context: Generate one technical SDE interview question for a candidate "
            "at a medium difficulty level. Focus on algorithms, data structures, "
            "database design, SQL, REST APIs, concurrency, testing, debugging, "
            "or practical software engineering problem-solving. "
            "Constraints: The question should require reasoning or application of "
            "technical concepts rather than simple recall. Vary the topic, scenario, "
            "and problem style across generations. Do not repeat or closely rephrase "
            "previously generated questions. Do not provide the answer or explanation. "
            "Return only the interview question."
        ),
    },
    {
        "domain": "sde",
        "difficulty": "hard",
        "prompt_template": (
            "Role: Act as a senior Software Engineering interviewer conducting an "
            "advanced SDE interview. Context: Generate one challenging technical "
            "question involving system design, distributed systems, scalability, "
            "performance optimization, fault tolerance, concurrency, data-intensive "
            "systems, or advanced software architecture. "
            "Constraints: The question must require multi-step technical reasoning "
            "and should reflect real-world engineering challenges. Vary the system, "
            "constraints, and problem scenario across generations. Do not repeat or "
            "closely rephrase previously generated questions. Avoid questions that "
            "can be answered with simple definitions. Do not provide the answer or "
            "explanation. Return only the interview question."
        ),
    },
]


# ---------------------------------------------------------------------------
# Post-Interview Candidate NPS Survey
# ---------------------------------------------------------------------------

CANDIDATE_SURVEY_PROMPT = (
    "The interview is now complete. Thank the candidate for their time. "
    "In the same message, ask two optional questions and state plainly "
    "that the answers are about the interview process and do not affect "
    "their evaluation.\n\n"
    "Question 1: On a scale of 0 to 10, how likely are you to recommend "
    "interviewing at {company_name} to a friend or colleague?\n"
    "Question 2: What is the main reason for that score?\n\n"
    "Rules:\n"
    "- Both questions in a single message. Never split across turns.\n"
    "- Whole message under 60 words. No preamble, no small talk.\n"
    "- Neutral tone. No hoping they enjoyed it, no praise, no consolation, "
    "no hint about performance.\n"
    "- If they ask how they did or what happens next: brief answer that "
    "results come from the {company_name} team, then repeat the two "
    "questions once.\n"
    "- If they give a reason but no number, ask once for a 0-10 number "
    "and nothing more.\n"
    "- If they decline, skip, or still give no number, thank them and end. "
    "Never guess a score. Never ask a third time.\n"
    "- No probing, no follow-ups, no arguing with a low score."
)

SURVEY_EXTRACTION_PROMPT = (
    "Extract the candidate's NPS survey response from the text below. "
    "Return JSON only — no prose, no markdown fences.\n\n"
    "Candidate reply:\n{candidate_reply}\n\n"
    "Required JSON shape:\n"
    '{{"nps_score": <int 0-10 or null>, "verbatim": <string or null>, '
    '"declined": <bool>, "notes": <string or null>}}\n\n'
    "Rules:\n"
    "- Only fill nps_score if a number was actually stated. Words count "
    '("eight", "a solid nine"), as do "8/10" and "8 out of ten".\n'
    '- NEVER infer a score from tone. "That was great!" with no number '
    "is nps_score null, not 10. This is the most important rule.\n"
    '- A range ("8 or 9") takes the lower value; put the detail in notes.\n'
    '- Out-of-scale numbers clamp into 0-10 ("11/10" becomes 10); '
    "note the original value in notes.\n"
    "- verbatim is a lightly trimmed copy of what they said — no "
    "summarising, rewriting, or cleaning up their opinion.\n"
    "- declined is true only if they refused or skipped the survey.\n"
    "- If nothing usable is found, return nulls with declined false."
)


def nps_category(score):
    """Return the NPS category for a given score.

    Returns ``"promoter"`` for 9-10, ``"passive"`` for 7-8,
    ``"detractor"`` for 0-6, or ``None`` when *score* is ``None``.
    """
    if score is None:
        return None
    if score >= 9:
        return "promoter"
    if score >= 7:
        return "passive"
    return "detractor"
