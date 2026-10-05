"""
Tests for the LLM client module.

Run with: pytest generation/tests/test_llm_client.py -v
"""

import json

import pytest

from generation.llm_client import MockLLMCaller


class TestMockLLMCaller:
    def test_returns_valid_json(self):
        caller = MockLLMCaller()
        response = caller("system", "PROJECT: TestApp\nEVIDENCE CHUNKS:\n[test] Some text\nSKILLS: Python")
        data = json.loads(response)
        assert isinstance(data, list)

    def test_project_prompt_returns_questions(self):
        caller = MockLLMCaller()
        response = caller("system", "PROJECT: MyApp\nEVIDENCE CHUNKS:\n[c1] Built with React\nSKILLS: React")
        data = json.loads(response)
        assert len(data) >= 1
        for item in data:
            assert "text" in item
            assert "hint" in item
            assert "difficulty" in item
            assert "evidence_quotes" in item

    def test_experience_prompt_returns_questions(self):
        caller = MockLLMCaller()
        response = caller("system", "INTERVIEW EXPERIENCES:\n[e1] Asked about SQL\nSTUDENT SKILLS: SQL")
        data = json.loads(response)
        assert len(data) >= 1
        for item in data:
            assert "text" in item
            assert "hint" in item
            assert "resume_quote" in item
            assert "experience_id" in item
            assert "experience_quote" in item

    def test_custom_project_response(self):
        custom = [{"text": "Custom Q?", "hint": "Custom hint", "difficulty": "easy", "evidence_quotes": ["test"]}]
        caller = MockLLMCaller(project_responses={"MyApp": custom})
        response = caller("system", "PROJECT: MyApp\nEVIDENCE CHUNKS:\nSKILLS: Python")
        data = json.loads(response)
        assert data[0]["text"] == "Custom Q?"

    def test_custom_experience_response(self):
        custom = [{"text": "Exp Q?", "hint": "Exp hint", "difficulty": "hard",
                    "resume_quote": "Python", "experience_id": "e1", "experience_quote": "asked about Python"}]
        caller = MockLLMCaller(experience_responses=custom)
        response = caller("system", "INTERVIEW EXPERIENCES:\nSTUDENT SKILLS: Python")
        data = json.loads(response)
        assert data[0]["text"] == "Exp Q?"

    def test_unknown_prompt_returns_empty(self):
        caller = MockLLMCaller()
        response = caller("system", "some random prompt")
        data = json.loads(response)
        assert data == []

    def test_call_count_tracking(self):
        caller = MockLLMCaller()
        caller("s", "PROJECT: A\nEVIDENCE:\nSKILLS: X")
        caller("s", "INTERVIEW EXPERIENCES:\nSKILLS: X")
        assert caller._call_count == 2