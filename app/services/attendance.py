import random
from datetime import datetime, date, timedelta
from typing import List, Optional, Dict
from sqlmodel import Session, select
from app.models import (
    User, Course, Attendance, CourseEnrollment,
    AttendanceStatus, AttendanceWarningLevel, WebhookEventType,
    CourseEnrollmentStatus, CourseSchedule, SystemSetting
)
from app.services.webhook_sender import (
    fire_webhook, create_webhook_log_sync
)
from app.schemas.webhook_payloads import (
    AttendanceAlertPayload, AttendanceMarkedPayload,
    WebhookEventType as SchemaWebhookEventType
)
from app.schemas import (
    AttendanceWarningLevel as SchemaAttendanceWarningLevel,
    AttendanceStatus as SchemaAttendanceStatus
)
import logging

logger = logging.getLogger(__name__)


def get_absence_count(session: Session, student_id: int, course_id: int) -> int:
    """Get the total number of absences for a student in a course"""
    return len(session.exec(
        select(Attendance)
        .where(Attendance.student_id == student_id)
        .where(Attendance.course_id == course_id)
        .where(Attendance.status == AttendanceStatus.ABSENT)
    ).all())

def get_total_sessions(course: Course) -> int:
    """Get the total sessions for a course based on its credits"""
    return {4: 12, 6: 18, 8: 24}.get(course.credits, 12)


def calculate_warning_level(absence_count: int, total_sessions: int) -> AttendanceWarningLevel:
    """Calculate warning level based on absence count and total sessions"""
    import math
    drop_threshold = math.ceil(total_sessions / 4) + 1
    
    if absence_count >= drop_threshold:
        return AttendanceWarningLevel.FINAL_WARNING
    elif absence_count >= drop_threshold - 1:
        return AttendanceWarningLevel.SECOND_WARNING
    elif absence_count >= 2:
        return AttendanceWarningLevel.FIRST_WARNING
    return AttendanceWarningLevel.NONE


def mark_attendance(
    session: Session,
    student_id: int,
    course_id: int,
    attendance_date: date,
    status: AttendanceStatus,
    notes: Optional[str] = None,
    marked_by: Optional[int] = None
) -> Optional[Attendance]:
    """Mark attendance for a student in a course on a specific date"""
    # Get the course to know total sessions
    course = session.get(Course, course_id)
    if not course:
        return None
        
    total_sessions = get_total_sessions(course)
    
    # Check if record exists
    existing = session.exec(
        select(Attendance)
        .where(Attendance.student_id == student_id)
        .where(Attendance.course_id == course_id)
        .where(Attendance.date == attendance_date)
    ).first()

    # Determine old absence count and old warning level
    old_absences = get_absence_count(session, student_id, course_id)
    old_warning_level = calculate_warning_level(old_absences, total_sessions)

    if existing:
        # If we are changing from ABSENT to PRESENT, absences decrease.
        # If from PRESENT to ABSENT, absences increase.
        if existing.status == AttendanceStatus.ABSENT and status == AttendanceStatus.PRESENT:
            new_absences = old_absences - 1
        elif existing.status == AttendanceStatus.PRESENT and status == AttendanceStatus.ABSENT:
            new_absences = old_absences + 1
        else:
            new_absences = old_absences

        new_warning_level = calculate_warning_level(new_absences, total_sessions)
        
        existing.status = status
        existing.warning_level = new_warning_level
        existing.notes = notes
        existing.marked_by = marked_by
        existing.marked_at = datetime.utcnow()
        session.add(existing)
        session.commit()
        session.refresh(existing)
        attendance = existing
    else:
        new_absences = old_absences + (1 if status == AttendanceStatus.ABSENT else 0)
        new_warning_level = calculate_warning_level(new_absences, total_sessions)

        attendance = Attendance(
            student_id=student_id,
            course_id=course_id,
            date=attendance_date,
            status=status,
            warning_level=new_warning_level,
            notes=notes,
            marked_by=marked_by,
            marked_at=datetime.utcnow()
        )
        session.add(attendance)
        session.commit()
        session.refresh(attendance)

    # Handle Enrollment Status Updates
    enrollment = session.exec(
        select(CourseEnrollment)
        .where(CourseEnrollment.student_id == student_id)
        .where(CourseEnrollment.course_id == course_id)
    ).first()
    
    if enrollment:
        if new_warning_level == AttendanceWarningLevel.FINAL_WARNING and enrollment.status != CourseEnrollmentStatus.DROPPED:
            enrollment.status = CourseEnrollmentStatus.DROPPED
            session.add(enrollment)
            session.commit()
        elif new_warning_level != AttendanceWarningLevel.FINAL_WARNING and enrollment.status == CourseEnrollmentStatus.DROPPED:
            enrollment.status = CourseEnrollmentStatus.ACTIVE
            session.add(enrollment)
            session.commit()

    # Fire attendance marked webhook
    student = session.get(User, student_id)
    course = session.get(Course, course_id)
    if student and course:
        payload = AttendanceMarkedPayload(
            event_type=SchemaWebhookEventType.ATTENDANCE_MARKED,
            student_id=student.student_id,
            student_name=student.full_name,
            course_code=course.code,
            course_name=course.name,
            date=attendance_date,
            status=status.value,
            warning_level=attendance.warning_level.value,
            marked_by="System"
        )
        create_webhook_log_sync(
            session,
            WebhookEventType.ATTENDANCE_MARKED,
            payload,
            student_id,
            course_id
        )

        # Fire attendance alert if warning level changed
        if old_warning_level != new_warning_level:
            fire_attendance_alert(session, student, course, attendance, new_warning_level, new_absences)

    return attendance


