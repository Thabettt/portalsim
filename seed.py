#!/usr/bin/env python3
"""
Database seeding script for University Portal Simulator.
Run with: python seed.py
Or use the admin endpoint: POST /admin/seed
"""

import random
from datetime import datetime, date, timedelta
from sqlmodel import Session, select, func, delete
from app.db import engine, create_db_and_tables
from app.models import (
    User, Course, CourseEnrollment, Attendance, Payment,
    Assessment, Internship, WebhookSetting, SystemSetting,
    WebhookLog, CourseSchedule,
    UserRole, AttendanceStatus, AttendanceWarningLevel,
    PaymentStatus, PaymentType, AssessmentType, InternshipStatus,
    CourseEnrollmentStatus
)
from app.services.attendance import calculate_warning_level, get_total_sessions
from app.config import get_settings
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)
settings = get_settings()


# Demo data constants
FIXED_STUDENTS = [
    ("Abdulaziz", "thabetology@gmail.com"),
    ("Ali", "alialnaggar.h@gmail.com"),
    ("Lakshy", "lakshyrupani.lr@gmail.com"),
    ("Mohamed", "giuians2027@gmail.com"),
]

STUDENT_NAMES = [
    ("Ahmed Hassan", "ahmed.hassan@student.edu.eg"),
    ("Fatima Ali", "fatima.ali@student.edu.eg"),
    ("Mohamed Omar", "mohamed.omar@student.edu.eg"),
    ("Aisha Mahmoud", "aisha.mahmoud@student.edu.eg"),
    ("Youssef Ibrahim", "youssef.ibrahim@student.edu.eg"),
    ("Mariam Adel", "mariam.adel@student.edu.eg"),
    ("Karim Mostafa", "karim.mostafa@student.edu.eg"),
    ("Nour El-Din", "nour.eldin@student.edu.eg"),
    ("Sara Khaled", "sara.khaled@student.edu.eg"),
    ("Omar Tarek", "omar.tarek@student.edu.eg"),
    ("Laila Samir", "laila.samir@student.edu.eg"),
]

COURSES = [
    ("CS-101", "Introduction to Computer Science", "Fall 2024", 4),
    ("CS-201", "Data Structures and Algorithms", "Fall 2024", 8),
    ("CS-301", "Database Systems", "Fall 2024", 6),
    ("CS-302", "Operating Systems", "Fall 2024", 6),
    ("CS-401", "Machine Learning", "Fall 2024", 8),
    ("CS-402", "Computer Networks", "Fall 2024", 4),
    ("MA-101", "Calculus I", "Fall 2024", 8),
    ("MA-201", "Linear Algebra", "Fall 2024", 4),
    ("PH-101", "Physics I", "Fall 2024", 6),
    ("EN-101", "Technical English", "Fall 2024", 4),
]

INSTRUCTORS = [
    ("Dr. Ahmed El-Sayed", "ahmed.elsayed@faculty.edu.eg"),
    ("Prof. Mona Hassan", "mona.hassan@faculty.edu.eg"),
    ("Dr. Karim Mahmoud", "karim.mahmoud@faculty.edu.eg"),
    ("Prof. Aisha Omar", "aisha.omar@faculty.edu.eg"),
    ("Dr. Youssef Nabil", "youssef.nabil@faculty.edu.eg"),
]

INTERNSHIP_COMPANIES = [
    ("TechCorp Egypt", "Software Engineering Intern", "Cairo"),
    ("Digital Solutions", "Data Science Intern", "Alexandria"),
    ("CloudTech Systems", "DevOps Intern", "Cairo"),
    ("AI Innovations", "ML Research Intern", "Giza"),
    ("FinTech Solutions", "Backend Developer Intern", "Cairo"),
    ("CyberSec Labs", "Security Analyst Intern", "Alexandria"),
    ("MobileFirst", "Mobile App Developer Intern", "Cairo"),
    ("DataFlow Analytics", "Data Engineering Intern", "Smart Village"),
]

