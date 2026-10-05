"""
Core question generation engine.

Orchestrates the LLM calls, evidence checking, and count rules.
"""

from __future__ import annotations

import json
import uuid
from typing import Optional

from .evidence_checker import filter_valid_questions
from .models import (
    Difficulty,
    Evidence,
    EvidenceChunk,
    EvidenceKind,
    ExperienceEntry,
    GenerateMoreResult,
    GenerationResult,
    Question,
    QuestionType,
)
from .prompts import EXPERIENCE_QUESTION_PROMPT, PROJECT_QUESTION_PROMPT, SYSTEM_PROMPT


# --- Count rules (from the plan) ---
BASELINE_COUNT = 20
MIN_PER_PROJECT = 2
MAX_FIRST_GEN = 40
INSUFFICIENT_THRESHOLD = 5


def _build_chunk_map(chunks: list[EvidenceChunk]) -> dict[str, EvidenceChunk]:
    return {c.chunk_id: c for c in chunks}


def _build_experience_map(entries: list[ExperienceEntry]) -> dict[str, ExperienceEntry]:
    return {e.id: e for e in entries}


def _format_evidence_text(chunks: list[EvidenceChunk]) -> str:
    parts = []
    for c in chunks:
        parts.append(f"[{c.chunk_id}] ({c.source.value}) {c.text}")
    return "\n\n".join(parts)


def _format_experiences_text(entries: list[ExperienceEntry]) -> str:
    parts = []
    for e in entries:
        parts.append(
            f"[{e.id}] {e.role} at {e.company} ({e.year}) - {e.round}\n"
            f"  Topic: {e.topic} | Skills: {', '.join(e.skills)}\n"
            f"  {e.question_text}"
        )
    return "\n\n".join(parts)


def _generate_id() -> str:
    return f"q_{uuid.uuid4().hex[:8]}"


def generate_questions(
    project_contexts: list[ProjectContext],
    experiences: list[ExperienceEntry],
    resume_skills: list[str],
    llm_caller: Optional[callable] = None,
) -> GenerationResult:
    """
    Generate interview questions from project contexts and experience entries.

    Args:
        project_contexts: Parsed project data with evidence chunks.
        experiences: Matched interview experience entries.
        resume_skills: Skills extracted from the resume.
        llm_caller: Function that takes (system_prompt, user_prompt) and returns
                    a string response. If None, returns empty questions (stub mode).

    Returns:
        GenerationResult with questions, warnings, and insufficient_input flag.
    """
    warnings: list[str] = []
    questions: list[Question] = []

    # Collect all chunks for evidence checking
    all_chunks: list[EvidenceChunk] = []
    for pc in project_contexts:
        all_chunks.extend(pc.evidence_chunks)
    chunk_map = _build_chunk_map(all_chunks)
    exp_map = _build_experience_map(experiences)

    # --- Project questions ---
    for pc in project_contexts:
        if pc.input_quality.value == "missing":
            warnings.append(f"Project '{pc.project_name}': no usable input, skipping.")
            continue

        if pc.needs_student_input:
            warnings.append(
                f"Project '{pc.project_name}': needs more details from student for better questions."
            )

        if not pc.evidence_chunks:
            warnings.append(f"Project '{pc.project_name}': no evidence chunks available.")
            continue

        if llm_caller is not None:
            prompt = PROJECT_QUESTION_PROMPT.format(
                project_name=pc.project_name,
                evidence_text=_format_evidence_text(pc.evidence_chunks),
                skills=", ".join(resume_skills),
            )
            response = llm_caller(SYSTEM_PROMPT, prompt)
            parsed = _parse_project_questions(response, pc.project_id)
            questions.extend(parsed)
        else:
            # Stub mode: produce placeholder questions for testing
            questions.extend(_stub_project_questions(pc, resume_skills))

    # --- Experience-based questions ---
    if experiences and llm_caller is not None:
        prompt = EXPERIENCE_QUESTION_PROMPT.format(
            skills=", ".join(resume_skills),
            resume_chunks=_format_evidence_text(all_chunks),
            experiences_text=_format_experiences_text(experiences),
        )
        response = llm_caller(SYSTEM_PROMPT, prompt)
        parsed = _parse_experience_questions(response)
        questions.extend(parsed)
    elif experiences:
        questions.extend(_stub_experience_questions(experiences, all_chunks))

    # --- Evidence check ---
    valid_questions = filter_valid_questions(questions, chunk_map, exp_map)
    dropped = len(questions) - len(valid_questions)
    if dropped > 0:
        warnings.append(f"Dropped {dropped} questions that failed evidence check.")

    # --- Count rules ---
    if len(valid_questions) <= INSUFFICIENT_THRESHOLD:
        return GenerationResult(
            questions=valid_questions,
            warnings=warnings,
            insufficient_input=True,
            reason=f"Only {len(valid_questions)} valid questions could be grounded in evidence. "
                   "Provide more project details or a richer resume for better results.",
        )

    return GenerationResult(
        questions=valid_questions[:MAX_FIRST_GEN],
        warnings=warnings,
        insufficient_input=False,
        reason=None,
    )


