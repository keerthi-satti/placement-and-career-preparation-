"""
Tests for the evidence checker module.

Run with: pytest generation/tests/test_evidence_check.py -v
"""

import json
from pathlib import Path

import pytest

from generation.evidence_checker import check_question_evidence, filter_valid_questions
from generation.models import (
    Difficulty,
    Evidence,
    EvidenceChunk,
    EvidenceKind,
    ExperienceEntry,
    Question,
    QuestionType,
)

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture
def sample_chunks():
    data = json.loads((FIXTURES / "project_contexts.json").read_text())
    chunks = {}
    for pc in data:
        for c in pc["evidence_chunks"]:
            chunks[c["chunk_id"]] = EvidenceChunk(**c)
    return chunks


@pytest.fixture
def sample_experiences():
    data = json.loads((FIXTURES / "experiences.json").read_text())
    return {e["id"]: ExperienceEntry(**e) for e in data}


def _make_question(
    text: str = "Test question?",
    evidence: list[dict] | None = None,
    qtype: QuestionType = QuestionType.PROJECT,
    project_id: str | None = "p1",
) -> Question:
    if evidence is None:
        evidence = [{"kind": "chunk", "ref_id": "p1-readme-01", "quote": "React frontend"}]
    return Question(
        id="q_test",
        text=text,
        hint="Test hint",
        type=qtype,
        difficulty=Difficulty.MEDIUM,
        project_id=project_id,
        evidence=[Evidence(**e) for e in evidence],
    )


class TestCheckQuestionEvidence:
    def test_valid_chunk_evidence(self, sample_chunks, sample_experiences):
        q = _make_question(
            evidence=[{"kind": "chunk", "ref_id": "p1-readme-01", "quote": "React frontend, Express.js REST API"}]
        )
        assert check_question_evidence(q, sample_chunks, sample_experiences) is True

    def test_invalid_chunk_quote(self, sample_chunks, sample_experiences):
        q = _make_question(
            evidence=[{"kind": "chunk", "ref_id": "p1-readme-01", "quote": "this text does not exist anywhere"}]
        )
        assert check_question_evidence(q, sample_chunks, sample_experiences) is False

    def test_missing_chunk_id(self, sample_chunks, sample_experiences):
        q = _make_question(
            evidence=[{"kind": "chunk", "ref_id": "nonexistent_id", "quote": "React frontend"}]
        )
        assert check_question_evidence(q, sample_chunks, sample_experiences) is False

    def test_valid_experience_evidence(self, sample_chunks, sample_experiences):
        q = _make_question(
            qtype=QuestionType.EXPERIENCE,
            project_id=None,
            evidence=[
                {"kind": "chunk", "ref_id": "p1-readme-01", "quote": "PostgreSQL database"},
                {"kind": "experience", "ref_id": "e_001", "quote": "design a schema for a social media application"},
            ],
        )
        assert check_question_evidence(q, sample_chunks, sample_experiences) is True

    def test_case_insensitive_matching(self, sample_chunks, sample_experiences):
        q = _make_question(
            evidence=[{"kind": "chunk", "ref_id": "p1-readme-01", "quote": "REACT FRONTEND"}]
        )
        assert check_question_evidence(q, sample_chunks, sample_experiences) is True

    def test_whitespace_normalization(self, sample_chunks, sample_experiences):
        q = _make_question(
            evidence=[{"kind": "chunk", "ref_id": "p1-readme-01", "quote": "React  frontend,  Express.js  REST  API"}]
        )
        assert check_question_evidence(q, sample_chunks, sample_experiences) is True

    def test_experience_with_invalid_quote(self, sample_chunks, sample_experiences):
        q = _make_question(
            qtype=QuestionType.EXPERIENCE,
            project_id=None,
            evidence=[
                {"kind": "chunk", "ref_id": "p1-readme-01", "quote": "PostgreSQL database"},
                {"kind": "experience", "ref_id": "e_001", "quote": "completely fabricated quote that does not exist"},
            ],
        )
        assert check_question_evidence(q, sample_chunks, sample_experiences) is False

    def test_partial_quote_match(self, sample_chunks, sample_experiences):
        """A quote that is a substring of the source should pass."""
        q = _make_question(
            evidence=[{"kind": "chunk", "ref_id": "p1-readme-01", "quote": "React frontend"}]
        )
        assert check_question_evidence(q, sample_chunks, sample_experiences) is True

    def test_empty_quote(self, sample_chunks, sample_experiences):
        """An empty quote should fail — it provides no evidence."""
        q = _make_question(
            evidence=[{"kind": "chunk", "ref_id": "p1-readme-01", "quote": ""}]
        )
        assert check_question_evidence(q, sample_chunks, sample_experiences) is False

    def test_whitespace_only_quote(self, sample_chunks, sample_experiences):
        """A whitespace-only quote should fail — it provides no evidence."""
        q = _make_question(
            evidence=[{"kind": "chunk", "ref_id": "p1-readme-01", "quote": "   "}]
        )
        assert check_question_evidence(q, sample_chunks, sample_experiences) is False


class TestFilterValidQuestions:
    def test_filters_out_invalid(self, sample_chunks, sample_experiences):
        valid = _make_question(
            text="Valid?",
            evidence=[{"kind": "chunk", "ref_id": "p1-readme-01", "quote": "React frontend"}],
        )
        invalid = _make_question(
            text="Invalid?",
            evidence=[{"kind": "chunk", "ref_id": "p1-readme-01", "quote": "this is not in the text at all"}],
        )
        result = filter_valid_questions([valid, invalid], sample_chunks, sample_experiences)
        assert len(result) == 1
        assert result[0].text == "Valid?"

    def test_empty_list(self, sample_chunks, sample_experiences):
        assert filter_valid_questions([], sample_chunks, sample_experiences) == []

    def test_all_valid(self, sample_chunks, sample_experiences):
        questions = [
            _make_question(
                text=f"Q{i}?",
                evidence=[{"kind": "chunk", "ref_id": "p1-readme-01", "quote": "React frontend"}],
            )
            for i in range(3)
        ]
        result = filter_valid_questions(questions, sample_chunks, sample_experiences)
        assert len(result) == 3

    def test_all_invalid(self, sample_chunks, sample_experiences):
        questions = [
            _make_question(
                text=f"Q{i}?",
                evidence=[{"kind": "chunk", "ref_id": "p1-readme-01", "quote": "completely fake quote"}],
            )
            for i in range(3)
        ]
        result = filter_valid_questions(questions, sample_chunks, sample_experiences)
        assert len(result) == 0

    def test_mixed_chunk_and_experience(self, sample_chunks, sample_experiences):
        chunk_q = _make_question(
            text="Chunk Q?",
            evidence=[{"kind": "chunk", "ref_id": "p1-readme-01", "quote": "React frontend"}],
        )
        exp_q = _make_question(
            text="Exp Q?",
            qtype=QuestionType.EXPERIENCE,
            project_id=None,
            evidence=[
                {"kind": "chunk", "ref_id": "p1-readme-01", "quote": "PostgreSQL database"},
                {"kind": "experience", "ref_id": "e_001", "quote": "design a schema for a social media application"},
            ],
        )
        result = filter_valid_questions([chunk_q, exp_q], sample_chunks, sample_experiences)
        assert len(result) == 2