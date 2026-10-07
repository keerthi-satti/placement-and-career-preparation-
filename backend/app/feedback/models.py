from typing import Optional

from pydantic import BaseModel, Field


class InterviewDateRequest(BaseModel):
    interview_date: str


class InterviewDateResponse(BaseModel):
    resume_upload_id: str
    interview_date: str
    message: str


class PerQuestionFeedback(BaseModel):
    question_id: str
    was_asked: bool
    hint_helped: bool


class FeedbackRequest(BaseModel):
    overall_score: int = Field(ge=1, le=5)
    comment: Optional[str] = None
    per_question: list[PerQuestionFeedback]


class FeedbackResponse(BaseModel):
    resume_upload_id: str
    message: str


class InterviewSchedule(BaseModel):
    resume_upload_id: str
    interview_date: str
    reminder_1_sent: bool = False
    reminder_2_sent: bool = False
    feedback_submitted: bool = False


class FeedbackRecord(BaseModel):
    resume_upload_id: str
    overall_score: int
    comment: Optional[str] = None
    per_question: list[PerQuestionFeedback]


class FeedbackSignal(BaseModel):
    question_type: str
    topic: Optional[str] = None
    skill_area: Optional[str] = None
    was_asked: bool
    hint_helped: bool