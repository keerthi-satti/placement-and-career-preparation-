from fastapi import APIRouter

from app.fake_data import (
    FAKE_MORE_QUESTIONS,
    FAKE_QUESTION_SET,
    FAKE_RESUME_LIST,
)

router = APIRouter(prefix="/resumes", tags=["resumes"])


@router.post("")
def upload_resume():
    return {"resume_upload_id": "r_123", "status": "processing"}


@router.get("")
def list_resumes():
    return FAKE_RESUME_LIST


@router.get("/{resume_id}/question-set")
def get_question_set(resume_id: str):
    return {**FAKE_QUESTION_SET, "resume_upload_id": resume_id}


@router.post("/{resume_id}/project-details")
def add_project_details(resume_id: str):
    return {"message": "fake details saved", "status": "processing"}


@router.post("/{resume_id}/generate-more")
def generate_more(resume_id: str):
    return {"questions": FAKE_MORE_QUESTIONS, "exhausted": False}


@router.delete("/{resume_id}")
def delete_resume(resume_id: str):
    return {"message": f"fake delete of {resume_id} ok"}