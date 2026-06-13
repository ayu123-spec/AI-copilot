"""Extract entities and relationships from text.

Two backends behind one :class:`EntityExtractor` interface:

* :class:`RuleBasedEntityExtractor` — deterministic and offline. Recognises
  proper-noun phrases and a fixed set of relationship verb patterns
  (``works for``, ``manages``, ``reports to``, ...), typing entities by simple
  suffix/keyword heuristics. Powers tests and dependency-free local use.
* :class:`LLMEntityExtractor` — prompts a generator for JSON and parses it, for
  higher-quality extraction in production.
"""

import json
import re
from abc import ABC, abstractmethod
from dataclasses import dataclass, field

from app.graph.base import Entity, Relationship
from app.rag.llm import Generator

_PROPER = r"[A-Z][\w&-]*(?:\s+[A-Z][\w&-]*){0,3}"

# (verb regex, relation type, default source type, default target type)
_PATTERNS: list[tuple[str, str, str, str]] = [
    (r"works?\s+for", "WORKS_FOR", "Person", "Company"),
    (r"works?\s+at", "WORKS_FOR", "Person", "Company"),
    (r"is\s+employed\s+by", "WORKS_FOR", "Person", "Company"),
    (r"reports?\s+to", "REPORTS_TO", "Person", "Person"),
    (r"manages?", "MANAGES", "Person", "Person"),
    (r"leads?", "MANAGES", "Person", "Department"),
    (r"heads?", "MANAGES", "Person", "Department"),
    (r"works?\s+on", "WORKS_ON", "Person", "Project"),
    (r"is\s+part\s+of", "PART_OF", "Department", "Company"),
    (r"belongs?\s+to", "PART_OF", "Department", "Company"),
]

_COMPANY_SUFFIXES = (
    " inc", " inc.", " corp", " corp.", " corporation", " ltd", " ltd.", " llc",
    " co", " co.", " company", " technologies", " systems", " labs", " group",
    " ventures", " partners", " solutions",
)  # fmt: skip
_DEPARTMENT_KEYWORDS = (
    "engineering", "sales", "marketing", "finance", "legal", "operations",
    "product", "support", "research", "human resources", "design", "analytics",
)  # fmt: skip


@dataclass
class ExtractionResult:
    entities: list[Entity] = field(default_factory=list)
    relationships: list[Relationship] = field(default_factory=list)


def _classify(name: str, default: str) -> str:
    low = " " + name.lower()
    if any(low.endswith(s) for s in _COMPANY_SUFFIXES):
        return "Company"
    if low.strip().startswith("project "):
        return "Project"
    if any(k in low for k in _DEPARTMENT_KEYWORDS):
        return "Department"
    return default


_PROPER_RE = re.compile(_PROPER)


def extract_candidate_names(text: str) -> list[str]:
    """Every proper-noun phrase in the text, for query-time entity spotting.

    Deliberately over-inclusive (it will also catch a sentence-initial word like
    "Who"): callers match these against the graph and silently drop the misses.
    """
    seen: list[str] = []
    for match in _PROPER_RE.finditer(text):
        name = match.group(0).strip(" .,")
        if name and name not in seen:
            seen.append(name)
    return seen


class EntityExtractor(ABC):
    @abstractmethod
    def extract(self, text: str) -> ExtractionResult:
        """Extract entities and relationships from a block of text."""


class RuleBasedEntityExtractor(EntityExtractor):
    def __init__(self) -> None:
        self._compiled = [
            (
                re.compile(rf"({_PROPER})\s+{verb}\s+(?:the\s+|an?\s+)?({_PROPER})"),
                rel,
                st,
                tt,
            )
            for verb, rel, st, tt in _PATTERNS
        ]
        self._standalone = re.compile(_PROPER)

    def extract(self, text: str) -> ExtractionResult:
        entities: dict[tuple[str, str], Entity] = {}
        relationships: dict[tuple[str, str, str], Relationship] = {}

        def add_entity(name: str, type_: str) -> str:
            name = name.strip(" .,")
            type_ = _classify(name, type_)
            entities.setdefault((name.lower(), type_), Entity(name=name, type=type_))
            return type_

        for pattern, rel, src_type, tgt_type in self._compiled:
            for match in pattern.finditer(text):
                source = match.group(1).strip(" .,")
                target = match.group(2).strip(" .,")
                st = add_entity(source, src_type)
                tt = add_entity(target, tgt_type)
                relationships.setdefault(
                    (source.lower(), rel, target.lower()),
                    Relationship(
                        source=source,
                        target=target,
                        type=rel,
                        source_type=st,
                        target_type=tt,
                    ),
                )

        # Standalone typed entities (companies, departments, projects) so the
        # graph has nodes even where no relationship verb was matched.
        for match in self._standalone.finditer(text):
            name = match.group(0).strip(" .,")
            type_ = _classify(name, "Person")
            if type_ != "Person":  # skip bare capitalised words to avoid noise
                entities.setdefault(
                    (name.lower(), type_), Entity(name=name, type=type_)
                )

        return ExtractionResult(
            entities=list(entities.values()),
            relationships=list(relationships.values()),
        )


class LLMEntityExtractor(EntityExtractor):
    """Prompt a generator for JSON entities/relationships and parse the result."""

    _SYSTEM = (
        "Extract entities and relationships from the text as JSON with this exact "
        "shape: "
        '{"entities":[{"name":"...","type":"Person|Company|Project|Department"}],'
        '"relationships":[{"source":"...","target":"...",'
        '"type":"WORKS_FOR|MANAGES|REPORTS_TO|PART_OF|WORKS_ON"}]}. '
        "Return only the JSON, with no commentary or code fences."
    )

    def __init__(self, generator: Generator) -> None:
        self._gen = generator

    def extract(self, text: str) -> ExtractionResult:
        raw = self._gen.generate(self._SYSTEM, text).strip()
        if raw.startswith("```"):
            raw = raw.strip("`")
            raw = raw[4:] if raw[:4].lower() == "json" else raw
        try:
            data = json.loads(raw)
        except (ValueError, TypeError):
            return ExtractionResult()
        entities = [
            Entity(name=e["name"], type=e.get("type", "Entity"))
            for e in data.get("entities", [])
            if e.get("name")
        ]
        relationships = [
            Relationship(
                source=r["source"], target=r["target"], type=r.get("type", "RELATED_TO")
            )
            for r in data.get("relationships", [])
            if r.get("source") and r.get("target")
        ]
        return ExtractionResult(entities=entities, relationships=relationships)
