from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient

from app.main import app
from app.feedback.service import (
    email_log,
    feedback_signals,
    feedback_store,
    interview_schedules,
)
from app.feedback.scheduler import check_reminders


client = TestClient(app)


def clear_feedback_data():
    interview_schedules.clear()
    feedback_store.clear()
    feedback_signals.clear()
    email_log.clear()


# ---------------------------------------------------------
# Test 1: Save interview date
# ---------------------------------------------------------

def test_save_interview_date():

    clear_feedback_data()

    response = client.post(
        "/resumes/r_test/interview-date",
        json={
            "interview_date": "2026-10-10"
        },
    )

    assert response.status_code == 200

    data = response.json()

    assert data["resume_upload_id"] == "r_test"
    assert data["interview_date"] == "2026-10-10"

    assert "r_test" in interview_schedules


# ---------------------------------------------------------
# Test 2: Overall score must be 1-5
# ---------------------------------------------------------

def test_invalid_feedback_score():

    clear_feedback_data()

    client.post(
        "/resumes/r_test/interview-date",
        json={
            "interview_date": "2026-10-10"
        },
    )

    response = client.post(
        "/resumes/r_test/feedback",
        json={
            "overall_score": 6,
            "comment": "Test",
            "per_question": [],
        },
    )

    assert response.status_code == 422


# ---------------------------------------------------------
# Test 3: Submit feedback
# ---------------------------------------------------------

def test_submit_feedback():

    clear_feedback_data()

    client.post(
        "/resumes/r_test/interview-date",
        json={
            "interview_date": "2026-10-10"
        },
    )

    response = client.post(
        "/resumes/r_test/feedback",
        json={
            "overall_score": 4,
            "comment": "Two questions were asked.",
            "per_question": [
                {
                    "question_id": "q_1",
                    "was_asked": True,
                    "hint_helped": True,
                }
            ],
        },
    )

    assert response.status_code == 200

    assert "r_test" in feedback_store

    assert (
        interview_schedules["r_test"].feedback_submitted
        is True
    )


# ---------------------------------------------------------
# Test 4: First reminder
# ---------------------------------------------------------

def test_first_reminder():

    clear_feedback_data()

    client.post(
        "/resumes/r_test/interview-date",
        json={
            "interview_date": "2026-10-10"
        },
    )

    now = datetime(
        2026,
        10,
        11,
        tzinfo=timezone.utc,
    )

    check_reminders(now)

    assert len(email_log) == 1

    assert (
        interview_schedules["r_test"].reminder_1_sent
        is True
    )


# ---------------------------------------------------------
# Test 5: Second reminder
# ---------------------------------------------------------

def test_second_reminder():

    clear_feedback_data()

    client.post(
        "/resumes/r_test/interview-date",
        json={
            "interview_date": "2026-10-10"
        },
    )

    # First reminder: October 11
    first_reminder_time = datetime(
        2026,
        10,
        11,
        tzinfo=timezone.utc,
    )

    check_reminders(first_reminder_time)

    assert len(email_log) == 1

    assert (
        interview_schedules["r_test"].reminder_1_sent
        is True
    )

    # Second reminder: October 14
    second_reminder_time = datetime(
        2026,
        10,
        14,
        tzinfo=timezone.utc,
    )

    check_reminders(second_reminder_time)

    assert len(email_log) == 2

    assert (
        interview_schedules["r_test"].reminder_2_sent
        is True
    )
# ---------------------------------------------------------
# Test 6: No email after feedback
# ---------------------------------------------------------

def test_no_reminder_after_feedback():

    clear_feedback_data()

    client.post(
        "/resumes/r_test/interview-date",
        json={
            "interview_date": "2026-10-10"
        },
    )

    client.post(
        "/resumes/r_test/feedback",
        json={
            "overall_score": 5,
            "comment": "Great.",
            "per_question": [
                {
                    "question_id": "q_1",
                    "was_asked": True,
                    "hint_helped": True,
                }
            ],
        },
    )

    now = datetime(
        2026,
        10,
        14,
        tzinfo=timezone.utc,
    )

    check_reminders(now)

    assert len(email_log) == 0


# ---------------------------------------------------------
# Test 7: De-identified signal created
# ---------------------------------------------------------

def test_feedback_signal_created():

    clear_feedback_data()

    client.post(
        "/resumes/r_test/interview-date",
        json={
            "interview_date": "2026-10-10"
        },
    )

    client.post(
        "/resumes/r_test/feedback",
        json={
            "overall_score": 4,
            "comment": "Good.",
            "per_question": [
                {
                    "question_id": "q_1",
                    "was_asked": True,
                    "hint_helped": False,
                }
            ],
        },
    )

    assert len(feedback_signals) == 1

    signal = feedback_signals[0]

    assert signal.was_asked is True
    assert signal.hint_helped is False

    # De-identified signal should not contain
    # student/resume/question text.
    assert not hasattr(signal, "student_name")
    assert not hasattr(signal, "student_email")
    assert not hasattr(signal, "resume_text")
    assert not hasattr(signal, "question_text")


# ---------------------------------------------------------
# Test 8: Cleanup
# ---------------------------------------------------------

def test_cleanup():

    clear_feedback_data()

    client.post(
        "/resumes/r_test/interview-date",
        json={
            "interview_date": "2026-10-10"
        },
    )

    client.post(
        "/resumes/r_test/feedback",
        json={
            "overall_score": 4,
            "comment": "Good.",
            "per_question": [],
        },
    )

    from app.feedback.service import cleanup_resume_feedback

    cleanup_resume_feedback("r_test")

    assert "r_test" not in interview_schedules
    assert "r_test" not in feedback_store