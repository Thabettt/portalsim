from datetime import datetime, date
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query, Body
from sqlmodel import Session, select, func
from sqlalchemy import delete as sqlalchemy_delete
from app.db import get_session
from app.models import (
    User, Course, CourseEnrollment, Attendance, Payment,
    Assessment, Internship, InternshipProgressReport, WebhookSetting, WebhookLog,
    SystemSetting, WebhookEventType, WebhookDeliveryStatus,
    PaymentStatus, InternshipStatus, ProgressReportStatus, AttendanceStatus,
    AttendanceWarningLevel, AssessmentType, UserRole
)
from app.schemas import (
    UserCreate, UserRead, CourseCreate, CourseRead,
    AttendanceCreate, AttendanceRead, PaymentCreate, PaymentRead,
    AssessmentCreate, AssessmentRead, InternshipCreate, InternshipRead,
    WebhookSettingCreate, WebhookSettingRead, WebhookSettingUpdate,
    WebhookLogRead, SystemStateResponse, SeedResponse,
    AttendanceMarkRequest, AttendanceBatchMarkRequest, AttendanceWarningBatchUpdateRequest, InternshipDecisionRequest,
    InternshipRevisionDecisionRequest, InternshipFinalStatusRequest,
    ProgressReportCreateRequest, ProgressReportDecisionRequest,
    AssessmentPublishRequest, PaginatedResponse
)
from app.services.attendance import (
    mark_attendance, simulate_day_end_attendance,
    get_student_attendance_summary, get_students_for_course_on_date,
    get_student_warning_report, update_student_warning_levels
)
from app.services.payments import (
    simulate_payment_reminders, get_student_payment_summary
)
from app.services.grades_internships import (
    publish_assessment_grade, simulate_deadline_check,
    update_internship_status, update_internship_revision_review, update_internship_final_status, get_student_grades_summary
)
from app.services.webhook_sender import deliver_webhook, get_webhook_logs
from app.services.n8n_attendance import (
    AttendanceFinalizationError,
    AttendanceFinalizationNotConfigured,
    send_attendance_snapshot,
)
from app.services.internship_admin import build_internship_admin_record, sort_internship_records
from app.services.internship_progress import (
    create_progress_report,
    list_approved_internships,
    list_all_internships,
    list_internship_progress_reports,
    list_pending_progress_reports,
    trigger_progress_report_accept_automation,
    trigger_progress_report_reject_automation,
    trigger_progress_report_submit_automation,
    update_progress_report_status,
)
# from app.config import get_settings as get_app_config  # Not used directly
import logging

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/admin", tags=["admin"])


@router.post("/seed", response_model=SeedResponse)
async def seed_database(session: Session = Depends(get_session)):
    """Wipe and reseed the database with demo data"""
    # Delete all data in reverse order of dependencies
    session.exec(sqlalchemy_delete(WebhookLog))
    session.exec(sqlalchemy_delete(Attendance))
    session.exec(sqlalchemy_delete(Payment))
    session.exec(sqlalchemy_delete(Assessment))
    session.exec(sqlalchemy_delete(InternshipProgressReport))
    session.exec(sqlalchemy_delete(Internship))
    session.exec(sqlalchemy_delete(CourseEnrollment))
    session.exec(sqlalchemy_delete(Course))
    session.exec(sqlalchemy_delete(User))
    session.exec(sqlalchemy_delete(WebhookSetting))
    session.exec(sqlalchemy_delete(SystemSetting))
    session.commit()

    # Import and run seed
    from seed import seed_database
    result = await seed_database(session)
    return SeedResponse(**result)


