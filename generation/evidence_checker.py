"""
Evidence checking: validates that every question's quotes appear in their
referenced source texts.

This is the core safety mechanism — it prevents the generation engine from
producing questions that mention details not present in the evidence.
"""

from __future__ import annotations

import re
from typing import Union

from .models import (
    EvidenceChunk,
    ExperienceEntry,
    Question,
)


def normalize_text(text: str) -> str:
    """Normalize text for comparison: lowercase, collapse whitespace."""
    return re.sub(r"\s+", " ", text.lower().strip())


def check_question_evidence(
    question: Question,
    chunks: dict[str, EvidenceChunk],
    experiences: dict[str, ExperienceEntry],
) -> bool:
    """
    Validate that every evidence item in the question has a quote that
    appears verbatim (ignoring case and extra whitespace) in the referenced
    source text.

    Args:
        question: The question to validate.
        chunks: Map of chunk_id -> EvidenceChunk.
        experiences: Map of experience_id -> ExperienceEntry.

    Returns:
        True if all evidence is valid, False otherwise.
    """
    for ev in question.evidence:
        quote_norm = normalize_text(ev.quote)

        # Empty quotes cannot validate evidence — reject them
        if not quote_norm:
            return False

        if ev.kind.value == "chunk":
            chunk = chunks.get(ev.ref_id)
            if chunk is None:
                return False
            source_norm = normalize_text(chunk.text)
            if quote_norm not in source_norm:
                return False

        elif ev.kind.value == "experience":
            exp = experiences.get(ev.ref_id)
            if exp is None:
                return False
            source_norm = normalize_text(exp.question_text)
            if quote_norm not in source_norm:
                return False

    return True


def filter_valid_questions(
    questions: list[Question],
    chunks: dict[str, EvidenceChunk],
    experiences: dict[str, ExperienceEntry],
) -> list[Question]:
    """
    Return only questions that pass the evidence check.
    """
    return [
        q for q in questions
        if check_question_evidence(q, chunks, experiences)
    ]