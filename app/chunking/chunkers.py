"""Chunking strategies.

A Chunk is a unit of text plus metadata used for retrieval. We provide four
strategies that share a common interface so they're interchangeable:

- fixed:        equal-size character windows with overlap
- recursive:    split on a separator hierarchy, then pack to target size
- parent_child: large parent chunks split into small child chunks (children are
                searched, the parent gives the model wider context)
- semantic:     group adjacent sentences while embedding similarity stays high

`semantic` takes an embedder so it can be unit-tested with a stub and run for
real with a sentence-transformer model.
"""

from __future__ import annotations

import re
import uuid
from dataclasses import dataclass, field
from typing import Protocol

from app.ingestion.base import ParsedDocument


@dataclass
class Chunk:
    text: str
    metadata: dict = field(default_factory=dict)
    id: str = field(default_factory=lambda: uuid.uuid4().hex)


class _Embedder(Protocol):
    def embed(self, texts: list[str]) -> list[list[float]]: ...


# ── helpers ────────────────────────────────────────────────────────────────
def _split_sentences(text: str) -> list[str]:
    parts = re.split(r"(?<=[.!?])\s+", text.strip())
    return [p.strip() for p in parts if p.strip()]


def _cosine(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b, strict=False))
    na = sum(x * x for x in a) ** 0.5
    nb = sum(y * y for y in b) ** 0.5
    if na == 0 or nb == 0:
        return 0.0
    return dot / (na * nb)


# ── strategies ─────────────────────────────────────────────────────────────
def fixed_chunks(text: str, size: int = 800, overlap: int = 100) -> list[str]:
    if size <= 0:
        raise ValueError("size must be positive")
    step = max(1, size - overlap)
    return [
        text[i : i + size]
        for i in range(0, max(1, len(text)), step)
        if text[i : i + size].strip()
    ]


def recursive_chunks(
    text: str,
    size: int = 800,
    overlap: int = 100,
    separators: tuple[str, ...] = ("\n\n", "\n", ". ", " ", ""),
) -> list[str]:
    """Split with the first separator that yields pieces under `size`, recursing
    into any piece still too large, then merge small pieces back up to `size`."""

    def _split(t: str, seps: tuple[str, ...]) -> list[str]:
        if len(t) <= size or not seps:
            return [t]
        sep, rest = seps[0], seps[1:]
        pieces = t.split(sep) if sep else list(t)
        out: list[str] = []
        for piece in pieces:
            piece = piece + sep if sep and piece else piece
            if len(piece) <= size:
                out.append(piece)
            else:
                out.extend(_split(piece, rest))
        return out

    pieces = _split(text, separators)
    merged: list[str] = []
    current = ""
    for piece in pieces:
        if len(current) + len(piece) <= size:
            current += piece
        else:
            if current.strip():
                merged.append(current.strip())
            current = (current[-overlap:] if overlap else "") + piece
    if current.strip():
        merged.append(current.strip())
    return merged


def semantic_chunks(
    text: str,
    embedder: _Embedder,
    threshold: float = 0.6,
    max_chars: int = 1200,
) -> list[str]:
    sentences = _split_sentences(text)
    if len(sentences) <= 1:
        return [text.strip()] if text.strip() else []
    vectors = embedder.embed(sentences)
    chunks: list[str] = []
    current = [sentences[0]]
    for i in range(1, len(sentences)):
        sim = _cosine(vectors[i - 1], vectors[i])
        joined_len = sum(len(s) + 1 for s in current)
        if sim >= threshold and joined_len + len(sentences[i]) <= max_chars:
            current.append(sentences[i])
        else:
            chunks.append(" ".join(current))
            current = [sentences[i]]
    chunks.append(" ".join(current))
    return chunks


def parent_child_chunks(
    text: str,
    parent_size: int = 2000,
    child_size: int = 400,
    child_overlap: int = 50,
) -> list[tuple[str, str]]:
    """Return (child_text, parent_text) pairs. Children are what you embed and
    search; the parent text travels with each child for wider context."""
    parents = recursive_chunks(text, size=parent_size, overlap=0)
    pairs: list[tuple[str, str]] = []
    for parent in parents:
        for child in recursive_chunks(parent, size=child_size, overlap=child_overlap):
            pairs.append((child, parent))
    return pairs


# ── document-level entry point ─────────────────────────────────────────────
def chunk_document(
    doc: ParsedDocument,
    strategy: str = "recursive",
    embedder: _Embedder | None = None,
    **kwargs,
) -> list[Chunk]:
    """Chunk every page of a document, attaching page number + ordering metadata."""
    chunks: list[Chunk] = []
    for page in doc.pages:
        base_meta = {
            "source": doc.filename,
            "page_number": page.page_number,
            "chunker": strategy,
        }
        if strategy == "fixed":
            texts = fixed_chunks(page.text, **kwargs)
            for idx, t in enumerate(texts):
                chunks.append(Chunk(text=t, metadata={**base_meta, "chunk_index": idx}))
        elif strategy == "recursive":
            texts = recursive_chunks(page.text, **kwargs)
            for idx, t in enumerate(texts):
                chunks.append(Chunk(text=t, metadata={**base_meta, "chunk_index": idx}))
        elif strategy == "semantic":
            if embedder is None:
                raise ValueError("semantic strategy requires an embedder")
            texts = semantic_chunks(page.text, embedder, **kwargs)
            for idx, t in enumerate(texts):
                chunks.append(Chunk(text=t, metadata={**base_meta, "chunk_index": idx}))
        elif strategy == "parent_child":
            for idx, (child, parent) in enumerate(
                parent_child_chunks(page.text, **kwargs)
            ):
                chunks.append(
                    Chunk(
                        text=child,
                        metadata={
                            **base_meta,
                            "chunk_index": idx,
                            "parent_text": parent,
                        },
                    )
                )
        else:
            raise ValueError(f"Unknown chunking strategy: {strategy}")
    return chunks