@router.post("/reset")
async def reset_database(session: Session = Depends(get_session)):
    """Wipe database to empty state"""
    session.exec(sqlalchemy_delete(WebhookLog))
    session.exec(sqlalchemy_delete(Attendance))
    session.exec(sqlalchemy_delete(Payment))
    session.exec(sqlalchemy_delete(Assessment))
    session.exec(sqlalchemy_delete(InternshipProgressReport))
    session.exec(sqlalchemy_delete(Internship))
    session.exec(sqlalchemy_delete(CourseEnrollment))
    session.exec(sqlalchemy_delete(Course))
    session.exec(sqlalchemy_delete(User))
    session.exec(sqlalchemy_delete(WebhookSetting))
    session.exec(sqlalchemy_delete(SystemSetting))
    session.commit()
    return {"message": "Database reset to empty state"}


@router.get("/state", response_model=SystemStateResponse)
async def get_system_state(session: Session = Depends(get_session)):
    """Get current system state summary"""
    webhook_setting = session.exec(
        select(WebhookSetting).where(WebhookSetting.is_active == True)
    ).first()

    return SystemStateResponse(
        users=session.exec(select(func.count(User.id))).one(),
        courses=session.exec(select(func.count(Course.id))).one(),
        enrollments=session.exec(select(func.count(CourseEnrollment.id))).one(),
        attendances=session.exec(select(func.count(Attendance.id))).one(),
        payments=session.exec(select(func.count(Payment.id))).one(),
        assessments=session.exec(select(func.count(Assessment.id))).one(),
        internships=session.exec(select(func.count(Internship.id))).one(),
        webhook_logs=session.exec(select(func.count(WebhookLog.id))).one(),
        webhook_settings=session.exec(select(func.count(WebhookSetting.id))).one(),
        webhook_target_url=webhook_setting.webhook_target_url if webhook_setting else None,
        webhook_secret_configured=bool(webhook_setting and webhook_setting.shared_secret)
    )


@router.post("/simulate/day-end")
async def simulate_day_end(
    absence_rate: float = Query(0.15, ge=0, le=1),
    session: Session = Depends(get_session)
):
    """Fast-forward attendance simulation for current day"""
    result = simulate_day_end_attendance(session, absence_rate=absence_rate)
    return result


@router.post("/simulate/payment-reminders")
async def simulate_payment_reminders_endpoint(
    days_ahead: int = Query(7, ge=1, le=30),
    session: Session = Depends(get_session)
):
    """Fast-forward payment reminders check"""
    result = simulate_payment_reminders(session, days_ahead=days_ahead)
    return result


@router.post("/simulate/deadline-check")
async def simulate_deadline_check_endpoint(
    days_ahead: int = Query(7, ge=1, le=30),
    session: Session = Depends(get_session)
):
    """Fast-forward deadline reminders check"""
    result = simulate_deadline_check(session, days_ahead=days_ahead)
    return result


@router.post("/attendance/mark", response_model=AttendanceRead)
async def mark_attendance_manual(
    request: AttendanceMarkRequest,
    session: Session = Depends(get_session)
):
    """Manually mark attendance for a student"""
    attendance = mark_attendance(
        session=session,
        student_id=request.student_id,
        course_id=request.course_id,
        attendance_date=request.date,
        status=request.status,
        notes=request.notes
    )
    if not attendance:
        raise HTTPException(404, "Student or course not found")
    return attendance


@router.get("/courses/{course_id}/attendance-by-date")
async def get_course_attendance_by_date(
    course_id: int,
    date: date,
    session: Session = Depends(get_session)
):
    """Get all enrolled students for a course and their attendance status on a specific date"""
    course = session.get(Course, course_id)
    if not course:
        raise HTTPException(404, "Course not found")

    # Fetch all enrollments for this course (both active and dropped)
    enrollments = session.exec(
        select(CourseEnrollment, User)
        .join(User, CourseEnrollment.student_id == User.id)
        .where(CourseEnrollment.course_id == course_id)
    ).all()
    # Fetch existing attendance records for these students on this date
    attendances = session.exec(
        select(Attendance)
        .where(Attendance.course_id == course_id)
        .where(Attendance.date == date)
    ).all()
    
    attendance_map = {a.student_id: a.status for a in attendances}
    
    result = []
    for enrollment, student in enrollments:
        result.append({
            "student_id": student.id,
            "student_string_id": student.student_id,
            "full_name": student.full_name,
            "status": attendance_map.get(student.id, None),
            "enrollment_status": enrollment.status.value if hasattr(enrollment.status, 'value') else enrollment.status
        })
        
    return result


