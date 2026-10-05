"""
Data models matching the contracts in contracts/schemas/.

These Pydantic models enforce the same constraints as the JSON Schemas,
with additional runtime validation for evidence checking.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field, field_validator


class EvidenceKind(str, Enum):
    CHUNK = "chunk"
    EXPERIENCE = "experience"


class QuestionType(str, Enum):
    PROJECT = "project"
    EXPERIENCE = "experience"


class Difficulty(str, Enum):
    EASY = "easy"
    MEDIUM = "medium"
    HARD = "hard"


class InputQuality(str, Enum):
    OK = "ok"
    THIN = "thin"
    MISSING = "missing"


class ChunkSource(str, Enum):
    RESUME = "resume"
    README = "readme"
    STUDENT_PROVIDED = "student_provided"


class QuestionSetStatus(str, Enum):
    PROCESSING = "processing"
    READY = "ready"
    NEEDS_INPUT = "needs_input"
    FAILED = "failed"


# --- Core data types ---


class EvidenceChunk(BaseModel):
    chunk_id: str
    project_id: str
    source: ChunkSource
    text: str


class ProjectContext(BaseModel):
    project_id: str
    project_name: str
    input_quality: InputQuality
    needs_student_input: bool
    evidence_chunks: list[EvidenceChunk]


class ResumeIngestion(BaseModel):
    resume_upload_id: str
    skills: list[str]
    projects: list[dict]
    warnings: list[str] = Field(default_factory=list)


class ExperienceEntry(BaseModel):
    id: str
    role: str
    company: str
    round: str
    topic: str
    skills: list[str]
    question_text: str
    year: int = Field(ge=2000, le=2100)
    source_url: str


class Evidence(BaseModel):
    kind: EvidenceKind
    ref_id: str
    quote: str


class Question(BaseModel):
    id: str
    text: str
    hint: str
    type: QuestionType
    difficulty: Difficulty
    project_id: Optional[str] = None
    evidence: list[Evidence] = Field(min_length=1)

    @field_validator("evidence")
    @classmethod
    def experience_questions_have_two_evidence(cls, v: list[Evidence], info) -> list[Evidence]:
        # We can't reliably check `type` during validation since it may not
        # be set yet, so this is enforced at generation time instead.
        return v


class GenerationResult(BaseModel):
    questions: list[Question]
    warnings: list[str] = Field(default_factory=list)
    insufficient_input: bool = False
    reason: Optional[str] = None


class GenerateMoreResult(BaseModel):
    questions: list[Question]
    exhausted: bool


class QuestionSet(BaseModel):
    id: str
    resume_upload_id: str
    questions: list[Question]
    status: QuestionSetStatus
    created_at: datetime


class PerQuestionFeedback(BaseModel):
    question_id: str
    was_asked: bool
    hint_helped: bool


class Feedback(BaseModel):
    resume_upload_id: str
    overall_score: int = Field(ge=1, le=5)
    comment: Optional[str] = None
    per_question: list[PerQuestionFeedback]