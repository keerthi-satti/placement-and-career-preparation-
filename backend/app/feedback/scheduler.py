from datetime import datetime, timedelta, timezone

from app.feedback.service import (
    interview_schedules,
    send_email,
)


def parse_interview_date(date_string: str) -> datetime:
    """
    Convert an ISO date/datetime string into a datetime.

    Supports:
    2026-10-10
    2026-10-10T10:00:00
    2026-10-10T10:00:00+05:30
    """

    if len(date_string) == 10:
        date_string = date_string + "T00:00:00"

    date = datetime.fromisoformat(date_string)

    if date.tzinfo is None:
        date = date.replace(tzinfo=timezone.utc)

    return date


def check_reminders(
    now: datetime | None = None,
):
    """
    Check all interview schedules and send reminder emails.

    Reminder 1:
        Interview date + 1 day

    Reminder 2:
        Interview date + 4 days

    No reminders are sent after feedback is submitted.
    """

    if now is None:
        now = datetime.now(timezone.utc)

    for resume_upload_id, schedule in list(
        interview_schedules.items()
    ):

        # -------------------------------------------------
        # Important:
        # Never send an email after feedback is submitted.
        # -------------------------------------------------

        if schedule.feedback_submitted:
            continue

        interview_date = parse_interview_date(
            schedule.interview_date
        )

        reminder_1_date = interview_date + timedelta(days=1)

        # "Three days later" means three days after
        # the first reminder:
        #
        # Interview day       = Day 0
        # First reminder      = Day 1
        # Second reminder     = Day 4
        #
        reminder_2_date = interview_date + timedelta(days=4)

        # -------------------------------------------------
        # First reminder
        # -------------------------------------------------

        if (
            now >= reminder_1_date
            and not schedule.reminder_1_sent
        ):
            send_email(
                to="student@test.com",
                subject="Interview feedback reminder",
                body=(
                    "Your interview was recently completed. "
                    "Please submit your feedback."
                ),
            )

            schedule.reminder_1_sent = True

        # -------------------------------------------------
        # Second reminder
        # -------------------------------------------------

        if (
            now >= reminder_2_date
            and schedule.reminder_1_sent
            and not schedule.reminder_2_sent
        ):
            send_email(
                to="student@test.com",
                subject="Final interview feedback reminder",
                body=(
                    "This is your follow-up reminder to "
                    "submit your interview feedback."
                ),
            )

            schedule.reminder_2_sent = True