def generate_more(
    existing_questions: list[Question],
    project_contexts: list[ProjectContext],
    experiences: list[ExperienceEntry],
    resume_skills: list[str],
    llm_caller: Optional[callable] = None,
) -> GenerateMoreResult:
    """
    Generate additional questions that don't repeat existing ones.

    Uses unused evidence first. Returns exhausted=True when no more
    grounded questions can be produced.
    """
    existing_ids = {q.id for q in existing_questions}
    existing_texts_norm = {_normalize(q.text) for q in existing_questions}

    # Find evidence not yet used in existing questions
    used_chunk_ids = set()
    used_exp_ids = set()
    for q in existing_questions:
        for ev in q.evidence:
            if ev.kind == EvidenceKind.CHUNK:
                used_chunk_ids.add(ev.ref_id)
            elif ev.kind == EvidenceKind.EXPERIENCE:
                used_exp_ids.add(ev.ref_id)

    all_chunks: list[EvidenceChunk] = []
    for pc in project_contexts:
        all_chunks.extend(pc.evidence_chunks)

    unused_chunks = [c for c in all_chunks if c.chunk_id not in used_chunk_ids]
    unused_experiences = [e for e in experiences if e.id not in used_exp_ids]

    if not unused_chunks and not unused_experiences:
        return GenerateMoreResult(questions=[], exhausted=True)

    # If we have an LLM caller, use it
    if llm_caller is not None:
        new_questions: list[Question] = []
        # TODO: call LLM with unused evidence and existing questions for dedup
        # For now, stub mode
        pass

    # Stub mode: try to produce questions from unused evidence
    new_questions = []
    chunk_map = _build_chunk_map(all_chunks)
    exp_map = _build_experience_map(experiences)

    # Simple stub: one question per unused chunk
    for chunk in unused_chunks[:5]:
        q = Question(
            id=_generate_id(),
            text=f"Can you explain the part of your project described as: '{chunk.text[:60]}...'?",
            hint="Walk through the technical details and your decision-making process.",
            type=QuestionType.PROJECT,
            difficulty=Difficulty.MEDIUM,
            project_id=chunk.project_id,
            evidence=[Evidence(kind=EvidenceKind.CHUNK, ref_id=chunk.chunk_id, quote=chunk.text[:100])],
        )
        if _normalize(q.text) not in existing_texts_norm:
            new_questions.append(q)

    # Deduplicate against existing
    final = [q for q in new_questions if q.id not in existing_ids]
    valid = filter_valid_questions(final, chunk_map, exp_map)

    exhausted = len(unused_chunks) <= 5 and len(unused_experiences) == 0
    return GenerateMoreResult(questions=valid, exhausted=exhausted)


