from datetime import datetime, timedelta, timezone

from app.feedback.models import (
    FeedbackRecord,
    FeedbackSignal,
    InterviewSchedule,
)


# ---------------------------------------------------------
# Temporary in-memory storage
# ---------------------------------------------------------

interview_schedules: dict[str, InterviewSchedule] = {}

feedback_store: dict[str, FeedbackRecord] = {}

feedback_signals: list[FeedbackSignal] = []

email_log: list[dict] = []


# ---------------------------------------------------------
# Interview date
# ---------------------------------------------------------

def save_interview_date(
    resume_upload_id: str,
    interview_date: str,
) -> InterviewSchedule:

    schedule = InterviewSchedule(
        resume_upload_id=resume_upload_id,
        interview_date=interview_date,
        reminder_1_sent=False,
        reminder_2_sent=False,
        feedback_submitted=False,
    )

    interview_schedules[resume_upload_id] = schedule

    return schedule


def get_interview_schedule(
    resume_upload_id: str,
) -> InterviewSchedule | None:

    return interview_schedules.get(resume_upload_id)


# ---------------------------------------------------------
# Email
# ---------------------------------------------------------

def send_email(
    to: str,
    subject: str,
    body: str,
):
    """
    Day-1 implementation.

    We do not send a real email.
    We only log the email so the scheduler can be tested.
    """

    email = {
        "to": to,
        "subject": subject,
        "body": body,
    }

    email_log.append(email)

    print("=" * 50)
    print("TEST EMAIL")
    print("TO:", to)
    print("SUBJECT:", subject)
    print(body)
    print("=" * 50)


# ---------------------------------------------------------
# Feedback
# ---------------------------------------------------------

def save_feedback(
    resume_upload_id: str,
    feedback: FeedbackRecord,
):

    feedback_store[resume_upload_id] = feedback

    # Mark feedback as submitted.
    schedule = interview_schedules.get(resume_upload_id)

    if schedule:
        schedule.feedback_submitted = True
        interview_schedules[resume_upload_id] = schedule

    return feedback


# ---------------------------------------------------------
# De-identified feedback signals
# ---------------------------------------------------------

def save_feedback_signals(
    feedback: FeedbackRecord,
):
    """
    Store only de-identified signals.

    No student name.
    No student email.
    No resume text.
    No question text.
    """

    for item in feedback.per_question:

        # The current Task 6 contract does not contain
        # question type/topic/skill metadata.

        # Therefore we use "unknown" until the generation
        # module provides that metadata.

        signal = FeedbackSignal(
            question_type="unknown",
            topic=None,
            skill_area=None,
            was_asked=item.was_asked,
            hint_helped=item.hint_helped,
        )

        feedback_signals.append(signal)


# ---------------------------------------------------------
# Cleanup
# ---------------------------------------------------------

def cleanup_resume_feedback(
    resume_upload_id: str,
):
    """
    Called by Task 4 when a resume upload is deleted.

    Removes:
    - interview date
    - feedback
    - pending reminders
    """

    interview_schedules.pop(
        resume_upload_id,
        None,
    )

    feedback_store.pop(
        resume_upload_id,
        None,
    )


def cleanup_account(
    resume_upload_ids: list[str],
):
    """
    Called when an account is deleted.
    """

    for resume_upload_id in resume_upload_ids:
        cleanup_resume_feedback(resume_upload_id)