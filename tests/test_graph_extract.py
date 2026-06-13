"""Tests for entity/relationship extraction (Phase 4, Module 12)."""

from app.graph.extract import RuleBasedEntityExtractor, extract_candidate_names


def test_extracts_works_for_relationship():
    res = RuleBasedEntityExtractor().extract("Alice Johnson works for Acme Corp.")
    rels = {(r.source, r.type, r.target) for r in res.relationships}
    assert ("Alice Johnson", "WORKS_FOR", "Acme Corp") in rels
    types = {e.name: e.type for e in res.entities}
    assert types["Alice Johnson"] == "Person"
    assert types["Acme Corp"] == "Company"


def test_extracts_reports_to_and_manages():
    text = "Bob Smith reports to Carol Lee. Carol Lee manages Dave Park."
    res = RuleBasedEntityExtractor().extract(text)
    rels = {(r.source, r.type, r.target) for r in res.relationships}
    assert ("Bob Smith", "REPORTS_TO", "Carol Lee") in rels
    assert ("Carol Lee", "MANAGES", "Dave Park") in rels


def test_department_classification_with_article():
    res = RuleBasedEntityExtractor().extract(
        "Bob Smith manages the Engineering department."
    )
    rels = {(r.source, r.type, r.target) for r in res.relationships}
    assert ("Bob Smith", "MANAGES", "Engineering") in rels
    types = {e.name: e.type for e in res.entities}
    assert types["Engineering"] == "Department"


def test_candidate_names_overinclusive():
    names = extract_candidate_names("Who does Alice Johnson report to?")
    assert "Alice Johnson" in names
