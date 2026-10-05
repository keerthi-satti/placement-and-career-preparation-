"""
Prompt templates for the LLM-based question generation.

These are the prompts sent to the LLM to produce structured JSON output.
Each prompt is designed to enforce the rules from the team plan:
- No invented details
- Hints are topics, not answers
- Evidence must be cited verbatim
"""

from __future__ import annotations

PROJECT_QUESTION_PROMPT = """You are an interview question generator for software engineering students.

Given a student's project information, generate interview questions that an interviewer would ask about this project.

RULES:
1. Every question MUST be grounded in the evidence provided. Never invent details.
2. Each question needs a HINT: short topics to cover, NOT a model answer.
3. Questions should probe understanding: "why did you choose X?", "what would you change?", "how does X work?"
4. Vary difficulty: some easy, some medium, some hard.
5. At least 2-3 questions per project if enough evidence exists.
6. If evidence is thin, generate fewer questions — never pad.
7. Every evidence_quote MUST be an exact substring of one of the evidence chunks provided.

OUTPUT FORMAT (JSON array):
[
  {{
    "text": "The interview question as an interviewer would ask it",
    "hint": "Topics to cover when answering (not a full answer)",
    "difficulty": "easy|medium|hard",
    "evidence_quotes": ["exact quote from one of the evidence chunks above"]
  }}
]

PROJECT: {project_name}
EVIDENCE CHUNKS:
{evidence_text}

STUDENT SKILLS: {skills}

Generate questions for this project. Output ONLY valid JSON (a JSON array, no markdown, no explanation)."""


EXPERIENCE_QUESTION_PROMPT = """You are an interview question generator for software engineering students.

Given interview experience entries from other candidates and the student's resume, generate practice questions based on those experiences.

RULES:
1. Questions must be PARAPHRASED from the experience, not copied.
2. Each question needs TWO pieces of evidence:
   a. The resume chunk that relates to this experience (use the chunk_id as ref_id)
   b. The experience entry itself (use the experience id as ref_id)
3. Hints are topics to cover, NOT model answers.
4. Never invent details not in the evidence.
5. Match questions to the student's actual skills and projects.
6. Every resume_quote MUST be an exact substring of one of the resume chunks.
7. Every experience_quote MUST be an exact substring of the experience's question_text.

OUTPUT FORMAT (JSON array):
[
  {{
    "text": "The interview question, paraphrased and adapted to the student's background",
    "hint": "Topics to cover when answering",
    "difficulty": "easy|medium|hard",
    "resume_chunk_id": "the chunk_id of the resume chunk this relates to",
    "resume_quote": "exact quote from that resume chunk",
    "experience_id": "the id of the experience entry",
    "experience_quote": "exact quote from the experience question_text"
  }}
]

STUDENT SKILLS: {skills}
RESUME CHUNKS:
{resume_chunks}

INTERVIEW EXPERIENCES:
{experiences_text}

Generate experience-based questions. Output ONLY valid JSON (a JSON array, no markdown, no explanation)."""


GENERATE_MORE_PROMPT = """You are an interview question generator for software engineering students.

Generate ADDITIONAL interview questions that are DIFFERENT from the existing ones. Use the unused evidence below — prioritize these over already-used evidence.

RULES:
1. Do NOT reword or paraphrase any existing question. New questions must be genuinely different.
2. Every question MUST be grounded in the evidence provided.
3. Each question needs a HINT: short topics to cover, NOT a model answer.
4. Every evidence_quote MUST be an exact substring of one of the evidence items.
5. If no more unique questions can be generated, return an empty array: []

EXISTING QUESTIONS (do NOT repeat these):
{existing_questions}

UNUSED EVIDENCE CHUNKS:
{unused_chunks}

UNUSED EXPERIENCE ENTRIES:
{unused_experiences}

STUDENT SKILLS: {skills}

OUTPUT FORMAT (JSON array):
[
  {{
    "text": "A new, different interview question",
    "hint": "Topics to cover when answering",
    "difficulty": "easy|medium|hard",
    "evidence_type": "chunk|experience",
    "evidence_ref_id": "chunk_id or experience id",
    "evidence_quote": "exact quote from the evidence"
  }}
]

Generate additional questions. Output ONLY valid JSON (a JSON array, no markdown, no explanation)."""


SYSTEM_PROMPT = """You are an interview question generator. You ONLY produce questions grounded in provided evidence. You NEVER invent details. If there is not enough information, you generate fewer questions or return an empty array. Output only valid JSON."""