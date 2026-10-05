# Contracts

Shared data shapes for the Interview Question Generator project.

## Files

- `schemas/` — JSON Schema definitions for every shared data type
- `examples/` — One example JSON per schema, showing realistic data

## Schemas

| Schema | Produced by | Consumed by |
|--------|------------|-------------|
| `resume_ingestion` | Task 1 (ingestion) | Task 3, Task 4 |
| `evidence_chunk` | Task 1 (ingestion) | Task 3, Task 4 |
| `project_context` | Task 1 (ingestion) | Task 3, Task 4 |
| `experience_entry` | Task 2 (corpus) | Task 3, Task 4 |
| `question` | Task 3 (generation) | Task 4, Task 5 |
| `generation_result` | Task 3 (generation) | Task 4 |
| `generate_more_result` | Task 3 (generation) | Task 4 |
| `question_set` | Task 4 (backend) | Task 5, Task 6 |
| `feedback` | Task 6 (feedback) | Task 4 |

## Rules

- `chunk_id` must be stable: same text = same id.
- `text` in evidence chunks is the exact original text, never rewritten.
- `quote` in question evidence must appear verbatim in the referenced source text.
- `type` is `project` or `experience`.
- Experience-based questions have exactly two evidence items (chunk + experience).
- Project questions have one evidence item (chunk).