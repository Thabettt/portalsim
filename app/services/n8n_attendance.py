import logging
import uuid
from datetime import datetime, timezone

import httpx
from sqlmodel import Session, select

from app.config import get_settings
from app.models import (
    Attendance,
    AttendanceWarningLevel,
    Course,
    CourseEnrollment,
    User,
    UserRole,
)

logger = logging.getLogger(__name__)

WARNING_LEVEL_VALUES = {
    AttendanceWarningLevel.NONE: 0,
    AttendanceWarningLevel.FIRST_WARNING: 1,
    AttendanceWarningLevel.SECOND_WARNING: 2,
    AttendanceWarningLevel.FINAL_WARNING: 3,
}


class AttendanceFinalizationError(Exception):
    """Raised when the finalized snapshot cannot be accepted by n8n."""


class AttendanceFinalizationNotConfigured(AttendanceFinalizationError):
    """Raised when the n8n attendance webhook URL is missing."""


def build_attendance_snapshot(session: Session) -> dict:
    """Build the authoritative saved warning state for every student enrollment."""
    finalized_at = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    students = session.exec(
        select(User)
        .where(User.role == UserRole.STUDENT)
        .where(User.is_active == True)
        .order_by(User.student_id)
    ).all()

    student_records = []
    course_record_count = 0

    for student in students:
        enrollments = session.exec(
            select(CourseEnrollment, Course)
            .join(Course, CourseEnrollment.course_id == Course.id)
            .where(CourseEnrollment.student_id == student.id)
            .order_by(Course.code)
        ).all()

        courses = []
        for _, course in enrollments:
            latest_attendance = session.exec(
                select(Attendance)
                .where(Attendance.student_id == student.id)
                .where(Attendance.course_id == course.id)
                .order_by(Attendance.date.desc(), Attendance.marked_at.desc())
            ).first()
            warning_level = (
                latest_attendance.warning_level
                if latest_attendance
                else AttendanceWarningLevel.NONE
            )
            courses.append({
                "course_id": course.code,
                "course_name": course.name,
                "warning_level": WARNING_LEVEL_VALUES[warning_level],
            })
            course_record_count += 1

        student_records.append({
            "student_id": student.student_id,
            "student_name": student.full_name,
            "recipient": student.email,
            "courses": courses,
        })

    return {
        "batch_id": str(uuid.uuid4()),
        "finalized_at": finalized_at,
        "warning_level_labels": {
            "0": "Good",
            "1": "Warning 1",
            "2": "Warning 2",
            "3": "Drop",
        },
        "students": student_records,
        "students_count": len(student_records),
        "course_records_count": course_record_count,
    }


async def send_attendance_snapshot(session: Session) -> dict:
    """Send the current saved attendance snapshot to the n8n workflow."""
    settings = get_settings()
    webhook_url = settings.n8n_attendance_webhook_url.strip()
    if not webhook_url:
        raise AttendanceFinalizationNotConfigured(
            "The n8n attendance webhook URL is not configured."
        )

    snapshot = build_attendance_snapshot(session)
    outbound_payload = {
        key: value
        for key, value in snapshot.items()
        if key not in {"students_count", "course_records_count"}
    }

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                webhook_url,
                json=outbound_payload,
                headers={"Content-Type": "application/json"},
            )
    except httpx.TimeoutException as exc:
        logger.exception("Timed out sending attendance snapshot to n8n")
        raise AttendanceFinalizationError(
            "The notification workflow did not respond in time. Please try again."
        ) from exc
    except httpx.RequestError as exc:
        logger.exception("Could not reach the n8n attendance webhook")
        raise AttendanceFinalizationError(
            "Attendance data was not sent to the notification workflow. Please try again."
        ) from exc

    if not 200 <= response.status_code < 300:
        logger.error(
            "n8n rejected attendance batch %s with HTTP %s: %s",
            snapshot["batch_id"],
            response.status_code,
            response.text[:1000],
        )
        raise AttendanceFinalizationError(
            "Attendance data was not sent to the notification workflow. Please try again."
        )

    try:
        n8n_response = response.json()
    except ValueError:
        n8n_response = {}

    return {
        "batch_id": snapshot["batch_id"],
        "finalized_at": snapshot["finalized_at"],
        "students_processed": snapshot["students_count"],
        "course_records_sent": snapshot["course_records_count"],
        "duplicate": bool(n8n_response.get("duplicate", False)),
        "message": "The attendance snapshot was sent to the notification workflow.",
    }
