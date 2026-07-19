from datetime import datetime, date
from typing import Optional, List, Dict, Any, Union
from pydantic import BaseModel, Field, EmailStr
from enum import Enum
import uuid


# ===== Enums =====
class UserRole(str, Enum):
    STUDENT = "student"
    ADMIN = "admin"
    INSTRUCTOR = "instructor"


class AttendanceStatus(str, Enum):
    PRESENT = "present"
    ABSENT = "absent"


class AttendanceWarningLevel(str, Enum):
    NONE = "none"
    FIRST_WARNING = "first_warning"
    SECOND_WARNING = "second_warning"
    FINAL_WARNING = "final_warning"


class PaymentStatus(str, Enum):
    PENDING = "pending"
    PAID = "paid"
    OVERDUE = "overdue"
    PARTIAL = "partial"
    WAIVED = "waived"


class PaymentType(str, Enum):
    TUITION = "tuition"
    LAB_FEE = "lab_fee"
    LIBRARY_FEE = "library_fee"
    EXAM_FEE = "exam_fee"
    OTHER = "other"


class AssessmentType(str, Enum):
    QUIZ = "quiz"
    MIDTERM = "midterm"
    FINAL = "final"
    ASSIGNMENT = "assignment"
    PROJECT = "project"
    PARTICIPATION = "participation"


class InternshipStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"


class WebhookEventType(str, Enum):
    ATTENDANCE_ALERT = "attendance_alert"
    PAYMENT_REMINDER = "payment_reminder"
    DEADLINE_REMINDER = "deadline_reminder"
    GRADE_PUBLISHED = "grade_published"
    INTERNSHIP_STATUS_UPDATE = "internship_status_update"
    ATTENDANCE_MARKED = "attendance_marked"
    PAYMENT_STATUS_CHANGE = "payment_status_change"


class WebhookDeliveryStatus(str, Enum):
    PENDING = "pending"
    SENT = "sent"
    FAILED = "failed"
    RETRYING = "retrying"


# ===== Base Models =====
class UserBase(BaseModel):
    student_id: str = Field(..., max_length=50)
    email: EmailStr
    full_name: str = Field(..., max_length=150)
    role: UserRole = UserRole.STUDENT


class UserCreate(UserBase):
    pass


class UserUpdate(BaseModel):
    email: Optional[EmailStr] = None
    full_name: Optional[str] = Field(None, max_length=150)
    role: Optional[UserRole] = None
    is_active: Optional[bool] = None


class UserRead(UserBase):
    id: int
    is_active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class CourseBase(BaseModel):
    code: str = Field(..., max_length=20)
    name: str = Field(..., max_length=150)
    description: Optional[str] = Field(None, max_length=500)
    credits: int = Field(default=3, ge=1)
    semester: str = Field(..., max_length=20)
    instructor_id: Optional[int] = None
    is_active: bool = True


class CourseCreate(CourseBase):
    pass


class CourseUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=150)
    description: Optional[str] = Field(None, max_length=500)
    credits: Optional[int] = Field(None, ge=1)
    semester: Optional[str] = Field(None, max_length=20)
    instructor_id: Optional[int] = None
    is_active: Optional[bool] = None