@router.post("/attendance/batch-mark")
async def batch_mark_attendance(
    request: AttendanceBatchMarkRequest,
    session: Session = Depends(get_session)
):
    """Batch mark attendance for a course on a specific date"""
    course = session.get(Course, request.course_id)
    if not course:
        raise HTTPException(404, "Course not found")
        
    for record in request.records:
        mark_attendance(
            session=session,
            student_id=record.student_id,
            course_id=request.course_id,
            attendance_date=request.date,
            status=record.status
        )
        
    return {"message": f"Successfully marked attendance for {len(request.records)} students"}


@router.get("/students/{student_id}/attendance-warnings")
async def get_attendance_warnings(
    student_id: int,
    include_good: bool = Query(False),
    session: Session = Depends(get_session)
):
    """Get a student's latest warning state, hiding Level 0 by default."""
    student = session.get(User, student_id)
    if not student or student.role != UserRole.STUDENT:
        raise HTTPException(404, "Student not found")

    return {
        "student": {
            "id": student.id,
            "student_id": student.student_id,
            "name": student.full_name,
        },
        "warnings": get_student_warning_report(session, student_id, include_good),
    }


@router.put("/students/{student_id}/attendance-warnings")
async def update_attendance_warnings(
    student_id: int,
    request: AttendanceWarningBatchUpdateRequest,
    session: Session = Depends(get_session)
):
    """Save TA warning corrections and emit correction notifications."""
    student = session.get(User, student_id)
    if not student or student.role != UserRole.STUDENT:
        raise HTTPException(404, "Student not found")

    try:
        updated = update_student_warning_levels(
            session,
            student,
            [change.model_dump() for change in request.changes],
        )
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc

    return {
        "message": f"Saved {len(updated)} warning change(s)",
        "updated": updated,
        "warnings": get_student_warning_report(session, student_id),
    }


@router.post("/internships/{internship_id}/decision", response_model=InternshipRead)
async def decide_internship(
    internship_id: int,
    request: InternshipDecisionRequest,
    session: Session = Depends(get_session)
):
    """Approve or reject an internship application"""
    if request.status not in {InternshipStatus.APPROVED, InternshipStatus.REJECTED}:
        raise HTTPException(400, "An internship decision must be approved or rejected")
    result = update_internship_status(
        session=session,
        internship_id=internship_id,
        new_status=request.status,
        rejection_reason=request.rejection_reason
    )
    if not result:
        raise HTTPException(404, "Internship not found")
    internship, webhook_log = result
    if webhook_log:
        await deliver_webhook(session, webhook_log)
    return internship


@router.post("/internships/revision-review/{review_type}")
async def decide_internship_revision_review(
    review_type: str,
    request: InternshipRevisionDecisionRequest,
    session: Session = Depends(get_session),
):
    """Update internship revision review status for the career center or supervisor."""
    try:
        internship = await update_internship_revision_review(
            session=session,
            student_email=request.student_email,
            internship_title=request.internship_title,
            review_type=review_type,
            new_status=request.new_status,
            reason=request.reason,
        )
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc

    if not internship:
        raise HTTPException(404, "Internship not found")

    status_field = "career_center_review_status" if review_type == "career_center" else "supervisor_review_status"
    return {
        "status": getattr(internship, status_field),
        "internship": internship,
    }


