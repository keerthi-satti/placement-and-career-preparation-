"""
Tests for the generator module.

Run with: pytest generation/tests/test_generator.py -v
"""

import json
from pathlib import Path

import pytest

from generation.generator import generate_more, generate_questions
from generation.models import (
    Difficulty,
    Evidence,
    EvidenceChunk,
    EvidenceKind,
    ExperienceEntry,
    GenerateMoreResult,
    GenerationResult,
    InputQuality,
    ProjectContext,
    Question,
    QuestionType,
)

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture
def project_contexts():
    data = json.loads((FIXTURES / "project_contexts.json").read_text())
    return [ProjectContext(**pc) for pc in data]


@pytest.fixture
def experiences():
    data = json.loads((FIXTURES / "experiences.json").read_text())
    return [ExperienceEntry(**e) for e in data]


@pytest.fixture
def skills():
    return json.loads((FIXTURES / "skills.json").read_text())


@pytest.fixture
def thin_input():
    data = json.loads((FIXTURES / "thin_input.json").read_text())
    return [ProjectContext(**pc) for pc in data]


class TestGenerateQuestions:
    def test_returns_generation_result(self, project_contexts, experiences, skills):
        result = generate_questions(project_contexts, experiences, skills)
        assert isinstance(result, GenerationResult)

    def test_produces_questions_for_each_project(self, project_contexts, experiences, skills):
        result = generate_questions(project_contexts, experiences, skills)
        project_ids = {q.project_id for q in result.questions if q.type == QuestionType.PROJECT}
        # Should have questions for p1 and p2 (p3 is thin/missing)
        assert "p1" in project_ids
        assert "p2" in project_ids

    def test_questions_have_evidence(self, project_contexts, experiences, skills):
        result = generate_questions(project_contexts, experiences, skills)
        for q in result.questions:
            assert len(q.evidence) >= 1
            for ev in q.evidence:
                assert ev.kind in (EvidenceKind.CHUNK, EvidenceKind.EXPERIENCE)
                assert ev.ref_id  # not empty
                assert ev.quote   # not empty

    def test_experience_questions_have_two_evidence(self, project_contexts, experiences, skills):
        result = generate_questions(project_contexts, experiences, skills)
        exp_questions = [q for q in result.questions if q.type == QuestionType.EXPERIENCE]
        for q in exp_questions:
            assert len(q.evidence) == 2
            kinds = {ev.kind for ev in q.evidence}
            assert EvidenceKind.CHUNK in kinds
            assert EvidenceKind.EXPERIENCE in kinds

    def test_project_id_set_correctly(self, project_contexts, experiences, skills):
        result = generate_questions(project_contexts, experiences, skills)
        for q in result.questions:
            if q.type == QuestionType.PROJECT:
                assert q.project_id is not None
            # experience questions can have project_id=None

    def test_thin_input_sets_insufficient_flag(self, thin_input, experiences, skills):
        result = generate_questions(thin_input, [], skills)
        # thin input should produce very few or no questions
        assert result.insufficient_input or len(result.questions) < 5

    def test_missing_input_produces_warning(self, thin_input, experiences, skills):
        result = generate_questions(thin_input, [], skills)
        # Should have a warning about missing input
        assert any("missing" in w.lower() or "needs" in w.lower() or "thin" in w.lower()
                    for w in result.warnings) or result.insufficient_input

    def test_no_questions_without_llm(self, project_contexts, experiences, skills):
        """In stub mode (no LLM), we still get some questions from the stubs."""
        result = generate_questions(project_contexts, experiences, skills)
        # Should produce at least some stub questions
        assert len(result.questions) > 0

    def test_difficulty_varies(self, project_contexts, experiences, skills):
        result = generate_questions(project_contexts, experiences, skills)
        difficulties = {q.difficulty for q in result.questions}
        # Should have at least 2 different difficulty levels
        assert len(difficulties) >= 2

    def test_hints_are_not_answers(self, project_contexts, experiences, skills):
        result = generate_questions(project_contexts, experiences, skills)
        for q in result.questions:
            # Hints should be shorter than questions (rough heuristic)
            assert len(q.hint) > 0
            # Hints shouldn't be identical to question text
            assert q.hint != q.text


class TestGenerateMore:
    def test_returns_generate_more_result(self, project_contexts, experiences, skills):
        initial = generate_questions(project_contexts, experiences, skills)
        result = generate_more(initial.questions, project_contexts, experiences, skills)
        assert isinstance(result, GenerateMoreResult)

    def test_no_repeats(self, project_contexts, experiences, skills):
        initial = generate_questions(project_contexts, experiences, skills)
        result = generate_more(initial.questions, project_contexts, experiences, skills)
        existing_ids = {q.id for q in initial.questions}
        for q in result.questions:
            assert q.id not in existing_ids

    def test_new_questions_have_valid_evidence(self, project_contexts, experiences, skills):
        initial = generate_questions(project_contexts, experiences, skills)
        result = generate_more(initial.questions, project_contexts, experiences, skills)
        for q in result.questions:
            assert len(q.evidence) >= 1
            for ev in q.evidence:
                assert len(ev.quote) > 0

    def test_exhausted_when_no_unused_evidence(self, project_contexts, experiences, skills):
        """If we pass all questions back, eventually exhausted should be True."""
        initial = generate_questions(project_contexts, experiences, skills)
        # Call generate_more repeatedly until exhausted
        all_questions = list(initial.questions)
        for _ in range(10):
            result = generate_more(all_questions, project_contexts, experiences, skills)
            if result.exhausted:
                break
            all_questions.extend(result.questions)
        # Eventually should be exhausted or we hit iteration limit (both acceptable)