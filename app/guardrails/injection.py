"""Heuristic prompt-injection / jailbreak detection.

A curated set of patterns covering the common families: instruction-override,
system-prompt extraction, role/persona jailbreaks, and guardrail-bypass requests.
Returns the labels that fired so callers can log *why* something was blocked.
"""

import re

_PATTERNS: list[tuple[re.Pattern, str]] = [
    (
        re.compile(
            r"ignore\s+(all\s+|the\s+)?(previous|prior|above|earlier)\s+(instructions|prompts?|messages?|rules?)",
            re.I,
        ),
        "ignore-previous-instructions",
    ),
    (
        re.compile(
            r"disregard\s+(all\s+|the\s+)?(previous|prior|above|earlier|safety)", re.I
        ),
        "disregard-previous",
    ),
    (
        re.compile(
            r"forget\s+(all\s+|everything\s+|your\s+)?(previous\s+)?(instructions|context|rules)",
            re.I,
        ),
        "forget-instructions",
    ),
    (
        re.compile(
            r"(reveal|show|print|repeat|expose|output|disclose)\s+(me\s+)?(your|the)\s+(system|hidden|initial|original|secret)\s+(prompt|instructions?|message)",
            re.I,
        ),
        "system-prompt-extraction",
    ),
    (
        re.compile(r"what\s+(is|are)\s+your\s+(system\s+)?(prompt|instructions)", re.I),
        "system-prompt-extraction",
    ),
    (
        re.compile(
            r"(you\s+are\s+now|act\s+as|pretend\s+to\s+be|roleplay\s+as)\s+(a\s+|an\s+)?(dan|unfiltered|unrestricted|jailbroken|evil|amoral)",
            re.I,
        ),
        "role-override",
    ),
    (re.compile(r"\bdeveloper\s+mode\b", re.I), "developer-mode"),
    (re.compile(r"\bdo\s+anything\s+now\b|\bDAN\b", re.I), "dan-jailbreak"),
    (
        re.compile(
            r"(bypass|override|disable|turn\s+off|circumvent)\s+(your\s+|the\s+|all\s+)?(safety|guard\s?rails?|restrictions?|filters?|rules?|policies)",
            re.I,
        ),
        "bypass-safety",
    ),
    (
        re.compile(
            r"pretend\s+(that\s+)?you\s+(are\s+not|have\s+no|don'?t\s+have)", re.I
        ),
        "pretend-override",
    ),
    (
        re.compile(
            r"without\s+(any\s+)?(restrictions?|filters?|rules?|censorship)", re.I
        ),
        "remove-restrictions",
    ),
]


def detect_prompt_injection(text: str) -> list[str]:
    """Return the labels of any injection patterns found in ``text`` (deduped)."""
    if not text:
        return []
    seen: list[str] = []
    for pattern, label in _PATTERNS:
        if pattern.search(text) and label not in seen:
            seen.append(label)
    return seen
