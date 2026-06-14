"""A small, fixed regression dataset for end-to-end answer evaluation.

Keeping the corpus and cases version-controlled makes evaluation re-runnable and
comparable across changes (the point of a regression set). Numbers are meaningful
with a real LLM/embedding backend; with the offline fakes they are illustrative.
"""

from app.evaluation.answer_harness import EvalCaseQA

CORPUS = {
    "finance.txt": (
        "The company reported that quarterly revenue grew 20 percent, "
        "driven by cloud services and enterprise subscriptions."
    ),
    "hr.txt": (
        "Employees are entitled to 25 days of paid annual leave and "
        "flexible remote working arrangements."
    ),
    "security.txt": (
        "All customer data is encrypted at rest using AES-256 and "
        "access requires multi-factor authentication."
    ),
    "product.txt": (
        "The product roadmap prioritizes a mobile app, offline sync, "
        "and a public API for integrations."
    ),
}

REGRESSION_CASES = [
    EvalCaseQA(
        query="How much did quarterly revenue grow?",
        relevant_substring="20 percent",
        reference_answer=(
            "Quarterly revenue grew 20 percent, driven by cloud services and "
            "enterprise subscriptions."
        ),
    ),
    EvalCaseQA(
        query="How many paid annual leave days do employees get?",
        relevant_substring="25 days",
        reference_answer="Employees are entitled to 25 days of paid annual leave.",
    ),
    EvalCaseQA(
        query="How is customer data protected at rest?",
        relevant_substring="AES-256",
        reference_answer=(
            "Customer data is encrypted at rest using AES-256, and access "
            "requires multi-factor authentication."
        ),
    ),
    EvalCaseQA(
        query="What is on the product roadmap?",
        relevant_substring="roadmap",
        reference_answer=(
            "The product roadmap prioritizes a mobile app, offline sync, and a "
            "public API for integrations."
        ),
    ),
]