PAYMENT_TYPES = [
    (PaymentType.TUITION, 15000, "Tuition Fee - Fall 2024"),
    (PaymentType.LAB_FEE, 2000, "Lab Fee - Fall 2024"),
    (PaymentType.LIBRARY_FEE, 500, "Library Fee - Fall 2024"),
    (PaymentType.EXAM_FEE, 1000, "Exam Fee - Fall 2024"),
]


def generate_student_id(year: int, sequence: int) -> str:
    return f"STU-{year}-{sequence:04d}"


def create_instructors(session: Session) -> list:
    """Create instructor users"""
    instructors = []
    for i, (name, email) in enumerate(INSTRUCTORS):
        instructor = User(
            student_id=f"INS-2024-{i+1:03d}",
            email=email,
            full_name=name,
            role=UserRole.INSTRUCTOR,
            hashed_password="demo_hash",
            is_active=True
        )
        session.add(instructor)
        instructors.append(instructor)
    session.commit()
    for inst in instructors:
        session.refresh(inst)
    logger.info(f"Created {len(instructors)} instructors")
    return instructors


def create_students(session: Session, year: int = 2024) -> list:
    """Create student users"""
    students = []
    
    # Create fixed students first
    for i, (name, email) in enumerate(FIXED_STUDENTS):
        student = User(
            student_id=generate_student_id(year, i + 1),
            email=email,
            full_name=name,
            role=UserRole.STUDENT,
            hashed_password="demo_hash",
            is_active=True
        )
        session.add(student)
        students.append(student)
        
    # Create random students
    start_idx = len(FIXED_STUDENTS) + 1
    for i, (name, email) in enumerate(STUDENT_NAMES):
        student = User(
            student_id=generate_student_id(year, start_idx + i),
            email=email,
            full_name=name,
            role=UserRole.STUDENT,
            hashed_password="demo_hash",
            is_active=True
        )
        session.add(student)
        students.append(student)
        
    session.commit()
    for s in students:
        session.refresh(s)
    logger.info(f"Created {len(students)} students")
    return students


def create_courses(session: Session, instructors: list) -> list:
    """Create courses with assigned instructors"""
    courses = []
    for i, (code, name, semester, credits) in enumerate(COURSES):
        instructor = instructors[i % len(instructors)] if instructors else None
        course = Course(
            code=code,
            name=name,
            description=f"Course description for {name}",
            credits=credits,
            semester=semester,
            instructor_id=instructor.id if instructor else None,
            is_active=True
        )
        session.add(course)
        courses.append(course)
    session.commit()
    for c in courses:
        session.refresh(c)
    logger.info(f"Created {len(courses)} courses")
    return courses


def create_course_schedules(session: Session, courses: list):
    """Generate 12-week schedule for all courses"""
    valid_weekdays = [0, 1, 2, 3, 6]  # Mon, Tue, Wed, Thu, Sun
    six_credit_courses = [c for c in courses if c.credits == 6]
    
    schedules = []
    
    for c in courses:
        if c.credits == 4:
            # 1 session per week
            weekday = random.choice(valid_weekdays)
            for week in range(1, 13):
                schedules.append(CourseSchedule(course_id=c.id, week_number=week, weekday=weekday))
                
        elif c.credits == 8:
            # 2 sessions per week
            weekdays = random.sample(valid_weekdays, 2)
            for week in range(1, 13):
                for w in weekdays:
                    schedules.append(CourseSchedule(course_id=c.id, week_number=week, weekday=w))
                    
    # Handle 6-credit courses in pairs if possible
    for i in range(0, len(six_credit_courses), 2):
        pair = six_credit_courses[i:i+2]
        weekdays = random.sample(valid_weekdays, 2)
        
        # First course in pair
        c1 = pair[0]
        for week in range(1, 13):
            # Alternates 1 and 2 sessions
            if week % 2 == 1: # Odd week: 1 session
                schedules.append(CourseSchedule(course_id=c1.id, week_number=week, weekday=weekdays[0]))
            else: # Even week: 2 sessions
                schedules.append(CourseSchedule(course_id=c1.id, week_number=week, weekday=weekdays[0]))
                schedules.append(CourseSchedule(course_id=c1.id, week_number=week, weekday=weekdays[1]))
                
        # Second course in pair (if exists)
        if len(pair) > 1:
            c2 = pair[1]
            for week in range(1, 13):
                # Alternates opposite to c1
                if week % 2 == 1: # Odd week: 2 sessions
                    schedules.append(CourseSchedule(course_id=c2.id, week_number=week, weekday=weekdays[0]))
                    schedules.append(CourseSchedule(course_id=c2.id, week_number=week, weekday=weekdays[1]))
                else: # Even week: 1 session
                    schedules.append(CourseSchedule(course_id=c2.id, week_number=week, weekday=weekdays[0]))

    for s in schedules:
        session.add(s)
    session.commit()
    logger.info(f"Created {len(schedules)} course schedule entries")


