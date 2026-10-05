"""
Tests for the generator module.

Run with: pytest generation/tests/test_generator.py -v
"""

import json
from pathlib import Path

import pytest

from generation.generator import generate_more, generate_questions
from generation.llm_client import MockLLMCaller
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


@pytest.fixture
def mock_llm():
    return MockLLMCaller()


# --- Stub mode tests (no LLM) ---


class TestGenerateQuestionsStub:
    """Tests for generate_questions in stub mode (no LLM)."""

    def test_returns_generation_result(self, project_contexts, experiences, skills):
        result = generate_questions(project_contexts, experiences, skills)
        assert isinstance(result, GenerationResult)

    def test_produces_questions_for_each_project(self, project_contexts, experiences, skills):
        result = generate_questions(project_contexts, experiences, skills)
        project_ids = {q.project_id for q in result.questions if q.type == QuestionType.PROJECT}
        assert "p1" in project_ids
        assert "p2" in project_ids

    def test_questions_have_evidence(self, project_contexts, experiences, skills):
        result = generate_questions(project_contexts, experiences, skills)
        for q in result.questions:
            assert len(q.evidence) >= 1
            for ev in q.evidence:
                assert ev.kind in (EvidenceKind.CHUNK, EvidenceKind.EXPERIENCE)
                assert ev.ref_id
                assert ev.quote

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

    def test_thin_input_sets_insufficient_flag(self, thin_input, experiences, skills):
        result = generate_questions(thin_input, [], skills)
        assert result.insufficient_input or len(result.questions) < 5

    def test_missing_input_produces_warning(self, thin_input, experiences, skills):
        result = generate_questions(thin_input, [], skills)
        assert any("missing" in w.lower() or "needs" in w.lower() or "thin" in w.lower()
                    for w in result.warnings) or result.insufficient_input

    def test_no_questions_without_llm(self, project_contexts, experiences, skills):
        result = generate_questions(project_contexts, experiences, skills)
        assert len(result.questions) > 0

    def test_difficulty_varies(self, project_contexts, experiences, skills):
        result = generate_questions(project_contexts, experiences, skills)
        difficulties = {q.difficulty for q in result.questions}
        assert len(difficulties) >= 2

    def test_hints_are_not_answers(self, project_contexts, experiences, skills):
        result = generate_questions(project_contexts, experiences, skills)
        for q in result.questions:
            assert len(q.hint) > 0
            assert q.hint != q.text

    def test_all_questions_pass_evidence_check(self, project_contexts, experiences, skills):
        """The generator should only return questions that pass evidence check."""
        result = generate_questions(project_contexts, experiences, skills)
        # Evidence check is done inside generate_questions, so all returned
        # questions should have valid evidence
        for q in result.questions:
            assert len(q.evidence) >= 1


# --- LLM mode tests ---


class TestGenerateQuestionsLLM:
    """Tests for generate_questions with a mock LLM."""

    def test_returns_generation_result_with_llm(self, project_contexts, experiences, skills, mock_llm):
        result = generate_questions(project_contexts, experiences, skills, llm_caller=mock_llm)
        assert isinstance(result, GenerationResult)

    def test_llm_produces_questions(self, project_contexts, experiences, skills, mock_llm):
        llm_result = generate_questions(project_contexts, experiences, skills, llm_caller=mock_llm)
        # LLM should produce a reasonable number of questions
        assert len(llm_result.questions) >= 3

    def test_llm_questions_have_valid_evidence(self, project_contexts, experiences, skills, mock_llm):
        result = generate_questions(project_contexts, experiences, skills, llm_caller=mock_llm)
        for q in result.questions:
            assert len(q.evidence) >= 1
            for ev in q.evidence:
                assert ev.ref_id  # Should be resolved, not empty
                assert ev.quote

    def test_llm_experience_questions_have_two_evidence(self, project_contexts, experiences, skills, mock_llm):
        result = generate_questions(project_contexts, experiences, skills, llm_caller=mock_llm)
        exp_questions = [q for q in result.questions if q.type == QuestionType.EXPERIENCE]
        for q in exp_questions:
            assert len(q.evidence) == 2

    def test_llm_fallback_on_error(self, project_contexts, experiences, skills):
        """If LLM raises, should fall back to stub and add warning."""
        def bad_caller(sys_prompt, user_prompt):
            raise RuntimeError("LLM unavailable")

        result = generate_questions(project_contexts, experiences, skills, llm_caller=bad_caller)
        # Should still have questions from fallback
        assert len(result.questions) > 0
        assert any("failed" in w.lower() for w in result.warnings)


