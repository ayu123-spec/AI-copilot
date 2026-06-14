"""Guardrails: input/output safety checks for the RAG + agent pipeline.

Two layers:
  * input guards  — block prompt-injection / jailbreak attempts (and, optionally,
    blocked terms) before a query reaches the model.
  * output guards — redact PII/secrets from generated answers, flag low-grounding
    answers, and flag blocked terms.

Everything is deterministic and offline (regex + heuristics) so it runs in CI with
no model or network. An LLM-moderation backend can be layered on top later.
"""

from dataclasses import dataclass, field

# Returned to a user whose input was blocked by an input guard.
INJECTION_REFUSAL = (
    "I can't help with that request. It looks like an attempt to override my "
    "instructions. Ask me something about your workspace's knowledge instead."
)


@dataclass
class GuardrailResult:
    """Outcome of running a guard over a piece of text."""

    allowed: bool  # False => the input/output should be blocked
    text: str  # possibly-redacted text (use this downstream)
    action: str = "allow"  # "allow" | "block" | "redact" | "flag"
    reasons: list[str] = field(default_factory=list)  # human-readable triggers
    findings: dict = field(default_factory=dict)  # structured detail for logging

    @property
    def triggered(self) -> bool:
        return self.action != "allow"
