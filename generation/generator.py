"""
Core question generation engine.

Orchestrates LLM calls, evidence checking, deduplication, and count rules.
This is the main module Task 4 (backend) will call.

Usage:
    from generation.generator import generate_questions, generate_more
    from generation.llm_client import MockLLMCaller  # or a real caller

    result = generate_questions(project_contexts, experiences, skills, llm_caller=caller)
    more = generate_more(result.questions, project_contexts, experiences, skills, llm_caller=caller)
"""

from __future__ import annotations

import json
import re
import uuid
from typing import Optional

from .evidence_checker import check_question_evidence, filter_valid_questions
from .llm_client import LLMCaller
from .models import (
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
from .prompts import (
    EXPERIENCE_QUESTION_PROMPT,
    GENERATE_MORE_PROMPT,
    PROJECT_QUESTION_PROMPT,
    SYSTEM_PROMPT,
)


# --- Count rules (from the plan, section 7, Task 3) ---
BASELINE_COUNT = 20
MIN_PER_PROJECT = 2
MAX_FIRST_GEN = 40
INSUFFICIENT_THRESHOLD = 5


# --- Helpers ---


def _normalize(text: str) -> str:
    """Normalize text for comparison: lowercase, collapse whitespace."""
    return re.sub(r"\s+", " ", text.lower().strip())


def _generate_id() -> str:
    return f"q_{uuid.uuid4().hex[:8]}"


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


def _resolve_quote_to_chunk(quote: str, chunks: list[EvidenceChunk]) -> Optional[str]:
    """
    Find which chunk_id contains the given quote.
    Returns the chunk_id or None if no match.
    """
    quote_norm = _normalize(quote)
    for chunk in chunks:
        if quote_norm in _normalize(chunk.text):
            return chunk.chunk_id
    return None


def _questions_are_similar(q1: Question, q2: Question) -> bool:
    """
    Check if two questions are semantically similar (reworded versions).
    Uses word overlap as a simple heuristic.
    """
    words1 = set(_normalize(q1.text).split())
    words2 = set(_normalize(q2.text).split())
    # Remove common stop words
    stop_words = {"a", "an", "the", "is", "are", "was", "were", "be", "been",
                  "being", "have", "has", "had", "do", "does", "did", "will",
                  "would", "could", "should", "may", "might", "can", "shall",
                  "to", "of", "in", "for", "on", "with", "at", "by", "from",
                  "as", "into", "through", "during", "before", "after", "above",
                  "below", "between", "out", "off", "over", "under", "again",
                  "further", "then", "once", "here", "there", "when", "where",
                  "why", "how", "all", "each", "every", "both", "few", "more",
                  "most", "other", "some", "such", "no", "nor", "not", "only",
                  "own", "same", "so", "than", "too", "very", "just", "because",
                  "but", "and", "or", "if", "while", "about", "up", "you", "your",
                  "i", "me", "my", "we", "our", "it", "its", "this", "that",
                  "these", "those", "what", "which", "who", "whom"}
    words1 -= stop_words
    words2 -= stop_words

    if not words1 or not words2:
        return False

    overlap = len(words1 & words2)
    smaller = min(len(words1), len(words2))
    return overlap / smaller > 0.7


# --- Parsers ---


def _parse_project_questions(
    response: str,
    project_id: str,
    chunks: list[EvidenceChunk],
) -> list[Question]:
    """
    Parse LLM response into Question objects for a project.
    Resolves evidence_quotes to chunk_ids.
    """
    try:
        data = json.loads(response)
    except json.JSONDecodeError:
        return []

    if not isinstance(data, list):
        return []

    questions = []
    for item in data:
        if not isinstance(item, dict):
            continue
        if "text" not in item or "hint" not in item:
            continue

        evidence_quotes = item.get("evidence_quotes", [])
        if not evidence_quotes:
            continue

        # Resolve each quote to a chunk_id
        evidence = []
        for quote in evidence_quotes:
            chunk_id = _resolve_quote_to_chunk(quote, chunks)
            if chunk_id:
                evidence.append(
                    Evidence(kind=EvidenceKind.CHUNK, ref_id=chunk_id, quote=quote)
                )

        if not evidence:
            continue

        difficulty_str = item.get("difficulty", "medium")
        try:
            difficulty = Difficulty(difficulty_str)
        except ValueError:
            difficulty = Difficulty.MEDIUM

        questions.append(
            Question(
                id=_generate_id(),
                text=item["text"],
                hint=item["hint"],
                type=QuestionType.PROJECT,
                difficulty=difficulty,
                project_id=project_id,
                evidence=evidence,
            )
        )
    return questions


def _parse_experience_questions(
    response: str,
    chunks: list[EvidenceChunk],
) -> list[Question]:
    """
    Parse LLM response into experience-based Question objects.
    Resolves resume_chunk_id and validates experience references.
    """
    try:
        data = json.loads(response)
    except json.JSONDecodeError:
        return []

    if not isinstance(data, list):
        return []

    questions = []
    for item in data:
        if not isinstance(item, dict):
            continue
        if "text" not in item or "hint" not in item:
            continue

        evidence = []

        # Resume chunk evidence
        resume_chunk_id = item.get("resume_chunk_id", "")
        resume_quote = item.get("resume_quote", "")
        if resume_quote:
            # Try to resolve by explicit chunk_id first, then by quote matching
            if resume_chunk_id:
                evidence.append(
                    Evidence(kind=EvidenceKind.CHUNK, ref_id=resume_chunk_id, quote=resume_quote)
                )
            else:
                resolved = _resolve_quote_to_chunk(resume_quote, chunks)
                if resolved:
                    evidence.append(
                        Evidence(kind=EvidenceKind.CHUNK, ref_id=resolved, quote=resume_quote)
                    )

        # Experience evidence
        experience_id = item.get("experience_id", "")
        experience_quote = item.get("experience_quote", "")
        if experience_id and experience_quote:
            evidence.append(
                Evidence(kind=EvidenceKind.EXPERIENCE, ref_id=experience_id, quote=experience_quote)
            )

        # Experience-based questions need exactly 2 evidence items
        if len(evidence) < 2:
            continue

        difficulty_str = item.get("difficulty", "medium")
        try:
            difficulty = Difficulty(difficulty_str)
        except ValueError:
            difficulty = Difficulty.MEDIUM

        questions.append(
            Question(
                id=_generate_id(),
                text=item["text"],
                hint=item["hint"],
                type=QuestionType.EXPERIENCE,
                difficulty=difficulty,
                project_id=None,
                evidence=evidence,
            )
        )
    return questions


def _parse_generate_more_questions(
    response: str,
    chunks: list[EvidenceChunk],
    experiences: list[ExperienceEntry],
) -> list[Question]:
    """
    Parse LLM response for generate_more. The format is slightly different
    (single evidence item per question instead of array).
    """
    try:
        data = json.loads(response)
    except json.JSONDecodeError:
        return []

    if not isinstance(data, list):
        return []

    exp_map = _build_experience_map(experiences)
    questions = []

    for item in data:
        if not isinstance(item, dict):
            continue
        if "text" not in item or "hint" not in item:
            continue

        evidence_type = item.get("evidence_type", "chunk")
        evidence_ref_id = item.get("evidence_ref_id", "")
        evidence_quote = item.get("evidence_quote", "")

        if not evidence_ref_id or not evidence_quote:
            continue

        # Validate the evidence exists
        if evidence_type == "chunk":
            chunk_id = evidence_ref_id
            if not any(c.chunk_id == chunk_id for c in chunks):
                # Try to resolve by quote
                chunk_id = _resolve_quote_to_chunk(evidence_quote, chunks)
                if not chunk_id:
                    continue
            evidence = [Evidence(kind=EvidenceKind.CHUNK, ref_id=chunk_id, quote=evidence_quote)]
            qtype = QuestionType.PROJECT
            # Find project_id from chunk
            project_id = next((c.project_id for c in chunks if c.chunk_id == chunk_id), None)
        elif evidence_type == "experience":
            if evidence_ref_id not in exp_map:
                continue
            evidence = [Evidence(kind=EvidenceKind.EXPERIENCE, ref_id=evidence_ref_id, quote=evidence_quote)]
            qtype = QuestionType.EXPERIENCE
            project_id = None
        else:
            continue

        difficulty_str = item.get("difficulty", "medium")
        try:
            difficulty = Difficulty(difficulty_str)
        except ValueError:
            difficulty = Difficulty.MEDIUM

        questions.append(
            Question(
                id=_generate_id(),
                text=item["text"],
                hint=item["hint"],
                type=qtype,
                difficulty=difficulty,
                project_id=project_id,
                evidence=evidence,
            )
        )
    return questions


# --- Stub generators (for testing without LLM) ---


def _stub_project_questions(pc: ProjectContext, skills: list[str]) -> list[Question]:
    """Generate stub questions for testing without an LLM."""
    questions = []
    difficulties = [Difficulty.EASY, Difficulty.MEDIUM, Difficulty.HARD]

    for i, chunk in enumerate(pc.evidence_chunks[:3]):
        diff = difficulties[i % 3]
        text_preview = chunk.text[:80]
        questions.append(
            Question(
                id=_generate_id(),
                text=f"Regarding your {pc.project_name} project: '{text_preview}...' Can you explain your approach?",
                hint=f"Discuss the technical choices and trade-offs related to {chunk.source.value} details.",
                type=QuestionType.PROJECT,
                difficulty=diff,
                project_id=pc.project_id,
                evidence=[Evidence(kind=EvidenceKind.CHUNK, ref_id=chunk.chunk_id, quote=chunk.text[:100])],
            )
        )

    # Ensure at least MIN_PER_PROJECT questions
    if len(questions) < MIN_PER_PROJECT and pc.evidence_chunks:
        chunk = pc.evidence_chunks[0]
        questions.append(
            Question(
                id=_generate_id(),
                text=f"What would you do differently if you started {pc.project_name} over?",
                hint="Reflect on lessons learned and alternative approaches.",
                type=QuestionType.PROJECT,
                difficulty=Difficulty.MEDIUM,
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
    difficulties = [Difficulty.EASY, Difficulty.MEDIUM, Difficulty.HARD]
    for i, exp in enumerate(experiences[:5]):
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

        diff = difficulties[i % 3]
        questions.append(
            Question(
                id=_generate_id(),
                text=f"Based on interview experiences at {exp.company}: {exp.question_text[:80]}... How would you approach this given your background?",
                hint=f"Relate to your experience with {', '.join(exp.skills)}.",
                type=QuestionType.EXPERIENCE,
                difficulty=diff,
                project_id=None,
                evidence=[
                    Evidence(kind=EvidenceKind.CHUNK, ref_id=matching_chunk.chunk_id, quote=matching_chunk.text[:100]),
                    Evidence(kind=EvidenceKind.EXPERIENCE, ref_id=exp.id, quote=exp.question_text[:100]),
                ],
            )
        )
    return questions


# --- Main entry points ---


def generate_questions(
    project_contexts: list[ProjectContext],
    experiences: list[ExperienceEntry],
    resume_skills: list[str],
    llm_caller: Optional[LLMCaller] = None,
) -> GenerationResult:
    """
    Generate interview questions from project contexts and experience entries.

    This is the primary entry point called by Task 4 (backend).

    Args:
        project_contexts: Parsed project data with evidence chunks (from Task 1).
        experiences: Matched interview experience entries (from Task 2).
        resume_skills: Skills extracted from the resume.
        llm_caller: LLM caller implementation. If None, uses stub mode.

    Returns:
        GenerationResult with questions, warnings, and insufficient_input flag.
    """
    warnings: list[str] = []
    questions: list[Question] = []

    # Collect all chunks for evidence checking and parsing
    all_chunks: list[EvidenceChunk] = []
    for pc in project_contexts:
        all_chunks.extend(pc.evidence_chunks)
    chunk_map = _build_chunk_map(all_chunks)
    exp_map = _build_experience_map(experiences)

    # --- Edge case: no input at all ---
    if not project_contexts and not experiences:
        return GenerationResult(
            questions=[],
            warnings=["No projects or interview experiences found in input."],
            insufficient_input=True,
            reason="No projects or interview experiences found. Provide a resume with projects and their repositories.",
        )

    # --- Edge case: no projects, only experiences ---
    if not project_contexts and experiences:
        warnings.append("No projects found. Generating experience-based questions only.")

    # --- Project questions ---
    for pc in project_contexts:
        if pc.input_quality == InputQuality.MISSING:
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
            try:
                response = llm_caller(SYSTEM_PROMPT, prompt)
                parsed = _parse_project_questions(response, pc.project_id, pc.evidence_chunks)
                questions.extend(parsed)
            except Exception as e:
                warnings.append(f"Project '{pc.project_name}': LLM call failed ({e}), using fallback.")
                questions.extend(_stub_project_questions(pc, resume_skills))
        else:
            # Stub mode
            questions.extend(_stub_project_questions(pc, resume_skills))

    # --- Experience-based questions ---
    if experiences:
        if llm_caller is not None:
            prompt = EXPERIENCE_QUESTION_PROMPT.format(
                skills=", ".join(resume_skills),
                resume_chunks=_format_evidence_text(all_chunks),
                experiences_text=_format_experiences_text(experiences),
            )
            try:
                response = llm_caller(SYSTEM_PROMPT, prompt)
                parsed = _parse_experience_questions(response, all_chunks)
                questions.extend(parsed)
            except Exception as e:
                warnings.append(f"Experience questions: LLM call failed ({e}), using fallback.")
                questions.extend(_stub_experience_questions(experiences, all_chunks))
        else:
            questions.extend(_stub_experience_questions(experiences, all_chunks))

    # --- Evidence check (plan: drop any question that fails) ---
    valid_questions = filter_valid_questions(questions, chunk_map, exp_map)
    dropped = len(questions) - len(valid_questions)
    if dropped > 0:
        warnings.append(f"Dropped {dropped} questions that failed evidence check.")

    # --- Count rules (plan section 7, Task 3) ---
    # Insufficient: ~5 or fewer valid questions
    if len(valid_questions) <= INSUFFICIENT_THRESHOLD:
        return GenerationResult(
            questions=valid_questions,
            warnings=warnings,
            insufficient_input=True,
            reason=f"Only {len(valid_questions)} valid questions could be grounded in evidence. "
                   "Provide more project details or a richer resume for better results.",
        )

    # Cap at MAX_FIRST_GEN (40)
    final_questions = valid_questions[:MAX_FIRST_GEN]

    return GenerationResult(
        questions=final_questions,
        warnings=warnings,
        insufficient_input=False,
        reason=None,
    )


def generate_more(
    existing_questions: list[Question],
    project_contexts: list[ProjectContext],
    experiences: list[ExperienceEntry],
    resume_skills: list[str],
    llm_caller: Optional[LLMCaller] = None,
) -> GenerateMoreResult:
    """
    Generate additional questions that don't repeat existing ones.

    Plan rules:
    - New questions must not repeat earlier ones (not reworded, same-evidence repeats)
    - Use unused evidence first
    - Return exhausted=True when no more grounded questions can be produced

    Args:
        existing_questions: Questions already generated.
        project_contexts: Parsed project data with evidence chunks.
        experiences: Matched interview experience entries.
        resume_skills: Skills extracted from the resume.
        llm_caller: LLM caller implementation. If None, uses stub mode.

    Returns:
        GenerateMoreResult with new questions and exhausted flag.
    """
    # Build maps
    all_chunks: list[EvidenceChunk] = []
    for pc in project_contexts:
        all_chunks.extend(pc.evidence_chunks)
    chunk_map = _build_chunk_map(all_chunks)
    exp_map = _build_experience_map(experiences)

    # Find evidence already used
    used_chunk_ids: set[str] = set()
    used_exp_ids: set[str] = set()
    for q in existing_questions:
        for ev in q.evidence:
            if ev.kind == EvidenceKind.CHUNK:
                used_chunk_ids.add(ev.ref_id)
            elif ev.kind == EvidenceKind.EXPERIENCE:
                used_exp_ids.add(ev.ref_id)

    unused_chunks = [c for c in all_chunks if c.chunk_id not in used_chunk_ids]
    unused_experiences = [e for e in experiences if e.id not in used_exp_ids]

    # If all evidence is used, try generating from used evidence but different angles
    # Only return exhausted if we truly have nothing left
    if not unused_chunks and not unused_experiences:
        # Try with all evidence but mark as potentially exhausted
        unused_chunks = all_chunks
        unused_experiences = experiences
        all_evidence_used = True
    else:
        all_evidence_used = False

    new_questions: list[Question] = []

    if llm_caller is not None:
        # Format existing questions for the prompt
        existing_text = "\n".join(
            f"- [{q.type.value}] {q.text}" for q in existing_questions
        )
        unused_chunks_text = _format_evidence_text(unused_chunks) if unused_chunks else "None available"
        unused_exp_text = _format_experiences_text(unused_experiences) if unused_experiences else "None available"

        prompt = GENERATE_MORE_PROMPT.format(
            existing_questions=existing_text,
            unused_chunks=unused_chunks_text,
            unused_experiences=unused_exp_text,
            skills=", ".join(resume_skills),
        )
        try:
            response = llm_caller(SYSTEM_PROMPT, prompt)
            new_questions = _parse_generate_more_questions(response, all_chunks, experiences)
        except Exception:
            new_questions = []

    if not new_questions and not llm_caller:
        # Stub mode: generate from unused evidence
        for chunk in unused_chunks[:5]:
            q = Question(
                id=_generate_id(),
                text=f"Can you walk me through how you implemented the feature described as: '{chunk.text[:60]}'?",
                hint="Explain your technical approach, decisions, and any trade-offs.",
                type=QuestionType.PROJECT,
                difficulty=Difficulty.MEDIUM,
                project_id=chunk.project_id,
                evidence=[Evidence(kind=EvidenceKind.CHUNK, ref_id=chunk.chunk_id, quote=chunk.text[:100])],
            )
            new_questions.append(q)

    # --- Deduplication ---
    # 1. Remove questions with IDs that already exist
    existing_ids = {q.id for q in existing_questions}
    new_questions = [q for q in new_questions if q.id not in existing_ids]

    # 2. Remove semantically similar questions (plan: "not reworded")
    deduped = []
    for new_q in new_questions:
        is_repeat = False
        for existing_q in existing_questions:
            if _questions_are_similar(new_q, existing_q):
                is_repeat = True
                break
        if not is_repeat:
            deduped.append(new_q)
    new_questions = deduped

    # 3. Remove same-evidence repeats (plan: "same-evidence repeats")
    # A new question that cites the exact same evidence as an existing one
    # is a repeat, even if the question text differs.
    existing_evidence_sigs = set()
    for q in existing_questions:
        sig = tuple(sorted((ev.kind.value, ev.ref_id) for ev in q.evidence))
        existing_evidence_sigs.add(sig)

    no_evidence_repeats = []
    for new_q in new_questions:
        sig = tuple(sorted((ev.kind.value, ev.ref_id) for ev in new_q.evidence))
        if sig not in existing_evidence_sigs:
            no_evidence_repeats.append(new_q)
    new_questions = no_evidence_repeats

    # --- Evidence check on new questions ---
    valid_new = filter_valid_questions(new_questions, chunk_map, exp_map)

    # Determine if exhausted
    # Exhausted if: all evidence was already used AND no new valid questions
    # OR: no unused evidence and no LLM to generate creative new ones
    exhausted = all_evidence_used and len(valid_new) == 0

    return GenerateMoreResult(questions=valid_new, exhausted=exhausted)