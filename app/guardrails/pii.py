"""PII and secret detection + redaction.

Used mainly on *outputs* to prevent the model from leaking sensitive data picked
up from documents or fabricated. Patterns are ordered so the most specific
(SSN, secrets) redact before looser numeric ones (phone, card, IP).
"""

import re

# (label, pattern). Order matters: specific patterns first.
_PATTERNS: list[tuple[str, re.Pattern]] = [
    ("EMAIL", re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")),
    ("AWS_KEY", re.compile(r"\bAKIA[0-9A-Z]{16}\b")),
    ("API_KEY", re.compile(r"\b(?:sk|pk|rk|ghp|xox[baprs])[-_][A-Za-z0-9]{16,}\b")),
    ("SSN", re.compile(r"\b\d{3}-\d{2}-\d{4}\b")),
    ("CREDIT_CARD", re.compile(r"\b(?:\d[ -]?){13,16}\b")),
    (
        "PHONE",
        re.compile(
            r"(?<!\d)(?:\+?\d{1,3}[\s.-]?)?\(?\d{3}\)?[\s.-]?\d{3}[\s.-]?\d{4}(?!\d)"
        ),
    ),
    ("IP", re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b")),
]


def detect_pii(text: str) -> list[tuple[str, str]]:
    """Return a list of (label, matched_value) for PII/secrets found in ``text``."""
    findings: list[tuple[str, str]] = []
    for label, pattern in _PATTERNS:
        for match in pattern.findall(text or ""):
            value = match if isinstance(match, str) else match[0]
            if value.strip():
                findings.append((label, value.strip()))
    return findings


def redact_pii(text: str) -> tuple[str, list[tuple[str, str]]]:
    """Replace PII/secrets with ``[REDACTED_<TYPE>]``.

    Returns the redacted text and the list of (label, original_value) removed.
    """
    if not text:
        return text, []
    findings: list[tuple[str, str]] = []
    redacted = text
    for label, pattern in _PATTERNS:

        def _sub(m: re.Match, label: str = label) -> str:
            findings.append((label, m.group(0).strip()))
            return f"[REDACTED_{label}]"

        redacted = pattern.sub(_sub, redacted)
    return redacted, findings
