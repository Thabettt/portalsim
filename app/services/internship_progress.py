import logging
from datetime import datetime
from typing import Optional

from sqlmodel import Session, func, select

from app.models import (
    Internship,
    InternshipProgressReport,
    InternshipStatus,
    ProgressReportStatus,
    User,
    WebhookEventType,
    WebhookLog,
)
from app.schemas.webhook_payloads import ProgressReportStatusUpdatePayload
from app.services.webhook_sender import create_webhook_log_sync


logger = logging.getLogger(__name__)

REPORT_ELIGIBLE_STATUSES = {
    InternshipStatus.APPROVED,
    InternshipStatus.IN_PROGRESS,
}


def _serialize_report(
    report: InternshipProgressReport,
    internship: Internship,
    student: User,
) -> dict:
    result = report.model_dump()
    result.update({
        "student_id": student.id,
        "internship_title": internship.position,
        "company_name": internship.company_name,
        "student_name": student.full_name,
        "student_string_id": student.student_id,
        "student_email": student.email,
    })
    return result


def list_approved_internships(session: Session) -> list[dict]:
    rows = session.exec(
        select(Internship, User)
        .join(User, Internship.student_id == User.id)
        .where(Internship.status.in_(tuple(REPORT_ELIGIBLE_STATUSES)))
        .order_by(User.full_name, Internship.position)
    ).all()

    result = []
    for internship, student in rows:
        latest_number = session.exec(
            select(func.max(InternshipProgressReport.report_number))
            .where(InternshipProgressReport.internship_id == internship.id)
        ).one()
        result.append({
            **internship.model_dump(),
            "internship_title": internship.position,
            "student_name": student.full_name,
            "student_string_id": student.student_id,
            "student_email": student.email,
            "next_progress_report_number": (latest_number or 0) + 1,
        })
    return result


def create_progress_report(
    session: Session,
    internship_id: int,
    summary: Optional[str] = None,
) -> Optional[tuple[dict, WebhookLog]]:
    internship = session.get(Internship, internship_id)
    if not internship:
        return None
    if internship.status not in REPORT_ELIGIBLE_STATUSES:
        raise ValueError("Progress reports can only be submitted for approved or in-progress internships.")

    latest_number = session.exec(
        select(func.max(InternshipProgressReport.report_number))
        .where(InternshipProgressReport.internship_id == internship.id)
    ).one()

    report = InternshipProgressReport(
        internship_id=internship.id,
        report_number=(latest_number or 0) + 1,
        summary=(summary or "").strip() or None,
        status=ProgressReportStatus.PENDING,
    )
    session.add(report)
    session.commit()
    session.refresh(report)

    student = session.get(User, internship.student_id)
    if not student:
        raise ValueError("The internship student could not be found.")
    return _serialize_report(report, internship, student)


def list_pending_progress_reports(session: Session) -> list[dict]:
    rows = session.exec(
        select(InternshipProgressReport, Internship, User)
        .join(Internship, InternshipProgressReport.internship_id == Internship.id)
        .join(User, Internship.student_id == User.id)
        .where(InternshipProgressReport.status == ProgressReportStatus.PENDING)
        .order_by(InternshipProgressReport.submitted_at)
    ).all()
    return [
        _serialize_report(report, internship, student)
        for report, internship, student in rows
    ]


def update_progress_report_status(
    session: Session,
    report_id: int,
    new_status: ProgressReportStatus,
    review_notes: Optional[str] = None,
) -> Optional[dict]:
    report = session.get(InternshipProgressReport, report_id)
    if not report:
        return None
    if report.status != ProgressReportStatus.PENDING:
        raise ValueError("This progress report has already been reviewed.")
    if new_status not in {ProgressReportStatus.APPROVED, ProgressReportStatus.REJECTED}:
        raise ValueError("A progress report decision must be approved or rejected.")
    if new_status == ProgressReportStatus.REJECTED and not (review_notes or "").strip():
        raise ValueError("A rejection reason is required.")

    internship = session.get(Internship, report.internship_id)
    if not internship:
        raise ValueError("The related internship could not be found.")
    student = session.get(User, internship.student_id)
    if not student:
        raise ValueError("The internship student could not be found.")

    report.status = new_status
    report.review_notes = (review_notes or "").strip() or None
    report.reviewed_at = datetime.utcnow()
    report.updated_at = datetime.utcnow()
    session.add(report)
    session.commit()
    session.refresh(report)

    payload = ProgressReportStatusUpdatePayload(
        event_type=WebhookEventType.PROGRESS_REPORT_STATUS_UPDATE,
        new_status=report.status.value,
        progress_report_number=report.report_number,
        student_email=student.email,
    )
    webhook_log = create_webhook_log_sync(
        session,
        WebhookEventType.PROGRESS_REPORT_STATUS_UPDATE,
        payload,
        student_id=student.id,
        internship_id=internship.id,
    )
    logger.info(
        "Progress report status webhook created: student=%s report=%s status=%s",
        student.student_id,
        report.report_number,
        report.status.value,
    )

    return _serialize_report(report, internship, student), webhook_log
