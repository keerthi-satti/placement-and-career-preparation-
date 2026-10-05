"""
Question generation engine for the Interview Question Generator.

Produces interview questions from project contexts, experience entries,
and resume skills. Every question includes a hint and evidence.

Main entry points:
    generate_questions(project_contexts, experiences, resume_skills) -> GenerationResult
    generate_more(existing_questions, project_contexts, experiences, resume_skills) -> GenerateMoreResult
"""