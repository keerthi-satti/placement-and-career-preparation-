"""
Question generation engine for the Interview Question Generator.

Produces interview questions from project contexts, experience entries,
and resume skills. Every question includes a hint and evidence.

Main entry points:
    generate_questions(project_contexts, experiences, resume_skills, llm_caller=None) -> GenerationResult
    generate_more(existing_questions, project_contexts, experiences, resume_skills, llm_caller=None) -> GenerateMoreResult

For testing without a real LLM:
    from generation.llm_client import MockLLMCaller
    caller = MockLLMCaller()
    result = generate_questions(..., llm_caller=caller)
"""