def _normalize(text: str) -> str:
    import re
    return re.sub(r"\s+", " ", text.lower().strip())


def _parse_project_questions(response: str, project_id: str) -> list[Question]:
    """Parse LLM response into Question objects for a project."""
    try:
        data = json.loads(response)
    except json.JSONDecodeError:
        return []

    questions = []
    for item in data:
        evidence = [
            Evidence(kind=EvidenceKind.CHUNK, ref_id="", quote=q)
            for q in item.get("evidence_quotes", [])
        ]
        if not evidence:
            continue
        questions.append(
            Question(
                id=_generate_id(),
                text=item["text"],
                hint=item["hint"],
                type=QuestionType.PROJECT,
                difficulty=Difficulty(item.get("difficulty", "medium")),
                project_id=project_id,
                evidence=evidence,
            )
        )
    return questions


def _parse_experience_questions(response: str) -> list[Question]:
    """Parse LLM response into experience-based Question objects."""
    try:
        data = json.loads(response)
    except json.JSONDecodeError:
        return []

    questions = []
    for item in data:
        evidence = []
        if item.get("resume_quote"):
            evidence.append(
                Evidence(kind=EvidenceKind.CHUNK, ref_id="", quote=item["resume_quote"])
            )
        if item.get("experience_id") and item.get("experience_quote"):
            evidence.append(
                Evidence(
                    kind=EvidenceKind.EXPERIENCE,
                    ref_id=item["experience_id"],
                    quote=item["experience_quote"],
                )
            )
        if len(evidence) < 2:
            continue
        questions.append(
            Question(
                id=_generate_id(),
                text=item["text"],
                hint=item["hint"],
                type=QuestionType.EXPERIENCE,
                difficulty=Difficulty(item.get("difficulty", "medium")),
                project_id=None,
                evidence=evidence,
            )
        )
    return questions


def _stub_project_questions(pc: ProjectContext, skills: list[str]) -> list[Question]:
    """Generate stub questions for testing without an LLM."""
    questions = []
    for i, chunk in enumerate(pc.evidence_chunks[:3]):
        diff = [Difficulty.EASY, Difficulty.MEDIUM, Difficulty.HARD][i % 3]
        questions.append(
            Question(
                id=_generate_id(),
                text=f"Regarding your {pc.project_name} project: {chunk.text[:80]}... Can you explain your approach?",
                hint=f"Discuss the technical choices and trade-offs related to {chunk.source.value} details.",
                type=QuestionType.PROJECT,
                difficulty=diff,
                project_id=pc.project_id,
                evidence=[Evidence(kind=EvidenceKind.CHUNK, ref_id=chunk.chunk_id, quote=chunk.text[:100])],
            )
        )
    return questions


def _stub_experience_questions(
    experiences: list[ExperienceEntry], chunks: list[EvidenceChunk]
) -> list[Question]:
    """Generate stub experience-based questions for testing."""
    questions = []
    for exp in experiences[:5]:
        # Find a matching chunk by skills
        matching_chunk = None
        for chunk in chunks:
            if any(skill.lower() in chunk.text.lower() for skill in exp.skills):
                matching_chunk = chunk
                break

        if matching_chunk is None and chunks:
            matching_chunk = chunks[0]

        if matching_chunk is None:
            continue

        questions.append(
            Question(
                id=_generate_id(),
                text=f"Based on interview experiences at {exp.company}: {exp.question_text[:80]}... How would you approach this given your background?",
                hint=f"Relate to your experience with {', '.join(exp.skills)}.",
                type=QuestionType.EXPERIENCE,
                difficulty=Difficulty.HARD,
                project_id=None,
                evidence=[
                    Evidence(kind=EvidenceKind.CHUNK, ref_id=matching_chunk.chunk_id, quote=matching_chunk.text[:100]),
                    Evidence(kind=EvidenceKind.EXPERIENCE, ref_id=exp.id, quote=exp.question_text[:100]),
                ],
            )
        )
    return questions