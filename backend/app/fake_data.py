FAKE_QUESTIONS = [
    {
        "id": "q_789",
        "text": "Why did you pick PostgreSQL over a simpler database for the expense tracker?",
        "hint": "Talk about the data you stored, any relations between tables, and what you traded off.",
        "type": "project",
        "difficulty": "medium",
        "project_id": "p1",
        "evidence": [
            {
                "kind": "chunk",
                "ref_id": "p1-readme-03",
                "quote": "The app uses PostgreSQL with a nightly backup job",
            }
        ],
    },
    {
        "id": "q_790",
        "text": "How would you speed up a slow SQL query?",
        "hint": "Mention indexes, query plans, and how you would measure the improvement.",
        "type": "experience",
        "difficulty": "medium",
        "project_id": None,
        "evidence": [
            {
                "kind": "chunk",
                "ref_id": "p1-resume-01",
                "quote": "Built a web app to track expenses",
            },
            {
                "kind": "experience",
                "ref_id": "e_456",
                "quote": "Asked how to speed up a slow query.",
            },
        ],
    },
]

FAKE_MORE_QUESTIONS = [
    {
        "id": "q_791",
        "text": "What would you change about the expense tracker if you rebuilt it?",
        "hint": "Talk about design choices, limits you hit, and what you learned.",
        "type": "project",
        "difficulty": "easy",
        "project_id": "p1",
        "evidence": [
            {
                "kind": "chunk",
                "ref_id": "p1-readme-03",
                "quote": "nightly backup job",
            }
        ],
    }
]

FAKE_QUESTION_SET = {
    "id": "qs_1",
    "resume_upload_id": "r_123",
    "questions": FAKE_QUESTIONS,
    "status": "ready",
    "created_at": "2026-10-03T10:00:00Z",
}

FAKE_RESUME_LIST = [
    {"resume_upload_id": "r_123", "filename": "resume.pdf", "status": "ready"}
]
