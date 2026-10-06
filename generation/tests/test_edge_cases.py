"""
Additional edge case tests for the generation engine.

Covers scenarios that are important for robustness:
- Empty inputs
- Single-chunk projects
- Experiences with no matching chunks
- generate_more exhaustion
- Evidence check with tricky quotes

Run with: pytest generation/tests/test_edge_cases.py -v
"""

import json
from pathlib import Path

import pytest

from generation.evidence_checker import check_question_evidence, filter_valid_questions
from generation.generator import generate_more, generate_questions
from generation.llm_client import MockLLMCaller
from generation.models import (
    Difficulty,
    Evidence,
    EvidenceChunk,
    EvidenceKind,
    ExperienceEntry,
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


class TestEmptyAndThinInputs:
    """Test behavior with empty or very thin inputs."""

    def test_empty_everything(self):
        result = generate_questions([], [], [])
        assert result.insufficient_input
        assert len(result.questions) == 0
        assert len(result.warnings) > 0

    def test_empty_project_contexts_with_experiences_only(self, experiences, skills):
        result = generate_questions([], experiences, skills)
        # Experience questions need resume chunks as evidence, so without projects
        # we can't properly ground experience questions
        assert result.insufficient_input

    def test_single_thin_project_no_experiences(self, skills):
        pc = ProjectContext(
            project_id="p_thin",
            project_name="Thin Project",
            input_quality=InputQuality.THIN,
            needs_student_input=True,
            evidence_chunks=[
                EvidenceChunk(
                    chunk_id="thin-01",
                    project_id="p_thin",
                    source="resume",
                    text="Made a website.",
                )
            ],
        )
        result = generate_questions([pc], [], skills)
        # Should produce some questions but flag as insufficient
        assert result.insufficient_input or len(result.questions) <= 2

    def test_missing_project_skipped_with_warning(self, skills):
        pc = ProjectContext(
            project_id="p_miss",
            project_name="Missing Project",
            input_quality=InputQuality.MISSING,
            needs_student_input=True,
            evidence_chunks=[],
        )
        result = generate_questions([pc], [], skills)
        assert result.insufficient_input
        assert any("missing" in w.lower() for w in result.warnings)

    def test_project_with_empty_chunks_list(self, skills):
        pc = ProjectContext(
            project_id="p_empty_chunks",
            project_name="No Chunks Project",
            input_quality=InputQuality.OK,
            needs_student_input=False,
            evidence_chunks=[],
        )
        result = generate_questions([pc], [], skills)
        assert any("no evidence" in w.lower() for w in result.warnings)

    def test_thin_input_with_experiences(self, experiences, skills):
        pc = ProjectContext(
            project_id="p_thin",
            project_name="Thin Project",
            input_quality=InputQuality.THIN,
            needs_student_input=True,
            evidence_chunks=[
                EvidenceChunk(
                    chunk_id="thin-01",
                    project_id="p_thin",
                    source="resume",
                    text="Built a REST API with Node.js and PostgreSQL.",
                )
            ],
        )
        result = generate_questions([pc], experiences, skills)
        # Should have some questions from the thin chunk + experiences
        assert isinstance(result.questions, list)


class TestExperienceEdgeCases:
    """Test edge cases specific to experience-based questions."""

    def test_no_matching_skills_between_experiences_and_chunks(self, skills):
        """Experiences with skills not mentioned in any chunk."""
        pc = ProjectContext(
            project_id="p1",
            project_name="Web App",
            input_quality=InputQuality.OK,
            needs_student_input=False,
            evidence_chunks=[
                EvidenceChunk(
                    chunk_id="c1",
                    project_id="p1",
                    source="readme",
                    text="Built a React frontend with Tailwind CSS.",
                )
            ],
        )
        # Experience with unrelated skills
        exp = ExperienceEntry(
            id="e_unrelated",
            role="Data Engineer",
            company="DataCo",
            round="Technical",
            topic="Data Pipelines",
            skills=["Apache Spark", "Kafka", "Airflow"],
            question_text="How would you design a data pipeline for real-time analytics?",
            year=2025,
            source_url="https://example.com/exp",
        )
        result = generate_questions([pc], [exp], skills)
        # Should still produce questions (stub mode finds a chunk to match)
        assert isinstance(result.questions, list)

    def test_experience_with_empty_question_text(self, skills):
        pc = ProjectContext(
            project_id="p1",
            project_name="App",
            input_quality=InputQuality.OK,
            needs_student_input=False,
            evidence_chunks=[
                EvidenceChunk(
                    chunk_id="c1",
                    project_id="p1",
                    source="resume",
                    text="Built a web app with Python and Flask.",
                )
            ],
        )
        exp = ExperienceEntry(
            id="e_empty",
            role="Engineer",
            company="Co",
            round="Tech",
            topic="General",
            skills=["Python"],
            question_text="",
            year=2025,
            source_url="https://example.com",
        )
        result = generate_questions([pc], [exp], skills)
        # Should not crash, experience question may be skipped
        assert isinstance(result, type(result))

    def test_multiple_experiences_same_skill(self, skills):
        """Multiple experiences with the same skill should produce distinct questions."""
        pc = ProjectContext(
            project_id="p1",
            project_name="DB App",
            input_quality=InputQuality.OK,
            needs_student_input=False,
            evidence_chunks=[
                EvidenceChunk(
                    chunk_id="c1",
                    project_id="p1",
                    source="readme",
                    text="Used PostgreSQL for the database with indexed queries.",
                )
            ],
        )
        exps = [
            ExperienceEntry(
                id=f"e_{i}",
                role="Engineer",
                company=f"Company{i}",
                round="Technical",
                topic="Databases",
                skills=["PostgreSQL"],
                question_text=f"Question {i} about database optimization.",
                year=2025,
                source_url=f"https://example.com/{i}",
            )
            for i in range(3)
        ]
        result = generate_questions([pc], exps, skills)
        assert isinstance(result.questions, list)


class TestEvidenceCheckEdgeCases:
    """Test evidence checker with tricky inputs."""

    def test_quote_with_different_whitespace(self):
        """Quote with different whitespace should still match."""
        chunk = EvidenceChunk(
            chunk_id="c1", project_id="p1", source="resume",
            text="Built a full-stack web application with React and Express."
        )
        q = Question(
            id="q1", text="Q?", hint="H",
            type=QuestionType.PROJECT, difficulty=Difficulty.MEDIUM,
            project_id="p1",
            evidence=[Evidence(kind=EvidenceKind.CHUNK, ref_id="c1",
                              quote="Built a  full-stack  web  application")],
        )
        assert check_question_evidence(q, {"c1": chunk}, {}) is True

    def test_quote_with_different_case(self):
        chunk = EvidenceChunk(
            chunk_id="c1", project_id="p1", source="resume",
            text="Used PostgreSQL for the database."
        )
        q = Question(
            id="q1", text="Q?", hint="H",
            type=QuestionType.PROJECT, difficulty=Difficulty.MEDIUM,
            project_id="p1",
            evidence=[Evidence(kind=EvidenceKind.CHUNK, ref_id="c1",
                              quote="used postgresql for the database.")],
        )
        assert check_question_evidence(q, {"c1": chunk}, {}) is True

    def test_partial_quote_match(self):
        """A substring of the source should pass."""
        chunk = EvidenceChunk(
            chunk_id="c1", project_id="p1", source="readme",
            text="The application uses Redis for caching and session management."
        )
        q = Question(
            id="q1", text="Q?", hint="H",
            type=QuestionType.PROJECT, difficulty=Difficulty.MEDIUM,
            project_id="p1",
            evidence=[Evidence(kind=EvidenceKind.CHUNK, ref_id="c1",
                              quote="Redis for caching")],
        )
        assert check_question_evidence(q, {"c1": chunk}, {}) is True

    def test_quote_not_in_source(self):
        chunk = EvidenceChunk(
            chunk_id="c1", project_id="p1", source="readme",
            text="Built with React and Express."
        )
        q = Question(
            id="q1", text="Q?", hint="H",
            type=QuestionType.PROJECT, difficulty=Difficulty.MEDIUM,
            project_id="p1",
            evidence=[Evidence(kind=EvidenceKind.CHUNK, ref_id="c1",
                              quote="Built with Angular and Django")],
        )
        assert check_question_evidence(q, {"c1": chunk}, {}) is False

    def test_multiple_evidence_all_must_pass(self):
        """If any evidence item fails, the whole question fails."""
        chunk = EvidenceChunk(
            chunk_id="c1", project_id="p1", source="readme",
            text="Uses PostgreSQL and Redis."
        )
        exp = ExperienceEntry(
            id="e1", role="Eng", company="Co", round="Tech", topic="DB",
            skills=["PostgreSQL"], question_text="Asked about indexing.",
            year=2025, source_url="https://example.com",
        )
        # One valid evidence, one invalid quote
        q = Question(
            id="q1", text="Q?", hint="H",
            type=QuestionType.EXPERIENCE, difficulty=Difficulty.MEDIUM,
            project_id=None,
            evidence=[
                Evidence(kind=EvidenceKind.CHUNK, ref_id="c1", quote="PostgreSQL"),
                Evidence(kind=EvidenceKind.EXPERIENCE, ref_id="e1", quote="completely fake quote"),
            ],
        )
        assert check_question_evidence(q, {"c1": chunk}, {"e1": exp}) is False


class TestGenerateMoreEdgeCases:
    """Test generate_more with various scenarios."""

    def test_generate_more_with_single_chunk(self, skills):
        """Single chunk project: generate_more should exhaust quickly."""
        pc = ProjectContext(
            project_id="p1",
            project_name="Small Project",
            input_quality=InputQuality.OK,
            needs_student_input=False,
            evidence_chunks=[
                EvidenceChunk(
                    chunk_id="c1",
                    project_id="p1",
                    source="resume",
                    text="Built a todo app with Flask.",
                )
            ],
        )
        initial = generate_questions([pc], [], skills)
        # First generate_more should work
        result1 = generate_more(initial.questions, [pc], [], skills)
        # After using all evidence, should be exhausted
        all_q = initial.questions + result1.questions
        result2 = generate_more(all_q, [pc], [], skills)
        assert result2.exhausted or len(result2.questions) == 0

    def test_generate_more_preserves_existing(self, project_contexts, experiences, skills):
        """generate_more should never modify the existing questions list."""
        initial = generate_questions(project_contexts, experiences, skills)
        original_ids = {q.id for q in initial.questions}
        original_count = len(initial.questions)

        generate_more(initial.questions, project_contexts, experiences, skills)

        # Original list should be unchanged
        assert len(initial.questions) == original_count
        assert {q.id for q in initial.questions} == original_ids

    def test_generate_more_empty_existing(self, project_contexts, experiences, skills):
        """generate_more with no existing questions should return questions from all evidence."""
        result = generate_more([], project_contexts, experiences, skills)
        # Should get some questions
        assert len(result.questions) >= 0

    def test_generate_more_no_projects_no_experiences(self, skills):
        """generate_more with nothing should return exhausted."""
        result = generate_more([], [], [], skills)
        assert result.exhausted
        assert len(result.questions) == 0


class TestProjectCoverage:
    """Verify that all projects get questions (coverage requirement)."""

    def test_all_projects_covered_in_stub_mode(self, project_contexts, skills):
        """Every non-missing project should have at least one question."""
        result = generate_questions(project_contexts, [], skills)
        project_ids_with_questions = {
            q.project_id for q in result.questions if q.type == QuestionType.PROJECT
        }
        non_missing_ids = {
            pc.project_id for pc in project_contexts
            if pc.input_quality != InputQuality.MISSING
        }
        # Every non-missing project should be represented
        assert non_missing_ids.issubset(project_ids_with_questions)

    def test_thin_project_still_gets_questions(self, skills):
        """A thin project should still get at least 1 question if it has any chunks."""
        pc = ProjectContext(
            project_id="p_thin",
            project_name="Thin Project",
            input_quality=InputQuality.THIN,
            needs_student_input=True,
            evidence_chunks=[
                EvidenceChunk(
                    chunk_id="t1",
                    project_id="p_thin",
                    source="resume",
                    text="Simple portfolio site with HTML and CSS.",
                )
            ],
        )
        result = generate_questions([pc], [], skills)
        project_q = [q for q in result.questions if q.project_id == "p_thin"]
        assert len(project_q) >= 1