@router.post("/internships/{internship_id}/final-status", response_model=InternshipRead)
async def fulfill_internship_final_status(
    internship_id: int,
    request: InternshipFinalStatusRequest,
    session: Session = Depends(get_session),
):
    """Mark an internship as fulfilled from the academic or career center perspective."""
    try:
        internship = await update_internship_final_status(session, internship_id, request.review_type)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    if not internship:
        raise HTTPException(404, "Internship not found")
    return internship


@router.get("/internships/approved")
async def get_approved_internships(session: Session = Depends(get_session)):
    """List internships that can submit bi-weekly progress reports."""
    return list_approved_internships(session)


@router.get("/internships/all")
async def get_all_internships(session: Session = Depends(get_session)):
    """List all internships for all students regardless of status."""
    return list_all_internships(session)


@router.post("/internships/{internship_id}/progress-reports")
async def submit_progress_report(
    internship_id: int,
    request: ProgressReportCreateRequest,
    session: Session = Depends(get_session),
):
    logger.info(f"Incoming progress report submit request: {internship_id} - {request}")
    """Create a numbered bi-weekly report for an approved internship."""
    try:
        report = create_progress_report(session, internship_id, request.report_number, request.summary)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    if not report:
        raise HTTPException(404, "Internship not found")
        
    await trigger_progress_report_submit_automation(report)
    
    return report


@router.get("/internships/{internship_id}/progress-reports")
async def get_internship_progress_reports(
    internship_id: int,
    session: Session = Depends(get_session),
):
    """List all submitted progress reports for an internship."""
    return list_internship_progress_reports(session, internship_id)


@router.get("/internship-progress-reports/pending")
async def get_pending_progress_reports(session: Session = Depends(get_session)):
    """List submitted bi-weekly reports awaiting approval or rejection."""
    return list_pending_progress_reports(session)


@router.post("/internship-progress-reports/{report_id}/decision")
async def decide_progress_report(
    report_id: int,
    request: ProgressReportDecisionRequest,
    session: Session = Depends(get_session),
):
    logger.info(f"Incoming progress report decision request: {report_id} - {request}")
    """Approve or reject a bi-weekly report and queue its webhook event."""
    try:
        result = update_progress_report_status(
            session,
            report_id,
            request.status,
            request.review_notes,
        )
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    if not result:
        raise HTTPException(404, "Progress report not found")
    report, webhook_log = result
    await deliver_webhook(session, webhook_log)
    return report


@router.post("/assessments/{assessment_id}/publish", response_model=AssessmentRead)
async def publish_assessment(
    assessment_id: int,
    request: AssessmentPublishRequest,
    session: Session = Depends(get_session)
):
    """Publish an assessment grade"""
    assessment = publish_assessment_grade(session, assessment_id, request.score)
    if not assessment:
        raise HTTPException(404, "Assessment not found")
    return assessment


@router.get("/webhook-logs", response_model=PaginatedResponse)
async def list_webhook_logs(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    event_type: Optional[WebhookEventType] = None,
    status: Optional[WebhookDeliveryStatus] = None,
    student_id: Optional[int] = None,
    session: Session = Depends(get_session)
):
    """Get paginated webhook logs"""
    result = get_webhook_logs(
        session,
        page=page,
        page_size=page_size,
        event_type=event_type,
        status=status,
        student_id=student_id
    )
    return PaginatedResponse(
        items=result["logs"],
        total=result["total"],
        page=result["page"],
        page_size=result["page_size"],
        total_pages=result["pages"]
    )


@router.post("/webhook-logs/{log_id}/retry")
async def retry_webhook(
    log_id: int,
    session: Session = Depends(get_session)
):
    """Immediately deliver a pending or previously failed webhook."""
    webhook_log = session.get(WebhookLog, log_id)
    if not webhook_log:
        raise HTTPException(404, "Webhook log not found")

    if webhook_log.status not in [
        WebhookDeliveryStatus.PENDING,
        WebhookDeliveryStatus.FAILED,
        WebhookDeliveryStatus.RETRYING,
    ]:
        raise HTTPException(400, "Webhook is not in a retryable state")

    webhook_log.status = WebhookDeliveryStatus.PENDING
    webhook_log.attempt_number = 0
    webhook_log.next_retry_at = datetime.utcnow()
    webhook_log.error_message = None
    session.add(webhook_log)
    session.commit()

    # Deliver this exact event immediately, regardless of unrelated queued logs.
    await deliver_webhook(session, webhook_log)

    return {"message": "Webhook retry initiated", "log_id": log_id}