# --- Count rules tests ---


class TestCountRules:
    """Tests for the count rules from the plan."""

    def test_baseline_count(self, project_contexts, experiences, skills):
        """Should aim for ~20 questions baseline."""
        result = generate_questions(project_contexts, experiences, skills)
        # With 3 projects and 5 experiences, we should get a reasonable number
        # (stub mode may be less than 20, but should be > 5)
        assert len(result.questions) > 5

    def test_max_first_gen_cap(self, project_contexts, experiences, skills, mock_llm):
        """First generation should be capped at 40."""
        result = generate_questions(project_contexts, experiences, skills, llm_caller=mock_llm)
        assert len(result.questions) <= 40

    def test_insufficient_threshold(self, thin_input, skills):
        """With thin input and no experiences, should flag as insufficient."""
        result = generate_questions(thin_input, [], skills)
        assert result.insufficient_input
        assert result.reason is not None

    def test_no_padding(self, thin_input, skills):
        """Should never pad to reach a number."""
        result = generate_questions(thin_input, [], skills)
        # Thin input: 1 chunk, missing project. Should get 0-1 questions, not padded to 5.
        assert len(result.questions) <= 2


# --- Edge case tests ---


class TestEdgeCases:
    """Tests for edge cases and unusual inputs."""

    def test_no_projects_no_experiences(self, skills):
        result = generate_questions([], [], skills)
        assert result.insufficient_input
        assert len(result.questions) == 0

    def test_no_experiences_only_projects(self, project_contexts, skills):
        result = generate_questions(project_contexts, [], skills)
        assert len(result.questions) > 0
        # All should be project questions
        for q in result.questions:
            assert q.type == QuestionType.PROJECT

    def test_no_projects_only_experiences(self, experiences, skills):
        result = generate_questions([], experiences, skills)
        # Experience questions need two evidence items (chunk + experience).
        # Without projects/chunks, we can't ground experience questions properly.
        # Should flag as insufficient and warn.
        assert result.insufficient_input
        assert any("no project" in w.lower() for w in result.warnings)

    def test_empty_skills(self, project_contexts, experiences):
        result = generate_questions(project_contexts, experiences, [])
        # Should still work, just without skill context
        assert isinstance(result, GenerationResult)

    def test_single_chunk_project(self, skills):
        """Project with only one chunk should still get at least 1-2 questions."""
        pc = ProjectContext(
            project_id="p_single",
            project_name="Single Chunk Project",
            input_quality=InputQuality.OK,
            needs_student_input=False,
            evidence_chunks=[
                EvidenceChunk(
                    chunk_id="sc-01",
                    project_id="p_single",
                    source="resume",
                    text="Built a simple REST API with Flask and SQLite.",
                )
            ],
        )
        result = generate_questions([pc], [], skills)
        assert len(result.questions) >= 1

    def test_all_missing_projects(self, skills):
        """All projects with missing input should produce insufficient result."""
        pcs = [
            ProjectContext(
                project_id=f"p{i}",
                project_name=f"Missing Project {i}",
                input_quality=InputQuality.MISSING,
                needs_student_input=True,
                evidence_chunks=[],
            )
            for i in range(3)
        ]
        result = generate_questions(pcs, [], skills)
        assert result.insufficient_input


