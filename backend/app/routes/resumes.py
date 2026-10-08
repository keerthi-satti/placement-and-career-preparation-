import uuid
from fastapi import APIRouter, UploadFile, File, HTTPException
import os
import tempfile

from app.fake_data import (
    FAKE_MORE_QUESTIONS,
    FAKE_QUESTION_SET,
    FAKE_RESUME_LIST,
)

from app.ingestion.service import process_resume


router = APIRouter(prefix="/resumes", tags=["resumes"])


@router.post("")
async def upload_resume(file: UploadFile = File(...)):

    # Check that the uploaded file is a PDF
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(
            status_code=400,
            detail="Only PDF resumes are supported."
        )

    temp_path = None

    try:
        # Read uploaded file
        file_data = await file.read()

        # Create temporary PDF file
        with tempfile.NamedTemporaryFile(
            delete=False,
            suffix=".pdf"
        ) as temp_file:

            temp_file.write(file_data)
            temp_path = temp_file.name

        # Run ingestion pipeline
        result = process_resume(temp_path)

        return {
            "resume_upload_id": f"r_{uuid.uuid4().hex[:8]}",
            "status": "processed",
            "filename": file.filename,
            "skills": result["skills"],
            "projects": result["projects"],
            "project_contexts": result["project_contexts"],
            "warnings": result["warnings"]
        }

    except Exception as error:

        raise HTTPException(
            status_code=500,
            detail=f"Resume processing failed: {error}"
        )

    finally:

        # Delete temporary uploaded PDF
        if temp_path and os.path.exists(temp_path):
            os.remove(temp_path)


@router.get("")
def list_resumes():

    return FAKE_RESUME_LIST


@router.get("/{resume_id}/question-set")
def get_question_set(resume_id: str):

    return {
        **FAKE_QUESTION_SET,
        "resume_upload_id": resume_id
    }


@router.post("/{resume_id}/project-details")
def add_project_details(resume_id: str):

    return {
        "message": "fake details saved",
        "status": "processing"
    }


@router.post("/{resume_id}/generate-more")
def generate_more(resume_id: str):

    return {
        "questions": FAKE_MORE_QUESTIONS,
        "exhausted": False
    }


@router.delete("/{resume_id}")
def delete_resume(resume_id: str):

    return {
        "message": f"fake delete of {resume_id} ok"
    }