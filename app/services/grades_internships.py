from datetime import datetime, date, timedelta
from typing import List, Optional
from sqlmodel import Session, select, func
from app.models import (
    User, Course, Assessment, AssessmentType, Internship, InternshipStatus,
    WebhookEventType, WebhookSetting
)
from app.services.webhook_sender import create_webhook_log_sync, fire_webhook
from app.schemas.webhook_payloads import (
    GradePublishedPayload, DeadlineReminderPayload, InternshipStatusUpdatePayload,
    WebhookEventType as SchemaWebhookEventType
)
import logging

logger = logging.getLogger(__name__)


def create_assessment(
    session: Session,
    course_id: int,
    student_id: int,
    assessment_type: AssessmentType,
    title: str,
    max_score: float,
    weight: float = 1.0,
    due_date: Optional[date] = None
) -> Assessment:
    """Create a new assessment"""
    assessment = Assessment(
        course_id=course_id,
        student_id=student_id,
        assessment_type=assessment_type,
        title=title,
        max_score=max_score,
        weight=weight,
        due_date=due_date,
        is_published=False
    )
    session.add(assessment)
    session.commit()
    session.refresh(assessment)
    return assessment


def publish_assessment_grade(
    session: Session,
    assessment_id: int,
    score: float
) -> Optional[Assessment]:
    """Publish an assessment grade and fire webhook"""
    assessment = session.get(Assessment, assessment_id)
    if not assessment:
        return None

    if score > assessment.max_score:
        raise ValueError(f"Score {score} exceeds max score {assessment.max_score}")

    assessment.score = score
    assessment.is_published = True
    assessment.published_at = datetime.utcnow()
    assessment.updated_at = datetime.utcnow()
    session.add(assessment)
    session.commit()
    session.refresh(assessment)

    # Fire webhook
    fire_grade_published_webhook(session, assessment)

    return assessment


def fire_grade_published_webhook(session: Session, assessment: Assessment):
    """Fire grade published webhook"""
    student = session.get(User, assessment.student_id)
    course = session.get(Course, assessment.course_id)

    if not student or not course:
        logger.warning(f"Student or course not found for assessment {assessment.id}")
        return

    percentage = (assessment.score / assessment.max_score) * 100 if assessment.max_score > 0 else 0

    payload = GradePublishedPayload(
        event_type=SchemaWebhookEventType.GRADE_PUBLISHED,
        student_id=student.student_id,
        student_name=student.full_name,
        student_email=student.email,
        assessment_id=assessment.id,
        assessment_title=assessment.title,
        assessment_type=assessment.assessment_type.value,
        course_code=course.code,
        course_name=course.name,
        score=assessment.score,
        max_score=assessment.max_score,
        weight=assessment.weight,
        percentage=round(percentage, 2)
    )
    create_webhook_log_sync(
        session,
        WebhookEventType.GRADE_PUBLISHED,
        payload,
        student.id,
        course.id,
        assessment_id=assessment.id
    )
    logger.info(f"Grade published webhook fired: {student.student_id} - {course.code} - {assessment.title}")


def get_upcoming_deadlines(session: Session, days_ahead: int = 7) -> List[Assessment]:
    """Get assessments with due dates within days_ahead that are not yet due"""
    cutoff_date = date.today() + timedelta(days=days_ahead)
    return session.exec(
        select(Assessment)
        .where(Assessment.due_date.is_not(None))
        .where(Assessment.due_date >= date.today())
        .where(Assessment.due_date <= cutoff_date)
    ).all()


def fire_deadline_reminder(session: Session, assessment: Assessment, days_until_due: int):
    """Fire deadline reminder webhook"""
    student = session.get(User, assessment.student_id)
    course = session.get(Course, assessment.course_id)

    if not student or not course:
        return

    reminder_offsets = {
        1: "1_day_before",
        2: "2_days_before",
        3: "3_days_before",
        7: "1_week_before"
    }
    reminder_offset = reminder_offsets.get(days_until_due, f"{days_until_due}_days_before")

    # Convert due_date to datetime for due_at field
    due_at = datetime.combine(assessment.due_date, datetime.min.time())

    payload = DeadlineReminderPayload(
        event_type=SchemaWebhookEventType.DEADLINE_REMINDER,
        student_id=student.student_id,
        student_name=student.full_name,
        course_code=course.code,
        course_name=course.name,
        title=assessment.title,
        due_at=due_at,
        reminder_offset=reminder_offset
    )
    create_webhook_log_sync(
        session,
        WebhookEventType.DEADLINE_REMINDER,
        payload,
        student.id,
        course.id,
        assessment_id=assessment.id
    )
    logger.info(f"Deadline reminder fired: {student.student_id} - {assessment.title} - {days_until_due} days")