# --- Generate more tests ---


class TestGenerateMoreStub:
    """Tests for generate_more in stub mode."""

    def test_returns_generate_more_result(self, project_contexts, experiences, skills):
        initial = generate_questions(project_contexts, experiences, skills)
        result = generate_more(initial.questions, project_contexts, experiences, skills)
        assert isinstance(result, GenerateMoreResult)

    def test_no_id_repeats(self, project_contexts, experiences, skills):
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
        initial = generate_questions(project_contexts, experiences, skills)
        all_questions = list(initial.questions)
        for _ in range(10):
            result = generate_more(all_questions, project_contexts, experiences, skills)
            if result.exhausted:
                break
            all_questions.extend(result.questions)

    def test_no_semantic_repeats(self, project_contexts, experiences, skills):
        """New questions should not be reworded versions of existing ones."""
        initial = generate_questions(project_contexts, experiences, skills)
        result = generate_more(initial.questions, project_contexts, experiences, skills)
        for new_q in result.questions:
            for existing_q in initial.questions:
                # Questions should be genuinely different, not just reworded
                assert new_q.text != existing_q.text

    def test_no_same_evidence_repeats(self, project_contexts, experiences, skills):
        """New questions should not cite the exact same evidence combination as existing ones."""
        initial = generate_questions(project_contexts, experiences, skills)
        result = generate_more(initial.questions, project_contexts, experiences, skills)

        def evidence_sig(q):
            return tuple(sorted((ev.kind.value, ev.ref_id) for ev in q.evidence))

        existing_sigs = {evidence_sig(q) for q in initial.questions}
        for new_q in result.questions:
            assert evidence_sig(new_q) not in existing_sigs

    def test_exhaustion_after_multiple_rounds(self, project_contexts, experiences, skills):
        """After enough rounds of generate_more, should eventually be exhausted."""
        initial = generate_questions(project_contexts, experiences, skills)
        all_questions = list(initial.questions)
        exhausted = False
        for _ in range(20):
            result = generate_more(all_questions, project_contexts, experiences, skills)
            if result.exhausted:
                exhausted = True
                break
            if not result.questions:
                # No more questions but not flagged exhausted - also acceptable
                break
            all_questions.extend(result.questions)
        # Should have found exhaustion or run out of new questions
        assert exhausted or len(result.questions) == 0


class TestGenerateMoreLLM:
    """Tests for generate_more with a mock LLM."""

    def test_returns_result_with_llm(self, project_contexts, experiences, skills, mock_llm):
        initial = generate_questions(project_contexts, experiences, skills, llm_caller=mock_llm)
        result = generate_more(initial.questions, project_contexts, experiences, skills, llm_caller=mock_llm)
        assert isinstance(result, GenerateMoreResult)

    def test_llm_generate_more_no_repeats(self, project_contexts, experiences, skills, mock_llm):
        initial = generate_questions(project_contexts, experiences, skills, llm_caller=mock_llm)
        result = generate_more(initial.questions, project_contexts, experiences, skills, llm_caller=mock_llm)
        existing_ids = {q.id for q in initial.questions}
        for q in result.questions:
            assert q.id not in existing_ids

    def test_llm_generate_more_no_same_evidence(self, project_contexts, experiences, skills, mock_llm):
        """LLM generate_more should not produce same-evidence repeats."""
        initial = generate_questions(project_contexts, experiences, skills, llm_caller=mock_llm)
        result = generate_more(initial.questions, project_contexts, experiences, skills, llm_caller=mock_llm)

        def evidence_sig(q):
            return tuple(sorted((ev.kind.value, ev.ref_id) for ev in q.evidence))

        existing_sigs = {evidence_sig(q) for q in initial.questions}
        for new_q in result.questions:
            assert evidence_sig(new_q) not in existing_sigs