def fire_attendance_alert(
    session: Session,
    student: User,
    course: Course,
    attendance: Attendance,
    warning_level: AttendanceWarningLevel,
    absence_count: int
):
    """Fire attendance alert webhook for warning levels"""

    payload = AttendanceAlertPayload(
        event_type=SchemaWebhookEventType.ATTENDANCE_ALERT,
        student_id=student.student_id,
        student_name=student.full_name,
        course_code=course.code,
        course_name=course.name,
        date=attendance.date,
        status=attendance.status.value,
        warning_level=SchemaAttendanceWarningLevel(warning_level.value),
        total_absences=absence_count
    )
    create_webhook_log_sync(
        session,
        WebhookEventType.ATTENDANCE_ALERT,
        payload,
        student.id,
        course.id
    )
    logger.info(f"Attendance alert fired: {student.student_id} - {course.code} - {warning_level.value} ({absence_count} absences)")


def get_students_for_course_on_date(
    session: Session,
    course_id: int,
    attendance_date: date
) -> List[User]:
    """Get all enrolled students for a course on a specific date"""
    enrollments = session.exec(
        select(CourseEnrollment)
        .where(CourseEnrollment.course_id == course_id)
        .where(CourseEnrollment.status == CourseEnrollmentStatus.ACTIVE)
    ).all()

    student_ids = [e.student_id for e in enrollments]
    if not student_ids:
        return []

    students = session.exec(
        select(User)
        .where(User.id.in_(student_ids))
        .where(User.is_active == True)
    ).all()
    return students


def get_courses_with_sessions_on_date(session: Session, attendance_date: date) -> List[Course]:
    """Get courses that have sessions on a given date based on CourseSchedule"""
    if attendance_date.weekday() in (4, 5):  # Friday or Saturday
        return []
        
    # Get semester start date
    setting = session.exec(select(SystemSetting).where(SystemSetting.key == "semester_start_date")).first()
    if not setting:
        return []
        
    semester_start_date = datetime.strptime(setting.value, "%Y-%m-%d").date()
    
    # Calculate week number (1-12)
    days_diff = (attendance_date - semester_start_date).days
    if days_diff < 0:
        return []
        
    week_number = (days_diff // 7) + 1
    if week_number > 12:
        return []
        
    weekday = attendance_date.weekday()
    
    # Find scheduled courses
    schedules = session.exec(
        select(CourseSchedule)
        .where(CourseSchedule.week_number == week_number)
        .where(CourseSchedule.weekday == weekday)
    ).all()
    
    if not schedules:
        return []
        
    course_ids = [s.course_id for s in schedules]
    return session.exec(
        select(Course)
        .where(Course.id.in_(course_ids))
        .where(Course.is_active == True)
    ).all()


def simulate_day_end_attendance(
    session: Session,
    attendance_date: Optional[date] = None,
    absence_rate: float = 0.15
) -> Dict:
    """Simulate end-of-day attendance marking for all courses"""
    if attendance_date is None:
        attendance_date = date.today()

    # Skip weekends (Friday/Saturday)
    if attendance_date.weekday() in (4, 5):
        return {
            "date": attendance_date.isoformat(),
            "message": "Weekend - no sessions scheduled",
            "courses_processed": 0,
            "students_marked": 0,
            "absences_created": 0,
            "alerts_fired": 0
        }

    courses = get_courses_with_sessions_on_date(session, attendance_date)
    results = {
        "date": attendance_date.isoformat(),
        "courses_processed": 0,
        "students_marked": 0,
        "absences_created": 0,
        "alerts_fired": 0,
        "details": []
    }

    for course in courses:
        students = get_students_for_course_on_date(session, course.id, attendance_date)
        course_absences = 0
        course_alerts = 0

        for student in students:
            # Randomly mark absent based on absence rate
            status = AttendanceStatus.ABSENT if random.random() < absence_rate else AttendanceStatus.PRESENT

            attendance = mark_attendance(
                session,
                student.id,
                course.id,
                attendance_date,
                status,
                marked_by=0  # 0 = system
            )

            results["students_marked"] += 1
            if status == AttendanceStatus.ABSENT:
                course_absences += 1
                results["absences_created"] += 1
                if attendance and attendance.warning_level != AttendanceWarningLevel.NONE:
                    course_alerts += 1
                    results["alerts_fired"] += 1

        results["courses_processed"] += 1
        results["details"].append({
            "course_code": course.code,
            "course_name": course.name,
            "students_count": len(students),
            "absences": course_absences,
            "alerts": course_alerts
        })

    logger.info(f"Day-end attendance simulation for {attendance_date}: {results['absences_created']} absences, {results['alerts_fired']} alerts")
    return results


def get_student_attendance_summary(session: Session, student_id: int) -> dict:
    """Get attendance summary for a student"""
    attendances = session.exec(
        select(Attendance)
        .where(Attendance.student_id == student_id)
        .order_by(Attendance.date.desc())
    ).all()

    by_course = {}
    for a in attendances:
        course = session.get(Course, a.course_id)
        if course:
            key = course.code
            if key not in by_course:
                by_course[key] = {
                    "course_name": course.name,
                    "total": 0,
                    "present": 0,
                    "absent": 0,
                    "warning_level": AttendanceWarningLevel.NONE
                }
            by_course[key]["total"] += 1
            by_course[key][a.status.value] += 1
            if a.warning_level.value > by_course[key]["warning_level"].value:
                by_course[key]["warning_level"] = a.warning_level

    return {
        "student_id": student_id,
        "by_course": by_course,
        "total_sessions": len(attendances)
    }