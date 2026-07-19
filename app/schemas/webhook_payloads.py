import uuid
from datetime import datetime, date
from typing import Optional, Literal, Union
from pydantic import BaseModel, Field
from app.models import WebhookEventType


class BaseWebhookPayload(BaseModel):
    """Base webhook payload with common fields"""
    event_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    event_type: WebhookEventType
    timestamp: datetime = Field(default_factory=datetime.utcnow)


# Payment Reminder Payload
class PaymentReminderPayload(BaseWebhookPayload):
    event_type: Literal[WebhookEventType.PAYMENT_REMINDER] = WebhookEventType.PAYMENT_REMINDER
    student_id: str
    student_name: str
    amount_due: float
    currency: str
    due_date: date
    reminder_type: str
    payment_type: str
    invoice_number: Optional[str] = None


# Internship Status Update Payload
class InternshipStatusUpdatePayload(BaseWebhookPayload):
    event_type: Literal[WebhookEventType.INTERNSHIP_STATUS_UPDATE] = WebhookEventType.INTERNSHIP_STATUS_UPDATE
    student_id: str
    student_name: str
    student_email: str
    internship_id: int
    company_name: str
    position: str
    previous_status: str
    new_status: str
    approved_by: Optional[str] = None
    approved_at: Optional[datetime] = None
    rejection_reason: Optional[str] = None


# Attendance Alert Payload
class AttendanceAlertPayload(BaseWebhookPayload):
    event_type: Literal[WebhookEventType.ATTENDANCE_ALERT] = WebhookEventType.ATTENDANCE_ALERT
    student_id: str
    student_name: str
    course_code: str
    course_name: str
    date: date
    status: str
    warning_level: str
    total_absences: int


# Grade Published Payload
class GradePublishedPayload(BaseWebhookPayload):
    event_type: Literal[WebhookEventType.GRADE_PUBLISHED] = WebhookEventType.GRADE_PUBLISHED
    student_id: str
    student_name: str
    course_code: str
    course_name: str
    assessment_type: str
    assessment_name: str
    score: float
    max_score: float
    percentage: float
    published_at: datetime


# Deadline Reminder Payload
class DeadlineReminderPayload(BaseWebhookPayload):
    event_type: Literal[WebhookEventType.DEADLINE_REMINDER] = WebhookEventType.DEADLINE_REMINDER
    student_id: str
    student_name: str
    course_code: str
    course_name: str
    title: str
    due_at: datetime
    reminder_offset: str


# Attendance Marked Payload (for manual marking)
class AttendanceMarkedPayload(BaseWebhookPayload):
    event_type: Literal[WebhookEventType.ATTENDANCE_MARKED] = WebhookEventType.ATTENDANCE_MARKED
    student_id: str
    student_name: str
    course_code: str
    course_name: str
    date: date
    status: str
    marked_by: str


# Payment Status Change Payload
class PaymentStatusChangePayload(BaseWebhookPayload):
    event_type: Literal[WebhookEventType.PAYMENT_STATUS_CHANGE] = WebhookEventType.PAYMENT_STATUS_CHANGE
    student_id: str
    student_name: str
    payment_type: str
    amount: float
    paid_amount: float
    due_date: date
    status: str
    invoice_number: Optional[str] = None


# Union type for all payloads
WebhookPayload = Union[
    PaymentReminderPayload,
    InternshipStatusUpdatePayload,
    AttendanceAlertPayload,
    GradePublishedPayload,
    DeadlineReminderPayload,
    AttendanceMarkedPayload,
    PaymentStatusChangePayload
]


# Example payloads for documentation
EXAMPLE_PAYLOADS = {
    "payment_reminder": {
        "event_id": "550e8400-e29b-41d4-a716-446655440000",
        "event_type": "payment_reminder",
        "timestamp": "2026-07-18T10:00:00Z",
        "student_id": "STU-2023-0142",
        "student_name": "Ahmed Hassan",
        "amount_due": 5000.00,
        "currency": "EGP",
        "due_date": "2026-07-24",
        "reminder_type": "7_days_before",
        "payment_type": "tuition",
        "invoice_number": "INV-2026-001"
    },
    "internship_status_update": {
        "event_id": "550e8400-e29b-41d4-a716-446655440001",
        "event_type": "internship_status_update",
        "timestamp": "2026-07-18T10:00:00Z",
        "student_id": "STU-2023-0142",
        "student_name": "Ahmed Hassan",
        "student_email": "ahmed.hassan@example.com",
        "internship_id": 1,
        "company_name": "Tech Corp",
        "position": "Software Engineering Intern",
        "previous_status": "PENDING",
        "new_status": "APPROVED",
        "approved_by": "Dr. Sarah Admin",
        "approved_at": "2026-07-18T10:05:00Z",
        "rejection_reason": None
    },
    "attendance_alert": {
        "event_id": "550e8400-e29b-41d4-a716-446655440002",
        "event_type": "attendance_alert",
        "timestamp": "2026-07-18T10:00:00Z",
        "student_id": "STU-2023-0142",
        "student_name": "Ahmed Hassan",
        "course_code": "CS-301",
        "course_name": "Data Structures and Algorithms",
        "date": "2026-07-17",
        "status": "ABSENT",
        "warning_level": "First Warning",
        "total_absences": 3
    },
    "grade_published": {
        "event_id": "550e8400-e29b-41d4-a716-446655440003",
        "event_type": "grade_published",
        "timestamp": "2026-07-18T10:00:00Z",
        "student_id": "STU-2023-0142",
        "student_name": "Ahmed Hassan",
        "course_code": "CS-301",
        "course_name": "Data Structures and Algorithms",
        "assessment_type": "Midterm",
        "assessment_name": "Midterm Exam",
        "score": 85.0,
        "max_score": 100.0,
        "percentage": 85.0,
        "published_at": "2026-07-18T10:00:00Z"
    },
    "deadline_reminder": {
        "event_id": "550e8400-e29b-41d4-a716-446655440004",
        "event_type": "deadline_reminder",
        "timestamp": "2026-07-18T10:00:00Z",
        "student_id": "STU-2023-0142",
        "student_name": "Ahmed Hassan",
        "course_code": "CS-301",
        "course_name": "Data Structures and Algorithms",
        "title": "Project 2 submission",
        "due_at": "2026-07-25T23:59:00Z",
        "reminder_offset": "3_days_before"
    }
}