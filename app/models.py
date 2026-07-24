from datetime import datetime, date as date_type
from enum import Enum as PyEnum
from typing import Optional, List
from sqlmodel import SQLModel, Field, Relationship, Column, Enum as SQLEnum, DateTime
from sqlalchemy import Date, UniqueConstraint, Text


class UserRole(str, PyEnum):
    STUDENT = "student"
    ADMIN = "admin"
    INSTRUCTOR = "instructor"


class AttendanceStatus(str, PyEnum):
    PRESENT = "present"
    ABSENT = "absent"


class AttendanceWarningLevel(str, PyEnum):
    NONE = "none"
    FIRST_WARNING = "first_warning"
    SECOND_WARNING = "second_warning"
    FINAL_WARNING = "final_warning"


class PaymentStatus(str, PyEnum):
    PENDING = "pending"
    PAID = "paid"
    OVERDUE = "overdue"
    PARTIAL = "partial"
    WAIVED = "waived"


class PaymentType(str, PyEnum):
    TUITION = "tuition"
    LAB_FEE = "lab_fee"
    LIBRARY_FEE = "library_fee"
    EXAM_FEE = "exam_fee"
    OTHER = "other"


class AssessmentType(str, PyEnum):
    QUIZ = "quiz"
    MIDTERM = "midterm"
    FINAL = "final"
    ASSIGNMENT = "assignment"
    PROJECT = "project"
    PARTICIPATION = "participation"