@router.get("/webhook-logs/stats")
async def get_webhook_log_stats(session: Session = Depends(get_session)):
    """Get webhook delivery statistics"""
    total = session.exec(select(func.count(WebhookLog.id))).one()
    sent = session.exec(
        select(func.count(WebhookLog.id))
        .where(WebhookLog.status == WebhookDeliveryStatus.SENT)
    ).one()
    failed = session.exec(
        select(func.count(WebhookLog.id))
        .where(WebhookLog.status == WebhookDeliveryStatus.FAILED)
    ).one()
    pending = session.exec(
        select(func.count(WebhookLog.id))
        .where(WebhookLog.status.in_([WebhookDeliveryStatus.PENDING, WebhookDeliveryStatus.RETRYING]))
    ).one()

    by_event = session.exec(
        select(WebhookLog.event_type, func.count(WebhookLog.id))
        .group_by(WebhookLog.event_type)
    ).all()

    return {
        "total": total,
        "sent": sent,
        "failed": failed,
        "pending": pending,
        "success_rate": round(sent / total * 100, 2) if total > 0 else 0,
        "by_event_type": {event.value: count for event, count in by_event}
    }


@router.get("/settings", response_model=WebhookSettingRead)
def get_webhook_settings(session: Session = Depends(get_session)):
    """Get current webhook settings"""
    webhook_setting = session.exec(
        select(WebhookSetting).where(WebhookSetting.is_active == True)
    ).first()

    if not webhook_setting:
        return WebhookSettingRead(
            id=0,
            webhook_target_url="",
            shared_secret="dev-secret-change-in-production",
            is_active=False,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )

    return webhook_setting


@router.put("/settings", response_model=WebhookSettingRead)
async def update_settings(
    request: WebhookSettingUpdate,
    session: Session = Depends(get_session)
):
    """Update webhook settings"""
    webhook_setting = session.exec(
        select(WebhookSetting).where(WebhookSetting.is_active == True)
    ).first()

    if not webhook_setting:
        webhook_setting = WebhookSetting(
            webhook_target_url=request.webhook_target_url or "",
            shared_secret=request.shared_secret or "dev-secret-change-in-production",
            is_active=request.is_active if request.is_active is not None else True
        )
        session.add(webhook_setting)
    else:
        if request.webhook_target_url is not None:
            webhook_setting.webhook_target_url = request.webhook_target_url
        if request.shared_secret is not None:
            webhook_setting.shared_secret = request.shared_secret
        if request.is_active is not None:
            webhook_setting.is_active = request.is_active
        webhook_setting.updated_at = datetime.utcnow()
        session.add(webhook_setting)

    session.commit()
    session.refresh(webhook_setting)
    return webhook_setting


@router.get("/students/{student_id}/summary")
async def get_student_summary(
    student_id: int,
    session: Session = Depends(get_session)
):
    """Get comprehensive summary for a student"""
    student = session.get(User, student_id)
    if not student:
        raise HTTPException(404, "Student not found")

    attendance = get_student_attendance_summary(session, student_id)
    payments = get_student_payment_summary(session, student_id)
    grades = get_student_grades_summary(session, student_id)

    return {
        "student": {
            "id": student.id,
            "student_id": student.student_id,
            "name": student.full_name,
            "email": student.email,
            "role": student.role.value
        },
        "attendance": attendance,
        "payments": payments,
        "grades": grades
    }


