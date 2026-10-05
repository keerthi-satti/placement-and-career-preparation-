"""
LLM client abstraction for question generation.

Provides a protocol for LLM callers and a mock implementation for testing.
The real implementation should be provided by the backend (Task 4) which
owns the API key and model configuration.
"""

from __future__ import annotations

import json
from typing import Protocol


class LLMCaller(Protocol):
    """Protocol for LLM callers. Takes system and user prompts, returns text."""

    def __call__(self, system_prompt: str, user_prompt: str) -> str: ...


class MockLLMCaller:
    """
    Mock LLM caller that returns realistic structured JSON responses.
    Used for testing the generation pipeline without a real LLM.
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

    def _handle_project_prompt(self, prompt: str) -> str:
        # Extract project name
        project_name = "Unknown"
        for line in prompt.split("\n"):
            if line.startswith("PROJECT:"):
                project_name = line.split(":", 1)[1].strip()
                break

        if project_name in self._project_responses:
            return json.dumps(self._project_responses[project_name])

        # Default: generate 3 questions per project
        return json.dumps([
            {
                "text": f"Why did you choose the tech stack you used for {project_name}?",
                "hint": "Discuss the alternatives you considered and what drove your decision.",
                "difficulty": "medium",
                "evidence_quotes": ["Tech stack"]
            },
            {
                "text": f"What was the hardest technical challenge in {project_name}?",
                "hint": "Describe the problem, what you tried, and how you resolved it.",
                "difficulty": "hard",
                "evidence_quotes": ["Built a"]
            },
            {
                "text": f"If you had to scale {project_name} to handle 10x the users, what would you change?",
                "hint": "Think about bottlenecks in your current architecture.",
                "difficulty": "hard",
                "evidence_quotes": ["Built a"]
            }
        ])

    def _handle_experience_prompt(self, prompt: str) -> str:
        if self._experience_responses:
            return json.dumps(self._experience_responses)

        # Default: generate 2 experience-based questions
        return json.dumps([
            {
                "text": "Based on common interview experiences, how would you optimize a slow database query?",
                "hint": "Discuss indexing, query planning, and when to denormalize.",
                "difficulty": "medium",
                "resume_quote": "PostgreSQL",
                "experience_id": "e_001",
                "experience_quote": "Asked how to speed up a slow query"
            },
            {
                "text": "How would you design a real-time system to handle thousands of concurrent connections?",
                "hint": "Cover WebSocket management, horizontal scaling, and caching strategies.",
                "difficulty": "hard",
                "resume_quote": "WebSocket",
                "experience_id": "e_002",
                "experience_quote": "scale a real-time chat system"
            }
        ])

    def _handle_generate_more_prompt(self, prompt: str) -> str:
        return json.dumps([
            {
                "text": "What trade-offs did you consider when designing the database schema?",
                "hint": "Discuss normalization vs. performance and your reasoning.",
                "difficulty": "medium",
                "evidence_quotes": ["normalized schema"]
            }
        ])