def create_enrollments(session: Session, students: list, courses: list) -> list:
    """Enroll students in courses"""
    enrollments = []
    for student in students:
        # Each student takes 4-6 courses
        num_courses = random.randint(4, 6)
        student_courses = random.sample(courses, num_courses)

        for course in student_courses:
            enrollment = CourseEnrollment(
                student_id=student.id,
                course_id=course.id,
                status=CourseEnrollmentStatus.ACTIVE
            )
            session.add(enrollment)
            enrollments.append(enrollment)
    session.commit()
    logger.info(f"Created {len(enrollments)} enrollments")
    return enrollments


def create_attendance_records(session: Session, students: list, courses: list):
    """Create attendance records for the past 8 weeks based on explicit schedule"""
    # Define today as being within week 9. Week starts on Monday (weekday 0)
    today = date.today()
    days_to_subtract = today.weekday() + (8 * 7) # Back to Monday of week 1
    semester_start_date = today - timedelta(days=days_to_subtract)
    
    # Save semester start date
    setting = SystemSetting(key="semester_start_date", value=semester_start_date.isoformat())
    session.add(setting)
    session.commit()
    
    # Get all active enrollments
    enrollments = session.exec(
        select(CourseEnrollment).where(CourseEnrollment.status == CourseEnrollmentStatus.ACTIVE)
    ).all()
    
    # Build a quick lookup dictionary: course_id -> list of student_ids
    course_students = {}
    for e in enrollments:
        if e.course_id not in course_students:
            course_students[e.course_id] = []
        course_students[e.course_id].append(e)

    end_date = today - timedelta(days=1)
    
    attendance_records = []
    absent_counts = {}  # Track absences per (student_id, course_id)

    # Pre-calculate total sessions map
    course_total_sessions = {c.id: get_total_sessions(c) for c in courses}
    
    current_date = semester_start_date
    while current_date <= end_date:
        if current_date.weekday() not in (4, 5):  # Not Friday/Saturday
            week_number = ((current_date - semester_start_date).days // 7) + 1
            weekday = current_date.weekday()
            
            # Find courses scheduled for today
            schedules = session.exec(
                select(CourseSchedule)
                .where(CourseSchedule.week_number == week_number)
                .where(CourseSchedule.weekday == weekday)
            ).all()
            
            for schedule in schedules:
                course_id = schedule.course_id
                active_enrollments = [e for e in course_students.get(course_id, []) if e.status == CourseEnrollmentStatus.ACTIVE]
                total_sess = course_total_sessions.get(course_id, 12)
                
                for enrollment in active_enrollments:
                    # 85% attendance rate
                    status = AttendanceStatus.PRESENT if random.random() < 0.85 else AttendanceStatus.ABSENT

                    key = (enrollment.student_id, course_id)
                    if key not in absent_counts:
                        absent_counts[key] = 0
                        
                    if status == AttendanceStatus.ABSENT:
                        absent_counts[key] += 1

                    # Determine warning level dynamically
                    warning = calculate_warning_level(absent_counts[key], total_sess)
                    
                    if warning == AttendanceWarningLevel.FINAL_WARNING:
                        enrollment.status = CourseEnrollmentStatus.DROPPED
                        session.add(enrollment)

                    attendance = Attendance(
                        student_id=enrollment.student_id,
                        course_id=course_id,
                        date=current_date,
                        status=status,
                        warning_level=warning,
                        notes="Auto-generated demo data" if status == AttendanceStatus.ABSENT else None,
                        marked_by=0
                    )
                    session.add(attendance)
                    attendance_records.append(attendance)
                    
        current_date += timedelta(days=1)

    session.commit()
    logger.info(f"Created {len(attendance_records)} attendance records")


def create_payments(session: Session, students: list):
    """Create payment schedules for students"""
    payments = []
    base_date = date.today()

    for student in students:
        for pay_type, amount, description in PAYMENT_TYPES:
            num_installments = random.randint(2, 3)
            installment_amount = amount / num_installments

            for i in range(num_installments):
                due_date = base_date + timedelta(days=random.randint(-30, 60))

                if due_date < base_date - timedelta(days=7):
                    status = PaymentStatus.OVERDUE
                elif due_date < base_date:
                    status = PaymentStatus.PENDING
                else:
                    status = PaymentStatus.PENDING

                payment = Payment(
                    student_id=student.id,
                    payment_type=pay_type,
                    amount=round(installment_amount, 2),
                    due_date=due_date,
                    status=status,
                    paid_amount=0 if status != PaymentStatus.PAID else round(installment_amount, 2),
                    paid_at=datetime.utcnow() if status == PaymentStatus.PAID else None,
                    description=description,
                    invoice_number=f"INV-{student.student_id}-{pay_type.value.upper()}-{i+1}"
                )
                session.add(payment)
                payments.append(payment)

    session.commit()
    logger.info(f"Created {len(payments)} payment records")


def create_assessments(session: Session, students: list, courses: list):
    """Create assessments for enrolled students"""
    enrollments = session.exec(
        select(CourseEnrollment).where(CourseEnrollment.status == CourseEnrollmentStatus.ACTIVE)
    ).all()

    assessments = []
    base_date = date.today()

    for enrollment in enrollments:
        num_assessments = random.randint(3, 5)
        assessment_types = random.sample(
            [AssessmentType.QUIZ, AssessmentType.MIDTERM, AssessmentType.ASSIGNMENT,
             AssessmentType.PROJECT, AssessmentType.FINAL],
            num_assessments
        )

        for i, atype in enumerate(assessment_types):
            due_date = base_date + timedelta(days=random.randint(-20, 30))
            max_score = 100 if atype in [AssessmentType.MIDTERM, AssessmentType.FINAL] else 50

            is_published = random.random() < 0.6
            score = None
            published_at = None

            if is_published:
                score = round(random.uniform(40, 95), 1)
                published_at = datetime.utcnow() - timedelta(days=random.randint(1, 30))

            assessment = Assessment(
                course_id=enrollment.course_id,
                student_id=enrollment.student_id,
                assessment_type=atype,
                title=f"{atype.value.title()} {i+1}",
                max_score=max_score,
                score=score,
                weight=1.0 if atype in [AssessmentType.QUIZ, AssessmentType.ASSIGNMENT] else 1.5,
                is_published=is_published,
                published_at=published_at,
                due_date=due_date
            )
            session.add(assessment)
            assessments.append(assessment)

    session.commit()
    logger.info(f"Created {len(assessments)} assessments")


def create_internships(session: Session, students: list):
    """Create internship applications"""
    internships = []

    # ~80% of students have internships to ensure we get plenty of entries
    students_with_internships = random.sample(students, int(len(students) * 0.8))

    for student in students_with_internships:
        num_applications = random.randint(2, 4)
        companies = random.sample(INTERNSHIP_COMPANIES, num_applications)

        for company_name, position, location in companies:
            start_date = date.today() + timedelta(days=random.randint(30, 120))
            end_date = start_date + timedelta(days=random.randint(60, 120))

            # Weight towards PENDING so the user has plenty to review
            status = random.choice([
                InternshipStatus.PENDING, InternshipStatus.PENDING, InternshipStatus.PENDING,
                InternshipStatus.APPROVED, InternshipStatus.REJECTED, 
                InternshipStatus.IN_PROGRESS, InternshipStatus.COMPLETED
            ])
            approved_by = None
            approved_at = None
            rejection_reason = None

            if status in [InternshipStatus.APPROVED, InternshipStatus.IN_PROGRESS, InternshipStatus.COMPLETED]:
                approved_by = 1  # First admin
                approved_at = datetime.utcnow() - timedelta(days=random.randint(1, 30))
            elif status == InternshipStatus.REJECTED:
                rejection_reason = random.choice([
                    "Position filled",
                    "Requirements not met",
                    "Insufficient experience",
                    "Academic schedule conflict"
                ])

            internship = Internship(
                student_id=student.id,
                company_name=company_name,
                position=position,
                start_date=start_date,
                end_date=end_date,
                status=status,
                description=f"Internship at {company_name} as {position}",
                supervisor_name=f"Supervisor at {company_name}",
                supervisor_email=f"supervisor@{company_name.lower().replace(' ', '')}.com",
                approved_by=approved_by,
                approved_at=approved_at,
                rejection_reason=rejection_reason
            )
            session.add(internship)
            internships.append(internship)

    session.commit()
    logger.info(f"Created {len(internships)} internship records")


def create_webhook_settings(session: Session):
    """Create default webhook settings"""
    existing = session.exec(
        select(WebhookSetting).where(WebhookSetting.is_active == True)
    ).first()

    if not existing:
        webhook_setting = WebhookSetting(
            webhook_target_url=settings.webhook_target_url,
            shared_secret=settings.shared_secret,
            is_active=bool(settings.webhook_target_url)
        )
        session.add(webhook_setting)
        session.commit()
        logger.info("Created default webhook settings")


def create_system_settings(session: Session):
    """Create default system settings"""
    settings_data = {
        "attendance_first_warning_threshold": "3",
        "attendance_second_warning_threshold": "5",
        "attendance_final_warning_threshold": "7",
        "payment_reminder_days_before": "7",
        "deadline_reminder_days": "1,3,7",
        "webhook_retry_max_attempts": "3",
        "webhook_retry_delays": "5,30,120"
    }

    for key, value in settings_data.items():
        existing = session.exec(
            select(SystemSetting).where(SystemSetting.key == key)
        ).first()
        if not existing:
            setting = SystemSetting(key=key, value=value)
            session.add(setting)
    session.commit()
    logger.info("Created default system settings")


async def seed_database(session: Session = None):
    """Main seed function"""
    if session is None:
        with Session(engine) as session:
            return await seed_database(session)

    logger.info("Starting database seeding...")

    # Create tables if not exist (drop first to ensure schema updates)
    from sqlmodel import SQLModel
    SQLModel.metadata.drop_all(engine)
    create_db_and_tables()

    # Clear existing data (in dependency order)
    session.exec(delete(WebhookLog))
    session.exec(delete(Internship))
    session.exec(delete(Assessment))
    session.exec(delete(Payment))
    session.exec(delete(Attendance))
    session.exec(delete(CourseSchedule))
    session.exec(delete(CourseEnrollment))
    session.exec(delete(Course))
    session.exec(delete(User))
    session.exec(delete(WebhookSetting))
    session.exec(delete(SystemSetting))
    session.commit()

    # Create data in dependency order
    instructors = create_instructors(session)
    students = create_students(session)
    courses = create_courses(session, instructors)
    create_course_schedules(session, courses)
    create_enrollments(session, students, courses)
    create_attendance_records(session, students, courses)
    create_payments(session, students)
    create_assessments(session, students, courses)
    create_internships(session, students)
    create_webhook_settings(session)
    create_system_settings(session)

    logger.info("Database seeding completed!")

    return {
        "message": "Database seeded successfully",
        "users_created": len(students) + len(instructors),
        "students_created": len(students),
        "instructors_created": len(instructors),
        "courses_created": len(courses),
        "enrollments_created": session.exec(select(func.count(CourseEnrollment.id))).one(),
        "attendances_created": session.exec(select(func.count(Attendance.id))).one(),
        "payments_created": session.exec(select(func.count(Payment.id))).one(),
        "assessments_created": session.exec(select(func.count(Assessment.id))).one(),
        "internships_created": session.exec(select(func.count(Internship.id))).one(),
    }


if __name__ == "__main__":
    import asyncio
    asyncio.run(seed_database())