def simulate_deadline_check(session: Session, days_ahead: int = 7) -> dict:
    """Check for upcoming deadlines and fire reminders"""
    assessments = get_upcoming_deadlines(session, days_ahead)
    results = {
        "reminders_sent": 0,
        "checked": len(assessments),
        "errors": 0
    }

    for assessment in assessments:
        try:
            days_until = (assessment.due_date - date.today()).days
            if days_until in [1, 2, 3, 7]:  # Only send reminders at specific intervals
                fire_deadline_reminder(session, assessment, days_until)
                results["reminders_sent"] += 1
        except Exception as e:
            logger.error(f"Error sending deadline reminder for assessment {assessment.id}: {e}")
            results["errors"] += 1

    return results


def create_internship(
    session: Session,
    student_id: int,
    company_name: str,
    position: str,
    start_date: date,
    end_date: date,
    description: Optional[str] = None,
    supervisor_name: Optional[str] = None,
    supervisor_email: Optional[str] = None
) -> Internship:
    """Create a new internship application"""
    internship = Internship(
        student_id=student_id,
        company_name=company_name,
        position=position,
        start_date=start_date,
        end_date=end_date,
        description=description,
        supervisor_name=supervisor_name,
        supervisor_email=supervisor_email,
        status=InternshipStatus.PENDING
    )
    session.add(internship)
    session.commit()
    session.refresh(internship)
    return internship


def update_internship_status(
    session: Session,
    internship_id: int,
    new_status: InternshipStatus,
    approved_by: Optional[int] = None,
    rejection_reason: Optional[str] = None
) -> Optional[Internship]:
    """Update internship status and fire webhook"""
    internship = session.get(Internship, internship_id)
    if not internship:
        return None

    old_status = internship.status
    internship.status = new_status
    internship.updated_at = datetime.utcnow()

    if new_status == InternshipStatus.APPROVED:
        internship.approved_by = approved_by
        internship.approved_at = datetime.utcnow()
    elif new_status == InternshipStatus.REJECTED:
        internship.rejection_reason = rejection_reason

    session.add(internship)
    session.commit()
    session.refresh(internship)

    # Fire webhook
    fire_internship_status_webhook(session, internship, old_status)

    return internship


def fire_internship_status_webhook(
    session: Session,
    internship: Internship,
    old_status: InternshipStatus
):
    """Fire internship status update webhook"""
    student = session.get(User, internship.student_id)
    if not student:
        return

    approved_by_name = None
    if internship.approved_by:
        approver = session.get(User, internship.approved_by)
        approved_by_name = approver.full_name if approver else None

    payload = InternshipStatusUpdatePayload(
        event_type=SchemaWebhookEventType.INTERNSHIP_STATUS_UPDATE,
        student_id=student.student_id,
        student_name=student.full_name,
        student_email=student.email,
        internship_id=internship.id,
        company_name=internship.company_name,
        position=internship.position,
        previous_status=old_status.value,
        new_status=internship.status.value,
        approved_by=approved_by_name,
        approved_at=internship.approved_at,
        rejection_reason=internship.rejection_reason
    )
    create_webhook_log_sync(
        session,
        WebhookEventType.INTERNSHIP_STATUS_UPDATE,
        payload,
        student.id,
        internship_id=internship.id
    )
    logger.info(f"Internship status webhook fired: {student.student_id} - {internship.company_name} - {internship.status.value}")


def get_student_grades_summary(session: Session, student_id: int) -> dict:
    """Get grades summary for a student"""
    assessments = session.exec(
        select(Assessment).where(Assessment.student_id == student_id)
    ).all()

    published = [a for a in assessments if a.is_published]
    unpublished = [a for a in assessments if not a.is_published]

    return {
        "total_assessments": len(assessments),
        "published_count": len(published),
        "pending_count": len(unpublished),
        "assessments": [
            {
                "id": a.id,
                "title": a.title,
                "type": a.assessment_type.value,
                "course_id": a.course_id,
                "max_score": a.max_score,
                "score": a.score,
                "weight": a.weight,
                "is_published": a.is_published,
                "published_at": a.published_at.isoformat() if a.published_at else None,
                "due_date": a.due_date.isoformat() if a.due_date else None
            }
            for a in assessments
        ]
    }