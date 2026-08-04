import uuid
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
    Assessment, Internship, InternshipProgressReport, WebhookSetting, SystemSetting,
    WebhookLog, CourseSchedule,
    UserRole, AttendanceStatus, AttendanceWarningLevel,
    PaymentStatus, PaymentType, AssessmentType, InternshipStatus,
    CourseEnrollmentStatus, ProgressReportStatus
)
from app.services.attendance import calculate_warning_level, get_total_sessions
from app.config import get_settings
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)
settings = get_settings()


# Demo data constants
FIXED_STUDENTS = [
    ("Abdulaziz", "alialnaggar.h@gmail.com"),
    ("Ali", "alialnaggar.h@gmail.com"),
    ("Lakshy", "alialnaggar.h@gmail.com"),
    ("Mohamed", "alialnaggar.h@gmail.com"),
]

STUDENT_NAMES = [
    ("Essam El-Din", "alialnaggar.h@gmail.com"),
    ("Khaled Yassin", "alialnaggar.h@gmail.com"),
    ("Tarek Badr", "alialnaggar.h@gmail.com"),
    ("Khaled Galal", "alialnaggar.h@gmail.com"),
    ("Nada Kamel", "alialnaggar.h@gmail.com"),
    ("Amr Hafez", "alialnaggar.h@gmail.com"),
    ("Mennatullah Ahmed", "alialnaggar.h@gmail.com"),
    ("Hala Farouk", "alialnaggar.h@gmail.com"),
    ("Omar Hafez", "alialnaggar.h@gmail.com"),
    ("Karim Saeed", "alialnaggar.h@gmail.com"),
    ("Rola Said", "alialnaggar.h@gmail.com"),
    ("Youssef Magdy", "alialnaggar.h@gmail.com"),
    ("Salma Samir", "alialnaggar.h@gmail.com"),
    ("Karim El-Din", "alialnaggar.h@gmail.com"),
    ("Yasmine Zaki", "alialnaggar.h@gmail.com"),
    ("Fatima Ali", "alialnaggar.h@gmail.com"),
    ("Rania Nabil", "alialnaggar.h@gmail.com"),
    ("Salma Hafez", "alialnaggar.h@gmail.com"),
    ("Tarek Hossam", "alialnaggar.h@gmail.com"),
    ("Mennatullah Saeed", "alialnaggar.h@gmail.com"),
    ("Rola Saleh", "alialnaggar.h@gmail.com"),
    ("Ghada Fares", "alialnaggar.h@gmail.com"),
    ("Mariam Tarek", "alialnaggar.h@gmail.com"),
    ("Nour Hafez", "alialnaggar.h@gmail.com"),
    ("Nasser Farouk", "alialnaggar.h@gmail.com"),
    ("Yasmine Galal", "alialnaggar.h@gmail.com"),
    ("Farah Gomaa", "alialnaggar.h@gmail.com"),
    ("Fatima Ashraf", "alialnaggar.h@gmail.com"),
    ("Rania Magdy", "alialnaggar.h@gmail.com"),
    ("Sara Essam", "alialnaggar.h@gmail.com"),
    ("Nada Riad", "alialnaggar.h@gmail.com"),
    ("Farah Ayman", "alialnaggar.h@gmail.com"),
    ("Mohamed Said", "alialnaggar.h@gmail.com"),
    ("Ghada Mostafa", "alialnaggar.h@gmail.com"),
    ("Farah Helmy", "alialnaggar.h@gmail.com"),
    ("Nada Tarek", "alialnaggar.h@gmail.com"),
    ("Hoda Omar", "alialnaggar.h@gmail.com"),
    ("Tarek Hassan", "alialnaggar.h@gmail.com"),
    ("Karim Farouk", "alialnaggar.h@gmail.com"),
    ("Hoda Hossam", "alialnaggar.h@gmail.com"),
    ("Mostafa Shawky", "alialnaggar.h@gmail.com"),
    ("Mariam Farouk", "alialnaggar.h@gmail.com"),
    ("Salma Ali", "alialnaggar.h@gmail.com"),
    ("Hassan Nabil", "alialnaggar.h@gmail.com"),
    ("Essam Yassin", "alialnaggar.h@gmail.com"),
    ("Aisha Khaled", "alialnaggar.h@gmail.com"),
    ("Laila Wael", "alialnaggar.h@gmail.com"),
    ("Sherif Mostafa", "alialnaggar.h@gmail.com"),
    ("Dina Omar", "alialnaggar.h@gmail.com"),
    ("Adel Hossam", "alialnaggar.h@gmail.com"),
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
    ("Dr. Mahmoud Hassan", "alialnaggar.h@gmail.com", "SUP001"),
    ("Dr. Mona Ibrahim", "alialnaggar.h@gmail.com", "SUP002"),
    ("Dr. Ahmed Mostafa", "alialnaggar.h@gmail.com", "SUP003"),
    ("Dr. Yasmine Nabil", "alialnaggar.h@gmail.com", "SUP004"),
    ("Dr. Khaled Amin", "alialnaggar.h@gmail.com", "SUP005"),
    ("Dr. Rania Fouad", "alialnaggar.h@gmail.com", "SUP006"),
    ("Dr. Heba Salah", "alialnaggar.h@gmail.com", "SUP007"),
    ("Dr. Ahmed El-Sayed", "alialnaggar.h@gmail.com", "INS001"),
    ("Prof. Mona Hassan", "alialnaggar.h@gmail.com", "INS002"),
    ("Dr. Karim Mahmoud", "alialnaggar.h@gmail.com", "INS003"),
    ("Prof. Aisha Omar", "alialnaggar.h@gmail.com", "INS004"),
    ("Dr. Youssef Nabil", "alialnaggar.h@gmail.com", "INS005"),
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
    for i, (name, email, inst_id) in enumerate(INSTRUCTORS):
        instructor = User(
            student_id=inst_id,
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
    """Create student users deterministically for demonstration scenarios"""
    students = []
    
    DEMO_STUDENTS = [
        ("STU001", "Ahmed Mohamed Hassan", "alialnaggar.h@gmail.com"),
        ("STU002", "Sara Ahmed Ali", "alialnaggar.h@gmail.com"),
        ("STU003", "Omar Khaled Mahmoud", "alialnaggar.h@gmail.com"),
        ("STU004", "Mariam Sherif Adel", "alialnaggar.h@gmail.com"),
        ("STU005", "Youssef Adel Ibrahim", "alialnaggar.h@gmail.com"),
        ("STU006", "Nouran Hossam El-Din", "alialnaggar.h@gmail.com"),
        ("STU007", "Fatma Wael Abdelrahman", "alialnaggar.h@gmail.com")
    ]
    
    for stu_id, name, email in DEMO_STUDENTS:
        student = User(
            student_id=stu_id,
            email=email,
            full_name=name,
            role=UserRole.STUDENT,
            hashed_password="demo_hash",
            is_active=True,
            is_foreigner=False,
            id_card_image_url="/static/images/id_card.png"
        )
        session.add(student)
        students.append(student)
        
    session.commit()
    for s in students:
        session.refresh(s)
    logger.info(f"Created {len(students)} deterministic students")
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
    today_midnight = datetime.combine(base_date, datetime.min.time())
    
    # Deterministic day offsets for testing all cases of midterm/final remarks
    midterm_final_cases = [0, 1, 2, 3, 4, 10]
    mf_case_idx = 0

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

            if atype in [AssessmentType.MIDTERM, AssessmentType.FINAL]:
                is_published = True
                score = round(random.uniform(40, 95), 1)
                days_ago = midterm_final_cases[mf_case_idx % len(midterm_final_cases)]
                published_at = today_midnight - timedelta(days=days_ago)
                mf_case_idx += 1
            else:
                is_published = random.random() < 0.6
                score = None
                published_at = None

                if is_published:
                    score = round(random.uniform(40, 95), 1)
                    published_at = today_midnight - timedelta(days=random.randint(1, 30))

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
    """Create internship applications with deterministic demo cases"""
    internships = []
    
    student_data = {
        "STU001": {
            "status": InternshipStatus.PENDING,
            "acad_sup": "SUP001 - Dr. Mahmoud Hassan",
            "country": "Egypt", "faculty": "Informatics and Computer Science",
            "major1": "Business Informatics", "major2": None,
            "company": "Oracle Egypt", "title": "Oracle Developer Intern", "dept": "Enterprise Applications",
            "start": date(2026, 1, 15), "end": date(2026, 6, 15),
            "entry": datetime(2026, 1, 10, 10, 30),
            "source": "LinkedIn", "workplace": "Hybrid", "days": 5, "hours": 8,
            "desc": "Maintain Oracle Forms applications, assist in bug fixing, develop SQL queries, support ERP enhancements, and document technical changes.",
            "org_sup_name": "Karim Adel", "org_sup_title": "Senior Oracle Developer", "org_sup_mob": "+20 101 234 5678",
            "cc_status": "pending", "sup_status": "pending", "cc_reason": None, "sup_reason": None,
            "acad_final": "waiting", "cc_final": "waiting",
            "proof": datetime(2026, 1, 9, 16, 12), "eval": None,
            "reports": []
        },
        "STU002": {
            "status": InternshipStatus.IN_PROGRESS,
            "acad_sup": "SUP002 - Dr. Mona Ibrahim",
            "country": "Egypt", "faculty": "Business Administration",
            "major1": "Management", "major2": "Marketing",
            "company": "Tanmeyah", "title": "Oracle Developer Intern", "dept": "Information Technology",
            "start": date(2026, 1, 15), "end": date(2026, 6, 15),
            "entry": datetime(2026, 1, 12, 9, 20),
            "source": "Career Fair", "workplace": "On Site", "days": 5, "hours": 8,
            "desc": "Maintain Oracle Forms and Reports, support ERP modules, develop SQL procedures, fix production issues, and participate in testing.",
            "org_sup_name": "Mohamed Samir", "org_sup_title": "Senior Software Engineer", "org_sup_mob": "+20 100 456 7812",
            "cc_status": "accepted", "sup_status": "accepted", "cc_reason": "Internship approved.", "sup_reason": "Approved for academic supervision.",
            "acad_final": "waiting", "cc_final": "waiting",
            "proof": datetime(2026, 1, 11, 11, 40), "eval": None,
            "reports": [
                {"status": ProgressReportStatus.APPROVED, "date": date(2026, 1, 29), "feedback": "Excellent first report. Good overview of onboarding activities.", "content": "During my first two weeks, I completed the onboarding process, received access to Oracle Forms and Reports Builder, attended meetings with the ERP team, and learned the company's development workflow. I also explored the existing banking modules and documented the overall system architecture."},
                {"status": ProgressReportStatus.REJECTED, "date": date(2026, 2, 12), "feedback": "Please include more technical details and explain your personal contribution.", "content": "I participated in resolving issues related to Oracle Forms, tested several existing reports, and reviewed SQL procedures used by the finance department. I also attended sprint meetings and documented the bugs identified during testing."},
                {"status": ProgressReportStatus.PENDING, "date": date(2026, 2, 26), "feedback": None, "content": "During this period I developed enhancements for an Oracle Forms screen, wrote SQL queries to retrieve customer information, and worked closely with my mentor to understand deployment procedures."},
                {"status": ProgressReportStatus.PENDING, "date": date(2026, 3, 12), "feedback": None, "content": "I optimized SQL queries to improve report performance, corrected validation issues in Oracle Forms, and participated in user acceptance testing with business stakeholders."},
                {"status": ProgressReportStatus.PENDING, "date": date(2026, 3, 26), "feedback": None, "content": "I implemented minor feature requests, updated technical documentation, fixed reported defects, and assisted the development team during deployment preparation."}
            ]
        },
        "STU003": {
            "status": InternshipStatus.IN_PROGRESS,
            "acad_sup": "SUP003 - Dr. Ahmed Mostafa",
            "country": "Egypt", "faculty": "Engineering",
            "major1": "Mechatronics Engineering", "major2": None,
            "company": "Siemens Egypt", "title": "Automation Engineering Intern", "dept": "Industrial Automation",
            "start": date(2026, 1, 15), "end": date(2026, 6, 15),
            "entry": datetime(2026, 1, 8, 14, 0),
            "source": "Internship Booklet", "workplace": "Hybrid", "days": 5, "hours": 8,
            "desc": "Support PLC programming, automation testing, industrial control systems, technical documentation, and equipment commissioning.",
            "org_sup_name": "Hany Fathy", "org_sup_title": "Automation Team Lead", "org_sup_mob": "+20 102 777 8811",
            "cc_status": "accepted", "sup_status": "accepted", "cc_reason": "Approved.", "sup_reason": "Approved.",
            "acad_final": "waiting", "cc_final": "waiting",
            "proof": datetime(2026, 1, 9, 10, 0), "eval": datetime(2026, 6, 16, 10, 0),
            "reports": [
                {"status": ProgressReportStatus.APPROVED, "date": date(2026, 1, 29), "feedback": None, "content": "Familiarized with PLC programming environments and basic logic gates. Assisted in reviewing existing SCADA configurations for minor projects."},
                {"status": ProgressReportStatus.APPROVED, "date": date(2026, 2, 12), "feedback": None, "content": "Participated in equipment testing and verified sensor calibrations. Documented the results for the engineering team."},
                {"status": ProgressReportStatus.APPROVED, "date": date(2026, 2, 26), "feedback": None, "content": "Worked on automation troubleshooting for a simulated assembly line. Identified and resolved a timing issue in the control loop."},
                {"status": ProgressReportStatus.APPROVED, "date": date(2026, 3, 12), "feedback": None, "content": "Helped draft technical documentation for the newly installed industrial control systems. Shadowed senior engineers during commissioning support."},
                {"status": ProgressReportStatus.APPROVED, "date": date(2026, 3, 26), "feedback": None, "content": "Monitored production performance remotely and analyzed data logs for process optimization."},
                {"status": ProgressReportStatus.APPROVED, "date": date(2026, 4, 9), "feedback": None, "content": "Optimized control system parameters to reduce cycle time by 5%. Presented findings to the automation team lead."},
                {"status": ProgressReportStatus.APPROVED, "date": date(2026, 4, 23), "feedback": None, "content": "Assisted in writing a new PLC script for an upcoming manufacturing client. Conducted initial simulations."},
                {"status": ProgressReportStatus.APPROVED, "date": date(2026, 5, 7), "feedback": None, "content": "Configured HMI panels to display real-time sensor data. Conducted user interface testing with operators."},
                {"status": ProgressReportStatus.PENDING, "date": date(2026, 5, 21), "feedback": None, "content": "During this period I assisted in testing new PLC logic, verified safety interlocks, documented test results, and collaborated with senior engineers to resolve automation issues before deployment."},
                {"status": ProgressReportStatus.PENDING, "date": date(2026, 6, 4), "feedback": None, "content": "I participated in the final commissioning phase, monitored production performance after deployment, prepared technical documentation, and presented my completed work to the engineering team."}
            ]
        },
        "STU004": {
            "status": InternshipStatus.IN_PROGRESS,
            "acad_sup": "SUP004 - Dr. Yasmine Nabil",
            "country": "Egypt", "faculty": "Biotechnology",
            "major1": "Biotechnology", "major2": None,
            "company": "EVA Pharma", "title": "Quality Assurance Intern", "dept": "Quality Assurance",
            "start": date(2026, 1, 15), "end": date(2026, 6, 15),
            "entry": datetime(2026, 1, 14, 10, 0),
            "source": "Referral", "workplace": "On Site", "days": 5, "hours": 8,
            "desc": "Assist in quality inspections, laboratory documentation, compliance verification, and quality reporting.",
            "org_sup_name": "Dina Tarek", "org_sup_title": "QA Supervisor", "org_sup_mob": "+20 101 555 2211",
            "cc_status": "accepted", "sup_status": "accepted", "cc_reason": None, "sup_reason": None,
            "acad_final": "waiting", "cc_final": "waiting",
            "proof": datetime(2026, 1, 14, 10, 0), "eval": None,
            "reports": []
        },
        "STU005": {
            "status": InternshipStatus.IN_PROGRESS,
            "acad_sup": "SUP005 - Dr. Khaled Amin",
            "country": "Egypt", "faculty": "Architecture",
            "major1": "Architecture", "major2": "Urban Design",
            "company": "ECG Engineering Consultants Group", "title": "Architectural Design Intern", "dept": "Design Office",
            "start": date(2026, 1, 15), "end": date(2026, 6, 15),
            "entry": datetime(2026, 1, 13, 10, 0),
            "source": "LinkedIn", "workplace": "Hybrid", "days": 5, "hours": 8,
            "desc": "Assist with architectural drawings, BIM models, site coordination, and design documentation.",
            "org_sup_name": "Ahmed Ragab", "org_sup_title": "Senior Architect", "org_sup_mob": "+20 100 987 6543",
            "cc_status": "accepted", "sup_status": "accepted", "cc_reason": None, "sup_reason": None,
            "acad_final": "waiting", "cc_final": "waiting",
            "proof": datetime(2026, 1, 13, 10, 0), "eval": None,
            "reports": []
        },
        "STU006": {
            "status": InternshipStatus.IN_PROGRESS,
            "acad_sup": "SUP006 - Dr. Rania Fouad",
            "country": "Egypt", "faculty": "Pharmaceuticals Engineering",
            "major1": "Pharmaceutical Engineering", "major2": None,
            "company": "Pharco Pharmaceuticals", "title": "Production Engineering Intern", "dept": "Production",
            "start": date(2026, 1, 15), "end": date(2026, 6, 15),
            "entry": datetime(2026, 1, 15, 10, 0),
            "source": "Family Business", "workplace": "On Site", "days": 5, "hours": 8,
            "desc": "Support pharmaceutical production, process monitoring, documentation, GMP compliance, and production planning.",
            "org_sup_name": "Mahmoud Atef", "org_sup_title": "Production Manager", "org_sup_mob": "+20 102 333 1122",
            "cc_status": "accepted", "sup_status": "accepted", "cc_reason": None, "sup_reason": None,
            "acad_final": "waiting", "cc_final": "waiting",
            "proof": datetime(2026, 1, 15, 10, 0), "eval": None,
            "reports": []
        },
        "STU007": {
            "status": InternshipStatus.COMPLETED,
            "acad_sup": "SUP007 - Dr. Heba Salah",
            "country": "Egypt", "faculty": "Informatics and Computer Science",
            "major1": "Computer Science", "major2": "Artificial Intelligence",
            "company": "Microsoft Egypt", "title": "Software Engineering Intern", "dept": "Azure Development",
            "start": date(2026, 1, 15), "end": date(2026, 6, 15),
            "entry": datetime(2026, 1, 10, 10, 0),
            "source": "Career Fair", "workplace": "Hybrid", "days": 5, "hours": 8,
            "desc": "Develop cloud applications, implement backend services, perform testing, fix bugs, and participate in agile software development.",
            "org_sup_name": "Omar Ashraf", "org_sup_title": "Software Engineering Manager", "org_sup_mob": "+20 100 222 9988",
            "cc_status": "accepted", "sup_status": "accepted", "cc_reason": None, "sup_reason": None,
            "acad_final": "fulfilled", "cc_final": "fulfilled",
            "proof": datetime(2026, 1, 9, 10, 0), "eval": datetime(2026, 6, 16, 10, 0),
            "reports": [
                {"status": ProgressReportStatus.APPROVED, "date": date(2026, 1, 29), "feedback": None, "content": "Set up development environment, learned Azure core services, and familiarized with the CI/CD pipeline used for deployments."},
                {"status": ProgressReportStatus.APPROVED, "date": date(2026, 2, 12), "feedback": None, "content": "Implemented a basic backend REST API using ASP.NET Core for internal telemetry collection. Wrote unit tests for the endpoints."},
                {"status": ProgressReportStatus.APPROVED, "date": date(2026, 2, 26), "feedback": None, "content": "Integrated the telemetry API with an Azure SQL Database. Optimized entity framework queries to reduce latency."},
                {"status": ProgressReportStatus.APPROVED, "date": date(2026, 3, 12), "feedback": None, "content": "Worked on a frontend dashboard using React to visualize the telemetry data. Configured Azure App Service for hosting the dashboard."},
                {"status": ProgressReportStatus.APPROVED, "date": date(2026, 3, 26), "feedback": None, "content": "Participated in sprint planning and took ownership of three user stories related to user authentication via Microsoft Entra ID."},
                {"status": ProgressReportStatus.APPROVED, "date": date(2026, 4, 9), "feedback": None, "content": "Resolved bugs reported during integration testing. Reviewed pull requests from other interns and provided code feedback."},
                {"status": ProgressReportStatus.APPROVED, "date": date(2026, 4, 23), "feedback": None, "content": "Researched and implemented Azure Key Vault for securely storing API secrets. Updated technical documentation for the new architecture."},
                {"status": ProgressReportStatus.APPROVED, "date": date(2026, 5, 7), "feedback": None, "content": "Assisted in migrating legacy data processing scripts to Azure Functions, resulting in more scalable and cost-effective execution."},
                {"status": ProgressReportStatus.APPROVED, "date": date(2026, 5, 21), "feedback": None, "content": "Conducted a load testing session using Azure Load Testing to ensure the new architecture handles expected peak traffic."},
                {"status": ProgressReportStatus.APPROVED, "date": date(2026, 6, 4), "feedback": None, "content": "Finalized the project documentation, fixed minor UI glitches in the dashboard, and delivered a final presentation of the project to the engineering team."}
            ]
        }
    }
    
    for student in students:
        if student.student_id not in student_data:
            continue
            
        data = student_data[student.student_id]
        
        internship = Internship(
            student_id=student.id,
            company_name=data["company"],
            position=data["title"],
            departments=data["dept"],
            start_date=data["start"],
            end_date=data["end"],
            entry_date=data["entry"],
            status=data["status"],
            description=data["desc"],
            supervisor_name=data["org_sup_name"],
            supervisor_email="alialnaggar.h@gmail.com",
            supervisor_job_title=data["org_sup_title"],
            supervisor_mobile=data["org_sup_mob"],
            academic_supervisor_name=data["acad_sup"],
            academic_supervisor_id=data["acad_sup"].split(" ")[0],
            country=data["country"],
            faculty=data["faculty"],
            first_major=data["major1"],
            second_major=data["major2"],
            source_of_internship=data["source"],
            workplace=data["workplace"],
            days_per_week=data["days"],
            hours_per_day=data["hours"],
            proof_of_acceptance_uploaded_at=data["proof"],
            evaluation_form_uploaded_at=data["eval"],
            career_center_review_status=data["cc_status"],
            career_center_review_reason=data["cc_reason"],
            supervisor_review_status=data["sup_status"],
            supervisor_review_reason=data["sup_reason"],
            academic_final_status=data["acad_final"],
            career_center_final_status=data["cc_final"]
        )
        
        if data["status"] in [InternshipStatus.APPROVED, InternshipStatus.IN_PROGRESS, InternshipStatus.COMPLETED]:
            internship.approved_by = 1
            internship.approved_at = datetime.utcnow() - timedelta(days=80)
            
        session.add(internship)
        session.commit()
        session.refresh(internship)
        internships.append(internship)
        
        # Create reports
        for j, rep_data in enumerate(data["reports"]):
            dt_report = datetime.combine(rep_data["date"], datetime.min.time())
            
            report = InternshipProgressReport(
                internship_id=internship.id,
                report_number=j + 1,
                summary=rep_data["content"],
                status=rep_data["status"],
                review_notes=rep_data["feedback"],
                reviewed_by=1 if rep_data["status"] != ProgressReportStatus.PENDING else None,
                reviewed_at=datetime.utcnow() if rep_data["status"] != ProgressReportStatus.PENDING else None,
                created_at=dt_report,
                updated_at=dt_report
            )
            session.add(report)
            
        session.commit()

    logger.info(f"Created {len(internships)} deterministic internship records")



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


def create_exam_remark_test_fixtures(session: Session, courses: list):
    """Create specific deterministic test cases for exam remark testing."""
    test_student = User(
        student_id="STU-9999-0001",
        email="alialnaggar.h@gmail.com",
        full_name="Remark Test User",
        role=UserRole.STUDENT,
        hashed_password="demo_hash",
        is_active=True,
        is_foreigner=False,
        id_card_image_url="/static/images/id_card.png"
    )
    session.add(test_student)
    session.commit()
    session.refresh(test_student)

    test_courses = courses[:5]
    
    for course in test_courses:
        enrollment = CourseEnrollment(
            student_id=test_student.id,
            course_id=course.id,
            status=CourseEnrollmentStatus.ACTIVE
        )
        session.add(enrollment)
    session.commit()

    base_date = date.today()
    today_midnight = datetime.combine(base_date, datetime.min.time())
    fixtures = []

    def add_paired_fixtures(course_idx, title_suffix, score, max_score, is_pub, days_ago):
        if len(test_courses) > course_idx:
            cid = test_courses[course_idx].id
            pub_date = today_midnight - timedelta(days=days_ago) if is_pub else None
            # Midterm
            fixtures.append(Assessment(
                course_id=cid, student_id=test_student.id,
                assessment_type=AssessmentType.MIDTERM,
                title=f"Midterm ({title_suffix})",
                max_score=max_score, score=score, weight=1.0,
                is_published=is_pub, published_at=pub_date, due_date=base_date
            ))
            # Final
            fixtures.append(Assessment(
                course_id=cid, student_id=test_student.id,
                assessment_type=AssessmentType.FINAL,
                title=f"Final Exam ({title_suffix})",
                max_score=max_score, score=score, weight=1.5,
                is_published=is_pub, published_at=pub_date, due_date=base_date
            ))

    # Case 1: A+ Case (score=96, max=100)
    add_paired_fixtures(0, "A+ Case", 96.0, 100.0, True, 2)
    
    # Case 2: Boundary 87 (score=87, max=100)
    add_paired_fixtures(1, "Boundary 87", 87.0, 100.0, True, 2)
    
    # Case 3: Unpublished
    add_paired_fixtures(2, "Unpublished", None, 100.0, False, 0)
    
    # Case 4: Custom Max 75 (score=60, max=75)
    add_paired_fixtures(3, "Custom Max 75", 60.0, 75.0, True, 2)
    
    # Case 5: Older than 3 days
    add_paired_fixtures(4, "Old Publish", 85.0, 100.0, True, 7)
        
    for f in fixtures:
        session.add(f)
    session.commit()
    logger.info("Created exam remark test fixtures for Remark Test User (STU-9999-0001)")


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
    session.exec(delete(InternshipProgressReport))
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
    
    # Add deterministic fixtures
    create_exam_remark_test_fixtures(session, courses)

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