class CourseRead(CourseBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True


class CourseEnrollmentCreate(BaseModel):
    student_id: int
    course_id: int


class CourseEnrollmentRead(BaseModel):
    id: int
    student_id: int
    course_id: int
    enrolled_at: datetime
    is_active: bool

    class Config:
        from_attributes = True


class AttendanceBase(BaseModel):
    student_id: int
    course_id: int
    date: date
    status: AttendanceStatus = AttendanceStatus.PRESENT
    notes: Optional[str] = Field(None, max_length=500)


class AttendanceCreate(AttendanceBase):
    pass


class AttendanceUpdate(BaseModel):
    status: Optional[AttendanceStatus] = None
    notes: Optional[str] = Field(None, max_length=500)
    warning_level: Optional[AttendanceWarningLevel] = None


class AttendanceRead(AttendanceBase):
    id: int
    warning_level: AttendanceWarningLevel
    marked_by: Optional[int]
    marked_at: datetime
    created_at: datetime

    class Config:
        from_attributes = True


class PaymentBase(BaseModel):
    student_id: int
    payment_type: PaymentType
    amount: float = Field(..., gt=0)
    due_date: date
    description: Optional[str] = Field(None, max_length=500)
    invoice_number: Optional[str] = Field(None, max_length=50)


class PaymentCreate(PaymentBase):
    pass


class PaymentUpdate(BaseModel):
    status: Optional[PaymentStatus] = None
    paid_amount: Optional[float] = Field(None, ge=0)
    description: Optional[str] = Field(None, max_length=500)


class PaymentRead(PaymentBase):
    id: int
    status: PaymentStatus
    paid_amount: float
    paid_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class AssessmentBase(BaseModel):
    course_id: int
    student_id: int
    assessment_type: AssessmentType
    title: str = Field(..., max_length=200)
    max_score: float = Field(..., gt=0)
    weight: float = Field(default=1.0, gt=0)
    due_date: Optional[date] = None


class AssessmentCreate(AssessmentBase):
    pass


class AssessmentUpdate(BaseModel):
    score: Optional[float] = Field(None, ge=0)
    max_score: Optional[float] = Field(None, gt=0)
    weight: Optional[float] = Field(None, gt=0)
    is_published: Optional[bool] = None
    due_date: Optional[date] = None


class AssessmentRead(AssessmentBase):
    id: int
    score: Optional[float]
    is_published: bool
    published_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class InternshipBase(BaseModel):
    student_id: int
    company_name: str = Field(..., max_length=200)
    position: str = Field(..., max_length=150)
    start_date: date
    end_date: date
    description: Optional[str] = Field(None, max_length=1000)
    supervisor_name: Optional[str] = Field(None, max_length=150)
    supervisor_email: Optional[EmailStr] = None


class InternshipCreate(InternshipBase):
    pass


class InternshipUpdate(BaseModel):
    status: Optional[InternshipStatus] = None
    description: Optional[str] = Field(None, max_length=1000)
    supervisor_name: Optional[str] = Field(None, max_length=150)
    supervisor_email: Optional[EmailStr] = None
    rejection_reason: Optional[str] = Field(None, max_length=500)


class InternshipRead(InternshipBase):
    id: int
    status: InternshipStatus
    approved_by: Optional[int]
    approved_at: Optional[datetime]
    rejection_reason: Optional[str]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ===== Webhook Schemas =====
class WebhookSettingBase(BaseModel):
    webhook_target_url: str = Field(..., max_length=500)
    shared_secret: str = Field(..., max_length=255)


class WebhookSettingCreate(WebhookSettingBase):
    pass


class WebhookSettingUpdate(BaseModel):
    webhook_target_url: Optional[str] = Field(None, max_length=500)
    shared_secret: Optional[str] = Field(None, max_length=255)
    is_active: Optional[bool] = None


class WebhookSettingRead(WebhookSettingBase):
    id: int
    is_active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class WebhookLogRead(BaseModel):
    id: int
    event_type: WebhookEventType
    target_url: str
    payload: str
    status: WebhookDeliveryStatus
    status_code: Optional[int]
    response_body: Optional[str]
    error_message: Optional[str]
    attempt_number: int
    max_retries: int
    next_retry_at: Optional[datetime]
    created_at: datetime
    sent_at: Optional[datetime]
    completed_at: Optional[datetime]
    student_id: Optional[int]
    course_id: Optional[int]
    payment_id: Optional[int]
    assessment_id: Optional[int]
    internship_id: Optional[int]

    class Config:
        from_attributes = True


# ===== Webhook Payload Contracts =====
class WebhookBasePayload(BaseModel):
    event_type: WebhookEventType
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    event_id: str = Field(default_factory=lambda: str(uuid.uuid4()))


class AttendanceAlertPayload(WebhookBasePayload):
    event_type: WebhookEventType = WebhookEventType.ATTENDANCE_ALERT
    student_id: str
    student_name: str
    student_email: str
    course_code: str
    course_name: str
    absence_count: int
    warning_level: AttendanceWarningLevel
    attendance_date: date


class PaymentReminderPayload(WebhookBasePayload):
    event_type: WebhookEventType = WebhookEventType.PAYMENT_REMINDER
    student_id: str
    student_name: str
    student_email: str
    payment_id: int
    payment_type: PaymentType
    amount_due: float
    due_date: date
    days_overdue: int
    invoice_number: Optional[str] = None


class DeadlineReminderPayload(WebhookBasePayload):
    event_type: WebhookEventType = WebhookEventType.DEADLINE_REMINDER
    student_id: str
    student_name: str
    student_email: str
    assessment_id: int
    assessment_title: str
    assessment_type: AssessmentType
    course_code: str
    course_name: str
    due_date: date
    days_until_due: int
    max_score: float
    weight: float


class GradePublishedPayload(WebhookBasePayload):
    event_type: WebhookEventType = WebhookEventType.GRADE_PUBLISHED
    student_id: str
    student_name: str
    student_email: str
    assessment_id: int
    assessment_title: str
    assessment_type: AssessmentType
    course_code: str
    course_name: str
    score: float
    max_score: float
    weight: float
    percentage: float


class InternshipStatusUpdatePayload(WebhookBasePayload):
    event_type: WebhookEventType = WebhookEventType.INTERNSHIP_STATUS_UPDATE
    student_id: str
    student_name: str
    student_email: str
    internship_id: int
    company_name: str
    position: str
    previous_status: InternshipStatus
    new_status: InternshipStatus
    approved_by: Optional[str] = None
    approved_at: Optional[datetime] = None
    rejection_reason: Optional[str] = None


class AttendanceMarkedPayload(WebhookBasePayload):
    event_type: WebhookEventType = WebhookEventType.ATTENDANCE_MARKED
    student_id: str
    student_name: str
    student_email: str
    course_code: str
    course_name: str
    date: date
    status: AttendanceStatus
    warning_level: AttendanceWarningLevel


class PaymentStatusChangePayload(WebhookBasePayload):
    event_type: WebhookEventType = WebhookEventType.PAYMENT_STATUS_CHANGE
    student_id: str
    student_name: str
    student_email: str
    payment_id: int
    payment_type: PaymentType
    previous_status: PaymentStatus
    new_status: PaymentStatus
    amount: float
    paid_amount: float
    due_date: date


# Union of all webhook payloads
WebhookPayload = Union[
    AttendanceAlertPayload,
    PaymentReminderPayload,
    DeadlineReminderPayload,
    GradePublishedPayload,
    InternshipStatusUpdatePayload,
    AttendanceMarkedPayload,
    PaymentStatusChangePayload
]


# ===== Admin/Control Schemas =====
class AttendanceMarkRequest(BaseModel):
    student_id: int
    course_id: int
    date: date
    status: AttendanceStatus
    notes: Optional[str] = Field(None, max_length=500)


class AttendanceBatchRecord(BaseModel):
    student_id: int
    status: AttendanceStatus


class AttendanceBatchMarkRequest(BaseModel):
    course_id: int
    date: date
    records: List[AttendanceBatchRecord]


class InternshipDecisionRequest(BaseModel):
    status: InternshipStatus
    rejection_reason: Optional[str] = Field(None, max_length=500)


class AssessmentPublishRequest(BaseModel):
    score: float = Field(..., ge=0)


class WebhookRetryRequest(BaseModel):
    log_id: int


class SystemStateResponse(BaseModel):
    users: int
    courses: int
    enrollments: int
    attendances: int
    payments: int
    assessments: int
    internships: int
    webhook_logs: int
    webhook_settings: int
    webhook_target_url: Optional[str]
    webhook_secret_configured: bool


class SeedResponse(BaseModel):
    message: str
    users_created: int
    courses_created: int
    enrollments_created: int
    attendances_created: int
    payments_created: int
    assessments_created: int
    internships_created: int


class PaginatedResponse(BaseModel):
    items: List[Any]
    total: int
    page: int
    page_size: int
    total_pages: int