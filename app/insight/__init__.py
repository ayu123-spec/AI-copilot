"""The Insight Engine: classify a question, then generate structured,
expert-level analysis instead of generic source regurgitation."""

from app.insight.classifier import QueryType, classify_query
from app.insight.prompts import build_system_prompt, build_user_prompt

__all__ = [
    "QueryType",
    "classify_query",
    "build_system_prompt",
    "build_user_prompt",
]
