import logging
from datetime import datetime
from typing import Optional

import httpx
from sqlmodel import Session, func, select

from app.config import get_settings
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
from app.services.internship_admin import build_internship_admin_record, sort_internship_records
from app.services.webhook_sender import create_webhook_log_sync


logger = logging.getLogger(__name__)
settings = get_settings()

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
        "supervisor_email": internship.supervisor_email,
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
        report_count = session.exec(
            select(func.count(InternshipProgressReport.id))
            .where(InternshipProgressReport.internship_id == internship.id)
        ).one()
        record = build_internship_admin_record(internship, student, report_count=report_count)
        record.update({
            "internship_title": internship.position,
            "proof_of_acceptance_uploaded_at": internship.proof_of_acceptance_uploaded_at.isoformat() if internship.proof_of_acceptance_uploaded_at else None,
            "evaluation_form_uploaded_at": internship.evaluation_form_uploaded_at.isoformat() if internship.evaluation_form_uploaded_at else None,
            "next_progress_report_number": (latest_number or 0) + 1,
        })
        result.append(record)
    return sort_internship_records(result)


def list_all_internships(session: Session) -> list[dict]:
    rows = session.exec(
        select(Internship, User)
        .join(User, Internship.student_id == User.id)
        .order_by(User.student_id, Internship.position)
    ).all()

    result = []
    for internship, student in rows:
        latest_number = session.exec(
            select(func.max(InternshipProgressReport.report_number))
            .where(InternshipProgressReport.internship_id == internship.id)
        ).one()
        report_count = session.exec(
            select(func.count(InternshipProgressReport.id))
            .where(InternshipProgressReport.internship_id == internship.id)
        ).one()
        waiting_count = session.exec(
            select(func.count(InternshipProgressReport.id))
            .where(InternshipProgressReport.internship_id == internship.id)
            .where(InternshipProgressReport.status == ProgressReportStatus.PENDING)
        ).one()
        accepted_count = session.exec(
            select(func.count(InternshipProgressReport.id))
            .where(InternshipProgressReport.internship_id == internship.id)
            .where(InternshipProgressReport.status == ProgressReportStatus.APPROVED)
        ).one()
        rejected_count = session.exec(
            select(func.count(InternshipProgressReport.id))
            .where(InternshipProgressReport.internship_id == internship.id)
            .where(InternshipProgressReport.status == ProgressReportStatus.REJECTED)
        ).one()

        record = build_internship_admin_record(internship, student, report_count=report_count)
        record.update({
            "internship_title": internship.position,
            "proof_of_acceptance_uploaded_at": internship.proof_of_acceptance_uploaded_at.isoformat() if internship.proof_of_acceptance_uploaded_at else None,
            "evaluation_form_uploaded_at": internship.evaluation_form_uploaded_at.isoformat() if internship.evaluation_form_uploaded_at else None,
            "next_progress_report_number": (latest_number or 0) + 1,
            "report_summary": {
                "total_reports": report_count,
                "waiting_for_review": waiting_count,
                "accepted": accepted_count,
                "rejected": rejected_count,
            }
        })
        result.append(record)
    return sort_internship_records(result)



def create_progress_report(
    session: Session,
    internship_id: int,
    report_number: int,
    summary: Optional[str] = None,
) -> Optional[tuple[dict, WebhookLog]]:
    internship = session.get(Internship, internship_id)
    if not internship:
        return None
    if internship.status not in REPORT_ELIGIBLE_STATUSES:
        raise ValueError("Progress reports can only be submitted for approved or in-progress internships.")

    existing_report = session.exec(
        select(InternshipProgressReport)
        .where(InternshipProgressReport.internship_id == internship.id)
        .where(InternshipProgressReport.report_number == report_number)
    ).first()

    if existing_report:
        raise ValueError("This report number has already been submitted for this internship.")

    report = InternshipProgressReport(
        internship_id=internship.id,
        report_number=report_number,
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


def list_internship_progress_reports(session: Session, internship_id: int) -> list[dict]:
    internship = session.get(Internship, internship_id)
    if not internship:
        return []
    student = session.get(User, internship.student_id)
    if not student:
        return []

    rows = session.exec(
        select(InternshipProgressReport)
        .where(InternshipProgressReport.internship_id == internship_id)
        .order_by(InternshipProgressReport.report_number)
    ).all()
    return [_serialize_report(report, internship, student) for report in rows]


async def _post_json(url: str, payload: dict) -> None:
    if not url:
        return
    async with httpx.AsyncClient(timeout=30.0) as client:
        await client.post(url, json=payload)


async def trigger_progress_report_accept_automation(session: Session, report: InternshipProgressReport, internship: Internship, student: User) -> None:
    pass


async def trigger_progress_report_reject_automation(session: Session, report: InternshipProgressReport, internship: Internship, student: User) -> None:
    payload = {
        "new_status": "rejected",
        "progress_report_number": str(report.report_number),
        "student_email": student.email,
    }
    await _post_json(settings.n8n_progress_report_reject_webhook_url.strip(), payload)


async def trigger_progress_report_submit_automation(report_dict: dict) -> None:
    payload = {
        "student_id": report_dict.get("student_string_id", ""),
        "studentId": report_dict.get("student_string_id", ""),
        "student_name": report_dict.get("student_name", ""),
        "studentName": report_dict.get("student_name", ""),
        "academic_supervisor_email": report_dict.get("supervisor_email", ""),
        "academicSupervisorEmail": report_dict.get("supervisor_email", ""),
        "progress_report_no": str(report_dict.get("report_number", "")),
        "progressReportNo": str(report_dict.get("report_number", "")),
    }
    await _post_json(settings.n8n_progress_reports_aggregated_report_webhook_url.strip(), payload)


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
