# Placement and Career Preparation: Interview Question Generator

A web app that helps students prepare for placement interviews. A student uploads a resume and gets interview questions based on their own projects and skills, with a hint for each question and the evidence it came from.

> Status: in development. Items marked **TODO** are for the team to fill in.

## The problem

Students often don't know what to expect in an interview, and general question lists don't match their own resume. Preparing from many scattered resources is confusing and stressful, and it's hard to know what to practice for the projects they actually built.

## Who it is for

- **Primary users:** students preparing for placement interviews.
- **Secondary users:** college placement departments.

## What it does

- Reads a student's resume and the README of each project repository.
- Generates about 20 or more interview questions, in two kinds:
  - **Project questions:** asked the way an interviewer would, based on the student's own projects.
  - **Experience-based questions:** based on real interview experiences collected in advance, matched to the skills on the resume.
- Gives every question a **hint**: what to talk about, not a full answer.
- Shows the **evidence** for every question: the resume line, README section, or interview experience it came from.
- Asks the student for more detail (for example a pasted README) when there is too little information, and returns fewer questions instead of making things up.
- Lets the student click **Generate more** to get additional questions that do not repeat earlier ones.
- Saves each resume's questions to the student's account, so everything is the same after logging out and in again.
- Asks for the student's interview date, sends a reminder afterwards, and collects feedback on how the questions helped.

## Key rules

- **No invented details.** Every question must be backed by its evidence, and each one is checked automatically before it is shown.
- **Hints, not answers.**
- **Student data is deletable.** Each resume upload can be deleted on its own, and a student can delete their whole account. Deleting removes the parsed content, the questions, the feedback, and any pending reminders.
- **No training on student data.** The system improves from de-identified feedback signals only.

## How it works

1. The student signs up and uploads a resume.
2. Ingestion extracts skills and projects, and fetches each project's README.
3. Retrieval finds matching interview experiences from our stored collection.
4. Generation writes questions with hints and evidence, and drops any that fail the evidence check.
5. The backend saves the question set, and the frontend shows it.
6. After the interview date, the student gets a reminder and gives feedback.

## Repository structure

```
contracts/    Shared data shapes and example JSON (agreed by the whole team)
ingestion/    Resume parsing and README fetching
corpus/       Interview experience collection and retrieval
generation/   Question generation and the evidence check
backend/      Accounts, storage, API, pipeline orchestration
frontend/     Web screens
feedback/     Interview date, reminders, student feedback
docs/adr/     Short records of key decisions
CONTEXT.md    Glossary of project terms
TEAM_PLAN.md  Full plan, tasks, and workflow
```

## Tech stack

**TODO:** fill in once the team decides.

- Language and framework (backend): TODO
- Frontend: TODO
- Database: TODO
- LLM provider: TODO
- Email: TODO

## Getting started

**TODO:** fill in once the stack is chosen.

```bash
# Clone
git clone https://github.com/keerthi-satti/placement-and-career-preparation-.git
cd placement-and-career-preparation-

# Create your own branch (see the branch list below)
git checkout -b feat/<your-task>

# Copy the example environment file and fill in your own values
cp .env.example .env

# TODO: install dependencies and run the project
```

Never commit `.env`, API keys, or real student data. This repository is public.

## Team and branches

| Task | Branch | Folder |
|------|--------|--------|
| Input ingestion (resume and README) | `feat/ingestion` | `ingestion/` |
| Experience corpus and retrieval | `feat/corpus` | `corpus/` |
| Question generation engine | `feat/generation` | `generation/` |
| Backend core | `feat/backend` | `backend/` |
| Frontend | `feat/frontend` | `frontend/` |
| Interview date, reminders, feedback | `feat/feedback` | `feedback/` |

## Contributing

- Never push directly to `main`.
- Work on your own branch and in your own folder.
- Open a **pull request** into `main` when a piece works. A teammate reviews it before it is merged.
- In the pull request, say what changed, how you tested it, and whether any contract in `contracts/` was touched.
- Use fake data only.

Details are in `TEAM_PLAN.md`.

## Current status

**TODO:** update as work is merged.

- [ ] Contracts agreed and committed
- [ ] Backend skeleton
- [ ] Ingestion
- [ ] Experience corpus
- [ ] Question generation
- [ ] Frontend
- [ ] Interview date, reminders, feedback
- [ ] Reviewer role (later)

## License

**TODO:** choose a license, or state that all rights are reserved.
