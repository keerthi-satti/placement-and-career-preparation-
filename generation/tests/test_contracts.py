"""
Contract validation tests: verify that generated questions match the JSON schemas
defined in contracts/schemas/.

Run with: pytest generation/tests/test_contracts.py -v
"""

import json
from pathlib import Path

import jsonschema
import pytest

from generation.generator import generate_more, generate_questions
from generation.llm_client import MockLLMCaller
from generation.models import (
    EvidenceChunk,
    ExperienceEntry,
    InputQuality,
    ProjectContext,
    QuestionType,
)

FIXTURES = Path(__file__).parent / "fixtures"
SCHEMAS = Path(__file__).parent.parent.parent / "contracts" / "schemas"


def _load_schema(name: str) -> dict:
    return json.loads((SCHEMAS / name).read_text())


def _load_resolver():
    """Create a resolver that can resolve $ref within the schemas directory."""
    store = {}
    for f in SCHEMAS.glob("*.schema.json"):
        schema = json.loads(f.read_text())
        uri = f"file://{f.resolve()}"
        store[uri] = schema
    # Set the base URI to the schemas directory so relative $refs resolve
    base_uri = f"file://{SCHEMAS.resolve()}/"
    return jsonschema.RefResolver(
        base_uri=base_uri,
        referrer=None,
        store=store,
    )


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
def resolver():
    return _load_resolver()


@pytest.fixture
def question_schema():
    return _load_schema("question.schema.json")


@pytest.fixture
def generation_result_schema():
    return _load_schema("generation_result.schema.json")


@pytest.fixture
def generate_more_result_schema():
    return _load_schema("generate_more_result.schema.json")


def _question_to_dict(q):
    """Convert a Question model to a dict matching the JSON schema."""
    return {
        "id": q.id,
        "text": q.text,
        "hint": q.hint,
        "type": q.type.value,
        "difficulty": q.difficulty.value,
        "project_id": q.project_id,
        "evidence": [
            {
                "kind": ev.kind.value,
                "ref_id": ev.ref_id,
                "quote": ev.quote,
            }
            for ev in q.evidence
        ],
    }


def _generation_result_to_dict(result):
    return {
        "questions": [_question_to_dict(q) for q in result.questions],
        "warnings": result.warnings,
        "insufficient_input": result.insufficient_input,
        "reason": result.reason,
    }


def _generate_more_result_to_dict(result):
    return {
        "questions": [_question_to_dict(q) for q in result.questions],
        "exhausted": result.exhausted,
    }


class TestQuestionContract:
    """Verify questions match the question.schema.json contract."""

    def test_stub_questions_match_schema(self, project_contexts, experiences, skills,
                                         question_schema, resolver):
        result = generate_questions(project_contexts, experiences, skills)
        for q in result.questions:
            data = _question_to_dict(q)
            jsonschema.validate(data, question_schema, resolver=resolver)

    def test_llm_questions_match_schema(self, project_contexts, experiences, skills,
                                         question_schema, resolver):
        caller = MockLLMCaller()
        result = generate_questions(project_contexts, experiences, skills, llm_caller=caller)
        for q in result.questions:
            data = _question_to_dict(q)
            jsonschema.validate(data, question_schema, resolver=resolver)

    def test_experience_questions_have_two_evidence_in_schema(self, project_contexts,
                                                               experiences, skills,
                                                               question_schema, resolver):
        caller = MockLLMCaller()
        result = generate_questions(project_contexts, experiences, skills, llm_caller=caller)
        for q in result.questions:
            if q.type == QuestionType.EXPERIENCE:
                assert len(q.evidence) == 2
                data = _question_to_dict(q)
                jsonschema.validate(data, question_schema, resolver=resolver)

    def test_project_questions_have_one_evidence_in_schema(self, project_contexts,
                                                            experiences, skills,
                                                            question_schema, resolver):
        result = generate_questions(project_contexts, experiences, skills)
        for q in result.questions:
            if q.type == QuestionType.PROJECT:
                assert len(q.evidence) >= 1
                data = _question_to_dict(q)
                jsonschema.validate(data, question_schema, resolver=resolver)


class TestGenerationResultContract:
    """Verify GenerationResult matches the generation_result.schema.json contract."""

    def test_stub_result_matches_schema(self, project_contexts, experiences, skills,
                                         generation_result_schema, resolver):
        result = generate_questions(project_contexts, experiences, skills)
        data = _generation_result_to_dict(result)
        jsonschema.validate(data, generation_result_schema, resolver=resolver)

    def test_llm_result_matches_schema(self, project_contexts, experiences, skills,
                                         generation_result_schema, resolver):
        caller = MockLLMCaller()
        result = generate_questions(project_contexts, experiences, skills, llm_caller=caller)
        data = _generation_result_to_dict(result)
        jsonschema.validate(data, generation_result_schema, resolver=resolver)

    def test_insufficient_result_matches_schema(self, skills, generation_result_schema, resolver):
        result = generate_questions([], [], skills)
        data = _generation_result_to_dict(result)
        jsonschema.validate(data, generation_result_schema, resolver=resolver)


class TestGenerateMoreResultContract:
    """Verify GenerateMoreResult matches the generate_more_result.schema.json contract."""

    def test_stub_generate_more_matches_schema(self, project_contexts, experiences, skills,
                                                generate_more_result_schema, resolver):
        initial = generate_questions(project_contexts, experiences, skills)
        result = generate_more(initial.questions, project_contexts, experiences, skills)
        data = _generate_more_result_to_dict(result)
        jsonschema.validate(data, generate_more_result_schema, resolver=resolver)

    def test_llm_generate_more_matches_schema(self, project_contexts, experiences, skills,
                                               generate_more_result_schema, resolver):
        caller = MockLLMCaller()
        initial = generate_questions(project_contexts, experiences, skills, llm_caller=caller)
        result = generate_more(initial.questions, project_contexts, experiences, skills, llm_caller=caller)
        data = _generate_more_result_to_dict(result)
        jsonschema.validate(data, generate_more_result_schema, resolver=resolver)