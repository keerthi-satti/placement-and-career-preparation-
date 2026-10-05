"""
LLM client abstraction for question generation.

Provides a protocol for LLM callers and a mock implementation for testing.
The real implementation should be provided by the backend (Task 4) which
owns the API key and model configuration.
"""

from __future__ import annotations

import json
import re
from typing import Protocol


class LLMCaller(Protocol):
    """Protocol for LLM callers. Takes system and user prompts, returns text."""

    def __call__(self, system_prompt: str, user_prompt: str) -> str: ...


class MockLLMCaller:
    """
    Mock LLM caller that returns realistic structured JSON responses.
    Used for testing the generation pipeline without a real LLM.

    Extracts chunk_ids and experience_ids from the prompt to produce
    evidence that will pass the evidence checker.
    """

    def __init__(self, project_responses: dict | None = None, experience_responses: list | None = None):
        self._project_responses = project_responses or {}
        self._experience_responses = experience_responses or []
        self._call_count = 0

    def __call__(self, system_prompt: str, user_prompt: str) -> str:
        self._call_count += 1

        # Detect if this is a project or experience prompt
        if "PROJECT:" in user_prompt and "INTERVIEW EXPERIENCES:" not in user_prompt:
            return self._handle_project_prompt(user_prompt)
        elif "INTERVIEW EXPERIENCES:" in user_prompt:
            return self._handle_experience_prompt(user_prompt)
        elif "generate more" in user_prompt.lower() or "additional questions" in user_prompt.lower():
            return self._handle_generate_more_prompt(user_prompt)
        else:
            return "[]"

    def _extract_chunks_from_prompt(self, prompt: str) -> list[dict]:
        """Extract chunk_id and text from the evidence chunks section of a prompt."""
        chunks = []
        # Match lines like: [chunk_id] (source) text
        pattern = r"\[([^\]]+)\]\s+\(([^)]+)\)\s+(.+?)(?=\n\n|\n\[|$)"
        in_evidence = False
        for line in prompt.split("\n"):
            if "EVIDENCE CHUNKS:" in line or "RESUME CHUNKS:" in line or "UNUSED EVIDENCE CHUNKS:" in line:
                in_evidence = True
                continue
            if in_evidence and line.startswith("["):
                match = re.match(r"\[([^\]]+)\]\s+\(([^)]+)\)\s+(.+)", line)
                if match:
                    chunks.append({
                        "chunk_id": match.group(1),
                        "source": match.group(2),
                        "text": match.group(3).strip(),
                    })
            elif in_evidence and line and not line.startswith(" ") and not line.startswith("\t"):
                in_evidence = False

        return chunks

    def _extract_experiences_from_prompt(self, prompt: str) -> list[dict]:
        """Extract experience_id and question_text from the prompt."""
        experiences = []
        lines = prompt.split("\n")
        in_experiences = False
        current_exp = None

        for line in lines:
            if "INTERVIEW EXPERIENCES:" in line:
                in_experiences = True
                continue
            if in_experiences and line.startswith("["):
                match = re.match(r"\[([^\]]+)\]", line)
                if match:
                    if current_exp:
                        experiences.append(current_exp)
                    current_exp = {
                        "id": match.group(1),
                        "question_text": "",
                    }
                    # The question_text is on the indented line after skills
                    # Format: [id] Role at Company (year) - Round\n  Topic: ... | Skills: ...\n  question_text
            elif in_experiences and current_exp and line.strip() and not line.startswith("  Topic:") and not line.startswith("  "):
                # This is the question_text line (after the metadata)
                current_exp["question_text"] = line.strip()
            elif in_experiences and current_exp and line.startswith("  ") and "Topic:" not in line:
                # Continuation or the question text
                stripped = line.strip()
                if stripped and not stripped.startswith("Topic:") and not stripped.startswith("Skills:"):
                    current_exp["question_text"] = stripped

        if current_exp:
            experiences.append(current_exp)

        return experiences

    def _handle_project_prompt(self, prompt: str) -> str:
        # Extract project name
        project_name = "Unknown"
        for line in prompt.split("\n"):
            if line.startswith("PROJECT:"):
                project_name = line.split(":", 1)[1].strip()
                break

        if project_name in self._project_responses:
            return json.dumps(self._project_responses[project_name])

        # Extract actual chunks from the prompt to use real evidence
        chunks = self._extract_chunks_from_prompt(prompt)

        if chunks:
            # Use real chunk text for evidence quotes
            c1 = chunks[0]
            c2 = chunks[1] if len(chunks) > 1 else chunks[0]
            c3 = chunks[2] if len(chunks) > 2 else chunks[0]
            return json.dumps([
                {
                    "text": f"Why did you choose the tech stack you used for {project_name}?",
                    "hint": "Discuss the alternatives you considered and what drove your decision.",
                    "difficulty": "medium",
                    "evidence_quotes": [c1["text"][:60]]
                },
                {
                    "text": f"What was the hardest technical challenge in {project_name}?",
                    "hint": "Describe the problem, what you tried, and how you resolved it.",
                    "difficulty": "hard",
                    "evidence_quotes": [c2["text"][:60]]
                },
                {
                    "text": f"If you had to scale {project_name} to handle 10x the users, what would you change?",
                    "hint": "Think about bottlenecks in your current architecture.",
                    "difficulty": "hard",
                    "evidence_quotes": [c3["text"][:60]]
                }
            ])

        # Fallback
        return json.dumps([
            {
                "text": f"Why did you choose the tech stack you used for {project_name}?",
                "hint": "Discuss the alternatives you considered.",
                "difficulty": "medium",
                "evidence_quotes": ["Built a"]
            }
        ])

    def _handle_experience_prompt(self, prompt: str) -> str:
        if self._experience_responses:
            return json.dumps(self._experience_responses)

        # Extract chunks and experiences from the prompt
        chunks = self._extract_chunks_from_prompt(prompt)
        experiences = self._extract_experiences_from_prompt(prompt)

        results = []

        # Generate one question per experience, matching to a chunk
        for i, exp in enumerate(experiences[:3]):
            # Find a matching chunk
            matching_chunk = None
            if chunks:
                for chunk in chunks:
                    exp_skills = exp.get("question_text", "").lower()
                    if any(word in chunk["text"].lower() for word in exp_skills.split()[:3]):
                        matching_chunk = chunk
                        break
                if matching_chunk is None:
                    matching_chunk = chunks[i % len(chunks)]

            if matching_chunk and exp.get("question_text"):
                results.append({
                    "text": f"Based on interview experiences: {exp['question_text'][:60]}... How would you approach this?",
                    "hint": "Relate to your project experience and discuss your approach.",
                    "difficulty": ["easy", "medium", "hard"][i % 3],
                    "resume_chunk_id": matching_chunk["chunk_id"],
                    "resume_quote": matching_chunk["text"][:60],
                    "experience_id": exp["id"],
                    "experience_quote": exp["question_text"][:60],
                })

        if results:
            return json.dumps(results)

        # Minimal fallback
        return json.dumps([
            {
                "text": "How would you approach a technical interview question about system design?",
                "hint": "Cover scalability, trade-offs, and your experience.",
                "difficulty": "medium",
                "resume_quote": "Built",
                "experience_id": experiences[0]["id"] if experiences else "e_001",
                "experience_quote": experiences[0]["question_text"][:60] if experiences else "Asked",
            }
        ])

    def _handle_generate_more_prompt(self, prompt: str) -> str:
        chunks = self._extract_chunks_from_prompt(prompt)

        if chunks:
            # Use a chunk that's likely unused
            chunk = chunks[-1] if len(chunks) > 1 else chunks[0]
            return json.dumps([
                {
                    "text": "What trade-offs did you consider when designing the database schema?",
                    "hint": "Discuss normalization vs. performance and your reasoning.",
                    "difficulty": "medium",
                    "evidence_type": "chunk",
                    "evidence_ref_id": chunk["chunk_id"],
                    "evidence_quote": chunk["text"][:60],
                }
            ])

        return json.dumps([
            {
                "text": "What trade-offs did you consider when designing the database schema?",
                "hint": "Discuss normalization vs. performance and your reasoning.",
                "difficulty": "medium",
                "evidence_type": "chunk",
                "evidence_ref_id": "p1-readme-03",
                "evidence_quote": "normalized schema",
            }
        ])