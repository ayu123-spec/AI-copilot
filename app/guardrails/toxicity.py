"""Blocked-term detection.

A deliberately simple, configurable denylist check (empty by default). Real
deployments can extend the denylist via ``GUARDRAIL_TOXICITY_DENYLIST`` or layer
an LLM/moderation API on top; the interface stays the same.
"""


def contains_blocked_terms(text: str, denylist: list[str]) -> list[str]:
    """Return the denylisted terms found in ``text`` (case-insensitive)."""
    if not text or not denylist:
        return []
    lowered = text.lower()
    return [term for term in denylist if term.lower() in lowered]