@router.get("/courses/{course_code}/attendance")
async def get_course_attendance(
    course_code: str,
    session: Session = Depends(get_session)
):
    """Get attendance summary for a course"""
    course = session.exec(
        select(Course).where(Course.code == course_code)
    ).first()

    if not course:
        raise HTTPException(404, "Course not found")

    attendances = session.exec(
        select(Attendance).where(Attendance.course_id == course.id)
        .order_by(Attendance.date.desc())
    ).all()

    by_student = {}
    for a in attendances:
        student = session.get(User, a.student_id)
        if student:
            sid = student.student_id
            if sid not in by_student:
                by_student[sid] = {
                    "student_name": student.full_name,
                    "total": 0,
                    "present": 0,
                    "absent": 0,
                    "warning_level": a.warning_level # First seen is most recent due to order_by desc
                }
            by_student[sid]["total"] += 1
            by_student[sid][a.status.value] += 1

    return {
        "course": {
            "code": course.code,
            "name": course.name,
            "semester": course.semester
        },
        "students": by_student
    }


@router.get("/scheduler/jobs")
async def get_scheduler_jobs():
    """Get status of scheduled jobs"""
    from app.scheduler import get_job_status
    return get_job_status()


@router.post("/scheduler/jobs/{job_id}/run")
async def run_scheduler_job_now(job_id: str):
    """Manually trigger a scheduled job"""
    from app.scheduler import run_job_now
    return run_job_now(job_id)


@router.get("/students", response_model=List[UserRead])
async def list_students(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    session: Session = Depends(get_session)
):
    """List all students"""
    students = session.exec(
        select(User)
        .where(User.role == UserRole.STUDENT)
        .order_by(User.student_id)
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()
    return students


@router.get("/courses", response_model=List[CourseRead])
async def list_courses(
    session: Session = Depends(get_session)
):
    """List all courses"""
    courses = session.exec(select(Course).order_by(Course.code)).all()
    return courses


@router.get("/payments/overdue")
async def list_overdue_payments(session: Session = Depends(get_session)):
    """List all overdue payments"""
    payments = session.exec(
        select(Payment, User)
        .join(User, Payment.student_id == User.id)
        .where(Payment.status == PaymentStatus.OVERDUE)
        .order_by(Payment.due_date)
    ).all()
    
    result = []
    for payment, user in payments:
        p_dict = payment.model_dump()
        p_dict["student_name"] = user.full_name
        p_dict["student_string_id"] = user.student_id
        result.append(p_dict)
        
    return result


@router.get("/internships/pending")
async def list_pending_internships(session: Session = Depends(get_session)):
    """List pending internship applications"""
    internships = session.exec(
        select(Internship, User)
        .join(User, Internship.student_id == User.id)
        .where(Internship.status == InternshipStatus.PENDING)
        .order_by(Internship.created_at)
    ).all()
    
    result = []
    for internship, user in internships:
        report_count = session.exec(
            select(func.count(InternshipProgressReport.id))
            .where(InternshipProgressReport.internship_id == internship.id)
        ).one()
        record = build_internship_admin_record(internship, user, report_count=report_count)
        record["proof_of_acceptance_uploaded_at"] = internship.proof_of_acceptance_uploaded_at.isoformat() if internship.proof_of_acceptance_uploaded_at else None
        record["evaluation_form_uploaded_at"] = internship.evaluation_form_uploaded_at.isoformat() if internship.evaluation_form_uploaded_at else None
        result.append(record)

    return sort_internship_records(result)


@router.post("/attendance/finalize-day")
async def finalize_attendance_day(session: Session = Depends(get_session)):
    """Send the complete saved attendance-warning snapshot to n8n."""
    try:
        return await send_attendance_snapshot(session)
    except AttendanceFinalizationNotConfigured as exc:
        raise HTTPException(503, str(exc)) from exc
    except AttendanceFinalizationError as exc:
        raise HTTPException(502, str(exc)) from exc
