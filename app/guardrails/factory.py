"""Builds the Guardrails instance from settings."""

from app.core.config import settings
from app.guardrails.guard import Guardrails

_guardrails: Guardrails | None = None


def get_guardrails() -> Guardrails:
    """Process-wide singleton configured from settings. Overridable in tests."""
    global _guardrails
    if _guardrails is None:
        _guardrails = Guardrails(
            block_injection=settings.GUARDRAIL_BLOCK_INJECTION,
            redact_pii=settings.GUARDRAIL_REDACT_PII,
            redact_pii_in_input=settings.GUARDRAIL_REDACT_PII_IN_INPUT,
            min_faithfulness=settings.GUARDRAIL_MIN_FAITHFULNESS,
            toxicity_denylist=settings.GUARDRAIL_TOXICITY_DENYLIST,
        )
    return _guardrails
