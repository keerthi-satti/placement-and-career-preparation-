from fastapi import APIRouter, HTTPException

from app.feedback.models import (
    FeedbackRecord,
    FeedbackRequest,
    FeedbackResponse,
    InterviewDateRequest,
    InterviewDateResponse,
)
from app.feedback.service import (
    get_interview_schedule,
    save_feedback,
    save_feedback_signals,
    save_interview_date,
)


router = APIRouter(
    prefix="/resumes",
    tags=["feedback"],
)


# ---------------------------------------------------------
# Save interview date
# ---------------------------------------------------------

@router.post(
    "/{resume_id}/interview-date",
    response_model=InterviewDateResponse,
)
def set_interview_date(
    resume_id: str,
    request: InterviewDateRequest,
):

    schedule = save_interview_date(
        resume_upload_id=resume_id,
        interview_date=request.interview_date,
    )

    return InterviewDateResponse(
        resume_upload_id=schedule.resume_upload_id,
        interview_date=schedule.interview_date,
        message="Interview date saved",
    )


# ---------------------------------------------------------
# Save feedback
# ---------------------------------------------------------

@router.post(
    "/{resume_id}/feedback",
    response_model=FeedbackResponse,
)
def submit_feedback(
    resume_id: str,
    request: FeedbackRequest,
):

    # -----------------------------------------------------
    # Make sure an interview date exists.
    # -----------------------------------------------------

    schedule = get_interview_schedule(
        resume_upload_id=resume_id
    )

    if schedule is None:
        raise HTTPException(
            status_code=404,
            detail="Interview date not found for this resume",
        )

    # -----------------------------------------------------
    # Prevent duplicate feedback.
    # -----------------------------------------------------

    if schedule.feedback_submitted:
        raise HTTPException(
            status_code=400,
            detail="Feedback has already been submitted",
        )

    # -----------------------------------------------------
    # Create feedback record.
    # -----------------------------------------------------

    feedback = FeedbackRecord(
        resume_upload_id=resume_id,
        overall_score=request.overall_score,
        comment=request.comment,
        per_question=request.per_question,
    )

    # -----------------------------------------------------
    # Save feedback.
    # This also marks feedback_submitted = True.
    # -----------------------------------------------------

    save_feedback(
        resume_upload_id=resume_id,
        feedback=feedback,
    )

    # -----------------------------------------------------
    # Create de-identified signals.
    # -----------------------------------------------------

    save_feedback_signals(feedback)

    return FeedbackResponse(
        resume_upload_id=resume_id,
        message="Feedback submitted successfully",
    )