class InternshipStatus(str, PyEnum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"


class WebhookEventType(str, PyEnum):
    ATTENDANCE_ALERT = "attendance_alert"
    PAYMENT_REMINDER = "payment_reminder"
    DEADLINE_REMINDER = "deadline_reminder"
    GRADE_PUBLISHED = "grade_published"
    INTERNSHIP_STATUS_UPDATE = "internship_status_update"
    ATTENDANCE_MARKED = "attendance_marked"
    PAYMENT_STATUS_CHANGE = "payment_status_change"


class CourseEnrollmentStatus(str, PyEnum):
    ACTIVE = "active"
    DROPPED = "dropped"


class WebhookDeliveryStatus(str, PyEnum):
    PENDING = "pending"
    SENT = "sent"
    FAILED = "failed"
    RETRYING = "retrying"


class User(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    student_id: str = Field(unique=True, index=True, max_length=50)  # e.g., STU-2023-0142
    email: str = Field(unique=True, index=True, max_length=100)
    full_name: str = Field(max_length=150)
    role: UserRole = Field(default=UserRole.STUDENT, sa_column=Column(SQLEnum(UserRole)))
    hashed_password: str = Field(max_length=255)  # Not used in demo, but kept for future
    is_active: bool = Field(default=True)
    created_at: datetime = Field(default_factory=datetime.utcnow, sa_column=Column(DateTime, default=datetime.utcnow))
    updated_at: datetime = Field(default_factory=datetime.utcnow, sa_column=Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow))

    # Relationships
    attendances: List["Attendance"] = Relationship(back_populates="student", sa_relationship_kwargs={"foreign_keys": "Attendance.student_id"})
    payments: List["Payment"] = Relationship(back_populates="student", sa_relationship_kwargs={"foreign_keys": "Payment.student_id"})
    assessments: List["Assessment"] = Relationship(back_populates="student", sa_relationship_kwargs={"foreign_keys": "Assessment.student_id"})
    internships: List["Internship"] = Relationship(back_populates="student", sa_relationship_kwargs={"foreign_keys": "Internship.student_id"})
    course_enrollments: List["CourseEnrollment"] = Relationship(back_populates="student", sa_relationship_kwargs={"foreign_keys": "CourseEnrollment.student_id"})


class Course(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    code: str = Field(unique=True, index=True, max_length=20)  # e.g., CS101
    name: str = Field(max_length=150)
    description: Optional[str] = Field(default=None, max_length=500)
    credits: int = Field(default=3)
    semester: str = Field(max_length=20)  # e.g., "Fall 2024"
    instructor_id: Optional[int] = Field(default=None, foreign_key="user.id")
    is_active: bool = Field(default=True)
    created_at: datetime = Field(default_factory=datetime.utcnow, sa_column=Column(DateTime, default=datetime.utcnow))

    # Relationships
    enrollments: List["CourseEnrollment"] = Relationship(back_populates="course")
    attendances: List["Attendance"] = Relationship(back_populates="course", sa_relationship_kwargs={"foreign_keys": "Attendance.course_id"})
    assessments: List["Assessment"] = Relationship(back_populates="course", sa_relationship_kwargs={"foreign_keys": "Assessment.course_id"})


class CourseEnrollment(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    student_id: int = Field(foreign_key="user.id", index=True)
    course_id: int = Field(foreign_key="course.id", index=True)
    enrolled_at: datetime = Field(default_factory=datetime.utcnow, sa_column=Column(DateTime, default=datetime.utcnow))
    status: CourseEnrollmentStatus = Field(default=CourseEnrollmentStatus.ACTIVE, sa_column=Column(SQLEnum(CourseEnrollmentStatus)))

    # Relationships
    student: Optional[User] = Relationship(back_populates="course_enrollments")
    course: Optional[Course] = Relationship(back_populates="enrollments")

    __table_args__ = (UniqueConstraint("student_id", "course_id", name="unique_student_course"),)


class CourseSchedule(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    course_id: int = Field(foreign_key="course.id", index=True)
    week_number: int = Field(ge=1, le=12)
    weekday: int = Field(ge=0, le=6)

    # Relationships
    course: Optional[Course] = Relationship()


class Attendance(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    student_id: int = Field(foreign_key="user.id", index=True)
    course_id: int = Field(foreign_key="course.id", index=True)
    date: date_type = Field(sa_column=Column(Date, index=True))
    status: AttendanceStatus = Field(default=AttendanceStatus.PRESENT, sa_column=Column(SQLEnum(AttendanceStatus)))
    warning_level: AttendanceWarningLevel = Field(default=AttendanceWarningLevel.NONE, sa_column=Column(SQLEnum(AttendanceWarningLevel)))
    notes: Optional[str] = Field(default=None, max_length=500)
    marked_by: Optional[int] = Field(default=None, foreign_key="user.id")
    marked_at: datetime = Field(default_factory=datetime.utcnow, sa_column=Column(DateTime, default=datetime.utcnow))
    created_at: datetime = Field(default_factory=datetime.utcnow, sa_column=Column(DateTime, default=datetime.utcnow))

    # Relationships
    student: Optional[User] = Relationship(back_populates="attendances", sa_relationship_kwargs={"foreign_keys": "Attendance.student_id"})
    course: Optional[Course] = Relationship(back_populates="attendances", sa_relationship_kwargs={"foreign_keys": "Attendance.course_id"})

    __table_args__ = (UniqueConstraint("student_id", "course_id", "date", name="unique_attendance_record"),)


class Payment(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    student_id: int = Field(foreign_key="user.id", index=True)
    payment_type: PaymentType = Field(sa_column=Column(SQLEnum(PaymentType)))
    amount: float = Field(gt=0)
    due_date: date_type = Field(sa_column=Column(Date, index=True))
    status: PaymentStatus = Field(default=PaymentStatus.PENDING, sa_column=Column(SQLEnum(PaymentStatus)))
    paid_amount: float = Field(default=0, ge=0)
    paid_at: Optional[datetime] = Field(default=None, sa_column=Column(DateTime))
    description: Optional[str] = Field(default=None, max_length=500)
    invoice_number: Optional[str] = Field(default=None, max_length=50, unique=True)
    external_reference_id: Optional[str] = Field(default=None, unique=True, index=True)
    source: str = Field(default="exam_remark", max_length=50)
    created_at: datetime = Field(default_factory=datetime.utcnow, sa_column=Column(DateTime, default=datetime.utcnow))
    updated_at: datetime = Field(default_factory=datetime.utcnow, sa_column=Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow))

    # Relationships
    student: Optional[User] = Relationship(back_populates="payments", sa_relationship_kwargs={"foreign_keys": "Payment.student_id"})


class Assessment(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    course_id: int = Field(foreign_key="course.id", index=True)
    student_id: int = Field(foreign_key="user.id", index=True)
    assessment_type: AssessmentType = Field(sa_column=Column(SQLEnum(AssessmentType)))
    title: str = Field(max_length=200)
    max_score: float = Field(gt=0)
    score: Optional[float] = Field(default=None, ge=0)
    weight: float = Field(default=1.0, gt=0)  # Weight for grade calculation
    is_published: bool = Field(default=False)
    published_at: Optional[datetime] = Field(default=None, sa_column=Column(DateTime))
    due_date: Optional[date_type] = Field(default=None, sa_column=Column(Date))
    created_at: datetime = Field(default_factory=datetime.utcnow, sa_column=Column(DateTime, default=datetime.utcnow))
    updated_at: datetime = Field(default_factory=datetime.utcnow, sa_column=Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow))

    # Relationships
    course: Optional[Course] = Relationship(back_populates="assessments", sa_relationship_kwargs={"foreign_keys": "Assessment.course_id"})
    student: Optional[User] = Relationship(back_populates="assessments", sa_relationship_kwargs={"foreign_keys": "Assessment.student_id"})


class Internship(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    student_id: int = Field(foreign_key="user.id", index=True)
    company_name: str = Field(max_length=200)
    position: str = Field(max_length=150)
    start_date: date_type = Field(sa_column=Column(Date))
    end_date: date_type = Field(sa_column=Column(Date))
    status: InternshipStatus = Field(default=InternshipStatus.PENDING, sa_column=Column(SQLEnum(InternshipStatus)))
    description: Optional[str] = Field(default=None, max_length=1000)
    supervisor_name: Optional[str] = Field(default=None, max_length=150)
    supervisor_email: Optional[str] = Field(default=None, max_length=150)
    approved_by: Optional[int] = Field(default=None, foreign_key="user.id")
    approved_at: Optional[datetime] = Field(default=None, sa_column=Column(DateTime))
    rejection_reason: Optional[str] = Field(default=None, max_length=500)
    created_at: datetime = Field(default_factory=datetime.utcnow, sa_column=Column(DateTime, default=datetime.utcnow))
    updated_at: datetime = Field(default_factory=datetime.utcnow, sa_column=Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow))

    # Relationships
    student: Optional[User] = Relationship(back_populates="internships", sa_relationship_kwargs={"foreign_keys": "Internship.student_id"})


class WebhookSetting(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    webhook_target_url: str = Field(max_length=500)
    shared_secret: str = Field(max_length=255)
    is_active: bool = Field(default=True)
    created_at: datetime = Field(default_factory=datetime.utcnow, sa_column=Column(DateTime, default=datetime.utcnow))
    updated_at: datetime = Field(default_factory=datetime.utcnow, sa_column=Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow))


class WebhookLog(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    event_type: WebhookEventType = Field(sa_column=Column(SQLEnum(WebhookEventType), index=True))
    target_url: str = Field(max_length=500)
    payload: str = Field(sa_column=Column(Text))  # JSON string
    status: WebhookDeliveryStatus = Field(default=WebhookDeliveryStatus.PENDING, sa_column=Column(SQLEnum(WebhookDeliveryStatus), index=True))
    status_code: Optional[int] = Field(default=None)
    response_body: Optional[str] = Field(default=None, max_length=2000)
    error_message: Optional[str] = Field(default=None, max_length=1000)
    attempt_number: int = Field(default=1)
    max_retries: int = Field(default=3)
    next_retry_at: Optional[datetime] = Field(default=None, sa_column=Column(DateTime, index=True))
    created_at: datetime = Field(default_factory=datetime.utcnow, sa_column=Column(DateTime, default=datetime.utcnow, index=True))
    sent_at: Optional[datetime] = Field(default=None, sa_column=Column(DateTime))
    completed_at: Optional[datetime] = Field(default=None, sa_column=Column(DateTime))

    # Related entity references
    student_id: Optional[int] = Field(default=None, foreign_key="user.id", index=True)
    course_id: Optional[int] = Field(default=None, foreign_key="course.id", index=True)
    payment_id: Optional[int] = Field(default=None, foreign_key="payment.id", index=True)
    assessment_id: Optional[int] = Field(default=None, foreign_key="assessment.id", index=True)
    internship_id: Optional[int] = Field(default=None, foreign_key="internship.id", index=True)


class SystemSetting(SQLModel, table=True):
    """Generic key-value settings store"""
    id: Optional[int] = Field(default=None, primary_key=True)
    key: str = Field(unique=True, index=True, max_length=100)
    value: str = Field(max_length=500)
    description: Optional[str] = Field(default=None, max_length=500)
    updated_at: datetime = Field(default_factory=datetime.utcnow, sa_column=Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow))