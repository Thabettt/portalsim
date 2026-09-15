#!/usr/bin/env python3
"""
Database seeding script for University Portal Simulator.
Seeds 100 students with complete Course Enrollments, Attendance, Payments,
Assessments, and Internship records according to exact business rules.
The first 7 student cases (STU001-STU007) strictly adhere to specified test scenarios.

Run with: python seed.py
Or use the admin endpoint: POST /admin/seed
"""

import random
from datetime import datetime, date, timedelta
from sqlmodel import Session, select, delete
from app.db import engine, create_db_and_tables
from app.models import (
    User, Course, CourseEnrollment, Attendance, Payment,
    Assessment, Internship, InternshipProgressReport, WebhookSetting, SystemSetting,
    WebhookLog, CourseSchedule, CourseInstructor,
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

# Seed Data Lists
FIRST_NAMES = [
    "Abdulaziz", "Ali", "Lakshy", "Mohamed", "Ahmed", "Sara", "Omar", "Mariam",
    "Youssef", "Nouran", "Fatma", "Khaled", "Tarek", "Nada", "Amr", "Mennatullah",
    "Hala", "Karim", "Rola", "Salma", "Yasmine", "Rania", "Ghada", "Nasser",
    "Farah", "Hoda", "Mostafa", "Hassan", "Essam", "Aisha", "Laila", "Sherif",
    "Dina", "Adel", "Ziad", "Hisham", "Nour", "Seif", "Ayman", "Reem",
    "Layla", "Tamer", "Noha", "Habiba", "Wael", "Mona", "Ibrahim", "Malak",
    "Samy", "Bassem"
]

LAST_NAMES = [
    "Hassan", "Ali", "Mahmoud", "Adel", "Ibrahim", "El-Din", "Abdelrahman", "Yassin",
    "Badr", "Galal", "Kamel", "Hafez", "Ahmed", "Farouk", "Saeed", "Said",
    "Magdy", "Samir", "Zaki", "Nabil", "Hossam", "Saleh", "Fares", "Tarek",
    "Gomaa", "Ashraf", "Essam", "Riad", "Ayman", "Mostafa", "Helmy", "Omar",
    "Shawky", "Khaled", "Wael", "Fouad", "Salah", "El-Sayed", "Amin", "Nasser"
]

FACULTIES = [
    "Faculty of Engineering & IT",
    "Faculty of Computer Science",
    "Faculty of Business Administration",
    "Faculty of Applied Sciences"
]

MAJORS = [
    ("Computer Science", "Software Engineering"),
    ("Software Engineering", "Artificial Intelligence"),
    ("Data Science", "Computer Science"),
    ("DevOps", "Software Engineering"),
    ("Cybersecurity", "Computer Networks"),
    ("Artificial Intelligence", "Data Science"),
    ("Business Informatics", "Management")
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
    ("John Zaki", "INS-2024-0001", "j.fayez@gmail.com", "Professor"),
    ("Mohamed El-Maadawy", "INS-2024-0002", "mo.elmaadawy1@gmail.com", "TA"),
    ("Lakshy Rupani", "INS-2024-0003", "lakshyrupani.lr+ta@gmail.com", "TA"),
    ("Dr. Mahmoud Hassan", "INS-2024-0004", "m.hassan@university.edu", "Professor"),
    ("Dr. Mona Ibrahim", "INS-2024-0005", "m.ibrahim@university.edu", "Professor"),
    ("Dr. Ahmed Mostafa", "INS-2024-0006", "a.mostafa@university.edu", "Professor"),
    ("Dr. Yasmine Nabil", "INS-2024-0007", "y.nabil@university.edu", "TA"),
    ("Dr. Khaled Amin", "INS-2024-0008", "k.amin@university.edu", "TA"),
    ("Dr. Rania Fouad", "INS-2024-0009", "r.fouad@university.edu", "Professor"),
    ("Dr. Heba Salah", "INS-2024-0010", "h.salah@university.edu", "TA"),
]

EXAM_OFFICERS = [
    ("Ali El-Naggar", "ADM-2024-0001", "alialnaggar.h+admin@gmail.com"),
    ("Admin Officer", "ADM-2024-0002", "admin@university.edu"),
]

ORGANIZATIONS = [
    ("TechCorp Egypt", "Cairo", "Software Engineering"),
    ("Digital Solutions", "Alexandria", "Data Analytics"),
    ("CloudTech Systems", "Cairo", "DevOps & Infrastructure"),
    ("AI Innovations", "Giza", "Machine Learning"),
    ("FinTech Solutions", "Cairo", "Backend Development"),
    ("CyberSec Labs", "Alexandria", "Cybersecurity"),
    ("MobileFirst", "Cairo", "Mobile App Development"),
    ("DataFlow Analytics", "Smart Village", "Big Data"),
    ("Valeo Egypt", "Smart Village", "Embedded Systems"),
    ("Vodafone Intelligent Solutions", "Cairo", "Cloud Architecture"),
    ("Siemens Healthineers", "Cairo", "Medical Software"),
    ("Swvl", "Cairo", "Platform Engineering"),
    ("Instabug", "Cairo", "SDK Development"),
    ("Paymob", "Cairo", "Payment Systems"),
    ("Fawry", "Cairo", "Financial Tech"),
    ("Trend Micro Egypt", "Cairo", "Security Operations"),
    ("Dell Technologies", "Cairo", "Enterprise Solutions"),
    ("Amazon Egypt", "Cairo", "E-Commerce Logistics Tech"),
    ("Microsoft Cairo Lab", "Cairo", "AI Research"),
    ("Oracle Egypt", "Cairo", "Database Applications"),
]

WORKPLACE_TYPES = ["On-site", "Hybrid", "Remote"]
INTERNSHIP_SOURCES = [
    "Career Fair", "LinkedIn", "Referral", "Family Business",
    "Internship Booklet", "University Portal", "Direct Application"
]

REJECTION_REASONS = [
    "Organization scope of work does not align with major requirements.",
    "Documentation insufficient or unverified organization.",
    "Job description does not meet technical rigor criteria.",
    "Supervisor credentials could not be verified by Career Center.",
    "Proposed internship timeline conflicts with academic calendar."
]


def generate_student_id(sequence: int) -> str:
    return f"STU{sequence:03d}"


def seed_database():
    """Main database seeding function for 100 students and all entities"""
    logger.info("Starting database seeding for 100 students...")

    with Session(engine) as session:
        # 1. Clean existing records
        logger.info("Cleaning existing database tables...")
        session.exec(delete(InternshipProgressReport))
        session.exec(delete(Internship))
        session.exec(delete(Assessment))
        session.exec(delete(Payment))
        session.exec(delete(Attendance))
        session.exec(delete(CourseEnrollment))
        session.exec(delete(CourseInstructor))
        session.exec(delete(CourseSchedule))
        session.exec(delete(Course))
        session.exec(delete(User))
        session.exec(delete(WebhookLog))
        session.exec(delete(WebhookSetting))
        session.exec(delete(SystemSetting))
        session.commit()

        # 2. Create System Settings & Webhook Settings
        session.add(SystemSetting(key="academic_year", value="2024-2025"))
        session.add(SystemSetting(key="current_semester", value="Fall 2024"))
        session.add(WebhookSetting(
            webhook_target_url=settings.webhook_target_url or "http://localhost:8080/webhook",
            shared_secret=settings.shared_secret,
            is_active=True
        ))
        session.commit()

        # 3. Create Instructors & Exam Officers
        logger.info("Creating Instructors and Exam Officers...")
        instructor_objs = []
        for name, ins_id, email, ins_type in INSTRUCTORS:
            user = User(
                student_id=ins_id,
                email=email,
                full_name=name,
                role=UserRole.INSTRUCTOR,
                hashed_password="demo_hash",
                is_active=True
            )
            session.add(user)
            instructor_objs.append((user, ins_type))
        
        for name, admin_id, email in EXAM_OFFICERS:
            admin = User(
                student_id=admin_id,
                email=email,
                full_name=name,
                role=UserRole.EXAM_OFFICER,
                hashed_password="demo_hash",
                is_active=True
            )
            session.add(admin)
        session.commit()

        for inst, _ in instructor_objs:
            session.refresh(inst)

        # 4. Create Courses & Assign Instructors
        logger.info("Creating Courses...")
        course_objs = []
        for code, name, semester, credits in COURSES:
            course = Course(
                code=code,
                name=name,
                description=f"Standard curriculum course: {name}",
                credits=credits,
                semester=semester,
                is_active=True
            )
            session.add(course)
            course_objs.append(course)
        session.commit()
        for c in course_objs:
            session.refresh(c)

        for i, course in enumerate(course_objs):
            inst, inst_type = instructor_objs[i % len(instructor_objs)]
            session.add(CourseInstructor(course_id=course.id, instructor_id=inst.id, instructor_type=inst_type))
            for week in range(1, 13):
                session.add(CourseSchedule(course_id=course.id, week_number=week, weekday=(i % 5)))
        session.commit()

        # 5. Create 100 Students (First 7 students match exact specified cases)
        logger.info("Creating 100 Students...")
        students = []

        FIRST_7_STUDENTS = [
            ("STU001", "Ahmed Mohamed Hassan", "alialnaggar.h@gmail.com", False),
            ("STU002", "Sara Ahmed Ali", "alialnaggar.h@gmail.com", False),
            ("STU003", "Omar Khaled Mahmoud", "alialnaggar.h@gmail.com", False),
            ("STU004", "Mariam Sherif Adel", "alialnaggar.h@gmail.com", False),
            ("STU005", "Youssef Adel Ibrahim", "alialnaggar.h@gmail.com", False),
            ("STU006", "Nouran Hossam El-Din", "alialnaggar.h@gmail.com", False),
            ("STU007", "Fatma Wael Abdelrahman", "alialnaggar.h@gmail.com", False),
        ]

        for stu_id, name, email, is_for in FIRST_7_STUDENTS:
            student = User(
                student_id=stu_id,
                email=email,
                full_name=name,
                role=UserRole.STUDENT,
                hashed_password="demo_hash",
                is_active=True,
                is_foreigner=is_for,
                id_card_image_url="/static/images/id_card.png"
            )
            session.add(student)
            students.append(student)

        # Generate remaining 93 students (STU008 to STU100)
        for i in range(8, 101):
            fname = FIRST_NAMES[(i - 1) % len(FIRST_NAMES)]
            lname = LAST_NAMES[(i - 1) % len(LAST_NAMES)]
            stu_id = generate_student_id(i)
            email = f"student{i:03d}@university.edu"
            is_foreigner = (i % 10 == 0)

            student = User(
                student_id=stu_id,
                email=email,
                full_name=f"{fname} {lname}",
                role=UserRole.STUDENT,
                hashed_password="demo_hash",
                is_active=True,
                is_foreigner=is_foreigner,
                id_card_image_url="/static/images/id_card.png"
            )
            session.add(student)
            students.append(student)

        # Remark test user fixture
        remark_test_user = User(
            student_id="STU-9999-0001",
            email="thabetology+testuser@gmail.com",
            full_name="Remark Test User",
            role=UserRole.STUDENT,
            hashed_password="demo_hash",
            is_active=True,
            is_foreigner=False,
            id_card_image_url="/static/images/id_card.png"
        )
        session.add(remark_test_user)

        session.commit()
        for s in students:
            session.refresh(s)
        session.refresh(remark_test_user)
        logger.info(f"Created {len(students)} students + 1 test fixture student.")

        # 6. Enroll Students in Courses
        logger.info("Enrolling students in courses...")
        all_student_objs = students + [remark_test_user]
        student_enrollments = {}

        for idx, student in enumerate(all_student_objs):
            num_courses = 4 + (idx % 3)
            enrolled_courses = [course_objs[(idx + c) % len(course_objs)] for c in range(num_courses)]
            student_enrollments[student.id] = enrolled_courses

            for course in enrolled_courses:
                session.add(CourseEnrollment(
                    student_id=student.id,
                    course_id=course.id,
                    enrolled_at=datetime.utcnow() - timedelta(days=120),
                    status=CourseEnrollmentStatus.ACTIVE
                ))
        session.commit()

        # 7. Generate Attendance Records
        logger.info("Generating attendance records...")
        today_date = date.today()
        base_start_date = today_date - timedelta(weeks=12)

        for student in all_student_objs:
            enrolled = student_enrollments[student.id]
            for c_idx, course in enumerate(enrolled):
                total_weeks = 12
                if (student.id + c_idx) % 15 == 0:
                    absent_count = 4
                elif (student.id + c_idx) % 9 == 0:
                    absent_count = 3
                elif (student.id + c_idx) % 5 == 0:
                    absent_count = 2
                else:
                    absent_count = random.choice([0, 1])

                absent_weeks = set(range(1, absent_count + 1))

                for week in range(1, total_weeks + 1):
                    session_date = base_start_date + timedelta(weeks=week-1, days=(c_idx % 5))
                    status = AttendanceStatus.ABSENT if week in absent_weeks else AttendanceStatus.PRESENT
                    current_absents = len([w for w in range(1, week + 1) if w in absent_weeks])
                    w_level = calculate_warning_level(current_absents, total_weeks)

                    session.add(Attendance(
                        student_id=student.id,
                        course_id=course.id,
                        date=session_date,
                        status=status,
                        warning_level=w_level,
                        notes=f"Week {week} session" if status == AttendanceStatus.ABSENT else None,
                        marked_at=datetime.combine(session_date, datetime.min.time())
                    ))
        session.commit()

        # 8. Generate Payments
        logger.info("Generating payment records...")
        for idx, student in enumerate(all_student_objs):
            t_status = PaymentStatus.PAID if idx % 4 != 0 else (PaymentStatus.OVERDUE if idx % 2 == 0 else PaymentStatus.PENDING)
            session.add(Payment(
                student_id=student.id,
                payment_type=PaymentType.TUITION,
                amount=15000.0,
                due_date=today_date - timedelta(days=30),
                status=t_status,
                paid_amount=15000.0 if t_status == PaymentStatus.PAID else 0.0,
                paid_at=datetime.utcnow() - timedelta(days=45) if t_status == PaymentStatus.PAID else None,
                description="Tuition Fee - Fall 2024",
                invoice_number=f"INV-TUITION-2024-{student.id:04d}",
                currency="EGP"
            ))

            l_status = PaymentStatus.PAID if idx % 3 != 0 else PaymentStatus.PENDING
            session.add(Payment(
                student_id=student.id,
                payment_type=PaymentType.LAB_FEE,
                amount=2000.0,
                due_date=today_date - timedelta(days=15),
                status=l_status,
                paid_amount=2000.0 if l_status == PaymentStatus.PAID else 0.0,
                paid_at=datetime.utcnow() - timedelta(days=20) if l_status == PaymentStatus.PAID else None,
                description="Lab Fee - Fall 2024",
                invoice_number=f"INV-LAB-2024-{student.id:04d}",
                currency="EGP"
            ))

            session.add(Payment(
                student_id=student.id,
                payment_type=PaymentType.LIBRARY_FEE,
                amount=500.0,
                due_date=today_date + timedelta(days=15),
                status=PaymentStatus.PAID if idx % 2 == 0 else PaymentStatus.PENDING,
                paid_amount=500.0 if idx % 2 == 0 else 0.0,
                paid_at=datetime.utcnow() - timedelta(days=5) if idx % 2 == 0 else None,
                description="Library Fee - Fall 2024",
                invoice_number=f"INV-LIB-2024-{student.id:04d}",
                currency="EGP"
            ))

            if idx % 7 == 0 or student.student_id in ("STU-9999-0001", "STU001"):
                session.add(Payment(
                    student_id=student.id,
                    payment_type=PaymentType.EXAM_FEE,
                    amount=500.0,
                    due_date=today_date + timedelta(days=10),
                    status=PaymentStatus.PENDING,
                    paid_amount=0.0,
                    description="Exam Remark Charge - CS-201 Midterm Re-evaluation",
                    invoice_number=f"INV-REMARK-2024-{student.id:04d}",
                    external_reference_id=f"REMARK-REF-{student.id:04d}",
                    source="exam_remark",
                    currency="EGP"
                ))
        session.commit()

        # 9. Generate Assessments
        logger.info("Generating assessment records...")
        for student in all_student_objs:
            enrolled = student_enrollments[student.id]
            for c_idx, course in enumerate(enrolled):
                session.add(Assessment(
                    course_id=course.id,
                    student_id=student.id,
                    assessment_type=AssessmentType.QUIZ,
                    title=f"Quiz 1 - {course.code}",
                    max_score=20.0,
                    score=float(random.randint(14, 20)),
                    weight=0.5,
                    is_published=True,
                    published_at=datetime.utcnow() - timedelta(days=40),
                    due_date=today_date - timedelta(days=42)
                ))

                session.add(Assessment(
                    course_id=course.id,
                    student_id=student.id,
                    assessment_type=AssessmentType.MIDTERM,
                    title=f"Midterm Exam - {course.code}",
                    max_score=100.0,
                    score=float(random.randint(65, 98)),
                    weight=1.0,
                    is_published=True,
                    published_at=datetime.utcnow() - timedelta(days=20),
                    due_date=today_date - timedelta(days=22)
                ))

                session.add(Assessment(
                    course_id=course.id,
                    student_id=student.id,
                    assessment_type=AssessmentType.FINAL,
                    title=f"Final Exam - {course.code}",
                    max_score=100.0,
                    score=float(random.randint(70, 99)),
                    weight=1.5,
                    is_published=True,
                    published_at=datetime.utcnow() - timedelta(days=5),
                    due_date=today_date - timedelta(days=7)
                ))
        session.commit()

        # 10. Generate Internships & Progress Reports for ALL 100 Students
        logger.info("Generating Internship records matching exact specified student cases...")

        start_date = date(2024, 1, 15)
        end_date = date(2024, 6, 30)
        proof_uploaded_dt = datetime.utcnow() - timedelta(days=120)
        eval_uploaded_dt = datetime.utcnow() - timedelta(days=10)

        for i, student in enumerate(students):
            faculty = FACULTIES[i % len(FACULTIES)]
            f_major, s_major = MAJORS[i % len(MAJORS)]
            org_name, org_city, org_dept = ORGANIZATIONS[i % len(ORGANIZATIONS)]
            workplace = WORKPLACE_TYPES[i % len(WORKPLACE_TYPES)]
            source = INTERNSHIP_SOURCES[i % len(INTERNSHIP_SOURCES)]

            inst_obj, _ = instructor_objs[i % len(instructor_objs)]
            academic_supervisor_name = inst_obj.full_name
            academic_supervisor_email = inst_obj.email

            org_supervisor_name = f"Eng. {FIRST_NAMES[(i+3) % len(FIRST_NAMES)]} {LAST_NAMES[(i+5) % len(LAST_NAMES)]}"
            org_supervisor_title = "Senior Technical Manager"
            org_supervisor_email = f"sup.{student.student_id.lower()}@{org_name.lower().replace(' ', '')}.com"
            org_supervisor_mobile = f"+201{random.choice(['0','1','2'])}{random.randint(10000000, 99999999)}"

            # -------------------------------------------------------------
            # SPECIFIC CASE 1: STU001 (Ahmed Mohamed Hassan) - Pending Review
            # -------------------------------------------------------------
            if i == 0:
                internship = Internship(
                    student_id=student.id,
                    company_name="TechCorp Egypt",
                    position="Software Engineering Intern",
                    start_date=start_date,
                    end_date=end_date,
                    status=InternshipStatus.PENDING,
                    description="Software engineering internship pending career center review.",
                    academic_supervisor_name=academic_supervisor_name,
                    academic_supervisor_id="SUP001",
                    supervisor_name=org_supervisor_name,
                    supervisor_email=org_supervisor_email,
                    supervisor_job_title=org_supervisor_title,
                    supervisor_mobile=org_supervisor_mobile,
                    country="Egypt",
                    faculty="Faculty of Computer Science",
                    first_major="Software Engineering",
                    second_major="Artificial Intelligence",
                    source_of_internship="Career Fair",
                    workplace="Hybrid",
                    departments="Software Engineering",
                    days_per_week=5,
                    hours_per_day=8,
                    entry_date=datetime.utcnow() - timedelta(days=60),
                    proof_of_acceptance_uploaded_at=proof_uploaded_dt,
                    evaluation_form_uploaded_at=None,
                    career_center_review_status="Pending",
                    supervisor_review_status="Pending",
                    academic_final_status="Waiting",
                    career_center_final_status="Waiting"
                )
                session.add(internship)
                # 0 progress reports

            # -------------------------------------------------------------
            # SPECIFIC CASE 2: STU002, STU003, STU004 - Accepted (No Reports)
            # -------------------------------------------------------------
            elif i in (1, 2, 3):
                internship = Internship(
                    student_id=student.id,
                    company_name=org_name,
                    position=f"{f_major} Intern",
                    start_date=start_date,
                    end_date=end_date,
                    status=InternshipStatus.APPROVED,
                    description=f"Approved {f_major} internship awaiting progress reports.",
                    academic_supervisor_name=academic_supervisor_name,
                    academic_supervisor_id=f"SUP{(i%10)+1:03d}",
                    supervisor_name=org_supervisor_name,
                    supervisor_email=org_supervisor_email,
                    supervisor_job_title=org_supervisor_title,
                    supervisor_mobile=org_supervisor_mobile,
                    country="Egypt",
                    faculty=faculty,
                    first_major=f_major,
                    second_major=s_major,
                    source_of_internship=source,
                    workplace=workplace,
                    departments=org_dept,
                    days_per_week=5,
                    hours_per_day=8,
                    entry_date=datetime.utcnow() - timedelta(days=90),
                    proof_of_acceptance_uploaded_at=proof_uploaded_dt,
                    evaluation_form_uploaded_at=None,
                    career_center_review_status="Accepted",
                    supervisor_review_status="Accepted",
                    academic_final_status="Waiting",
                    career_center_final_status="Waiting"
                )
                session.add(internship)
                # 0 progress reports

            # -------------------------------------------------------------
            # SPECIFIC CASE 3: STU005 (Youssef Adel Ibrahim) - In Progress (5 Reports)
            # -------------------------------------------------------------
            elif i == 4:
                internship = Internship(
                    student_id=student.id,
                    company_name=org_name,
                    position=f"{f_major} Intern",
                    start_date=start_date,
                    end_date=end_date,
                    status=InternshipStatus.IN_PROGRESS,
                    description="In-progress internship with 5 submitted reports (3 accepted, 1 pending, 1 rejected).",
                    academic_supervisor_name=academic_supervisor_name,
                    academic_supervisor_id="SUP005",
                    supervisor_name=org_supervisor_name,
                    supervisor_email=org_supervisor_email,
                    supervisor_job_title=org_supervisor_title,
                    supervisor_mobile=org_supervisor_mobile,
                    country="Egypt",
                    faculty=faculty,
                    first_major=f_major,
                    second_major=s_major,
                    source_of_internship=source,
                    workplace=workplace,
                    departments=org_dept,
                    days_per_week=5,
                    hours_per_day=8,
                    entry_date=datetime.utcnow() - timedelta(days=120),
                    proof_of_acceptance_uploaded_at=proof_uploaded_dt,
                    evaluation_form_uploaded_at=None,
                    career_center_review_status="Accepted",
                    supervisor_review_status="Accepted",
                    academic_final_status="Waiting",
                    career_center_final_status="Waiting"
                )
                session.add(internship)
                session.commit()
                session.refresh(internship)

                # 5 Reports: 3 Accepted, 1 Pending, 1 Rejected with feedback
                reports_data = [
                    (1, ProgressReportStatus.APPROVED, "Approved by Academic Supervisor."),
                    (2, ProgressReportStatus.APPROVED, "Approved by Academic Supervisor."),
                    (3, ProgressReportStatus.APPROVED, "Approved by Academic Supervisor."),
                    (4, ProgressReportStatus.PENDING, None),
                    (5, ProgressReportStatus.REJECTED, "Re-submit section 3 with detailed architecture diagram.")
                ]
                for r_num, r_status, r_notes in reports_data:
                    sub_date = datetime.utcnow() - timedelta(days=100 - (r_num * 15))
                    session.add(InternshipProgressReport(
                        internship_id=internship.id,
                        report_number=r_num,
                        summary=f"Progress report #{r_num}: Milestone review and sprint submission.",
                        status=r_status,
                        review_notes=r_notes,
                        submitted_at=sub_date,
                        reviewed_at=sub_date + timedelta(days=1) if r_status != ProgressReportStatus.PENDING else None
                    ))

            # -------------------------------------------------------------
            # SPECIFIC CASE 4: STU006 (Nouran Hossam El-Din) - Nearly Complete (8 Accepted, 1 Pending -> Academic Fulfillment = Waiting)
            # -------------------------------------------------------------
            elif i == 5:
                internship = Internship(
                    student_id=student.id,
                    company_name=org_name,
                    position=f"{f_major} Intern",
                    start_date=start_date,
                    end_date=end_date,
                    status=InternshipStatus.IN_PROGRESS,
                    description="Nearly complete internship with 8 accepted and 1 pending report.",
                    academic_supervisor_name=academic_supervisor_name,
                    academic_supervisor_id="SUP006",
                    supervisor_name=org_supervisor_name,
                    supervisor_email=org_supervisor_email,
                    supervisor_job_title=org_supervisor_title,
                    supervisor_mobile=org_supervisor_mobile,
                    country="Egypt",
                    faculty=faculty,
                    first_major=f_major,
                    second_major=s_major,
                    source_of_internship=source,
                    workplace=workplace,
                    departments=org_dept,
                    days_per_week=5,
                    hours_per_day=8,
                    entry_date=datetime.utcnow() - timedelta(days=130),
                    proof_of_acceptance_uploaded_at=proof_uploaded_dt,
                    evaluation_form_uploaded_at=None,
                    career_center_review_status="Accepted",
                    supervisor_review_status="Accepted",
                    academic_final_status="Waiting",  # EXPLICITLY WAITING per STU006 constraint!
                    career_center_final_status="Waiting"
                )
                session.add(internship)
                session.commit()
                session.refresh(internship)

                # 9 Reports: 8 Accepted, 1 Pending
                for r_num in range(1, 10):
                    r_status = ProgressReportStatus.APPROVED if r_num <= 8 else ProgressReportStatus.PENDING
                    sub_date = datetime.utcnow() - timedelta(days=120 - (r_num * 10))
                    session.add(InternshipProgressReport(
                        internship_id=internship.id,
                        report_number=r_num,
                        summary=f"Progress report #{r_num}: System architecture, integration tests, and documentation.",
                        status=r_status,
                        review_notes="Approved by Academic Supervisor." if r_status == ProgressReportStatus.APPROVED else None,
                        submitted_at=sub_date,
                        reviewed_at=sub_date + timedelta(days=1) if r_status == ProgressReportStatus.APPROVED else None
                    ))

            # -------------------------------------------------------------
            # SPECIFIC CASE 5: STU007 (Fatma Wael Abdelrahman) - Waiting for Final CC Review (9 Accepted, Academic = Fulfilled, CC Final = Waiting)
            # -------------------------------------------------------------
            elif i == 6:
                internship = Internship(
                    student_id=student.id,
                    company_name=org_name,
                    position=f"{f_major} Intern",
                    start_date=start_date,
                    end_date=end_date,
                    status=InternshipStatus.IN_PROGRESS,
                    description="Completed 9 progress reports and evaluation form uploaded; waiting for final Career Center sign-off.",
                    academic_supervisor_name=academic_supervisor_name,
                    academic_supervisor_id="SUP007",
                    supervisor_name=org_supervisor_name,
                    supervisor_email=org_supervisor_email,
                    supervisor_job_title=org_supervisor_title,
                    supervisor_mobile=org_supervisor_mobile,
                    country="Egypt",
                    faculty=faculty,
                    first_major=f_major,
                    second_major=s_major,
                    source_of_internship=source,
                    workplace=workplace,
                    departments=org_dept,
                    days_per_week=5,
                    hours_per_day=8,
                    entry_date=datetime.utcnow() - timedelta(days=130),
                    proof_of_acceptance_uploaded_at=proof_uploaded_dt,
                    evaluation_form_uploaded_at=eval_uploaded_dt,
                    career_center_review_status="Accepted",
                    supervisor_review_status="Accepted",
                    academic_final_status="Fulfilled",
                    career_center_final_status="Waiting"
                )
                session.add(internship)
                session.commit()
                session.refresh(internship)

                # 9 Accepted Reports
                for r_num in range(1, 10):
                    sub_date = datetime.utcnow() - timedelta(days=120 - (r_num * 10))
                    session.add(InternshipProgressReport(
                        internship_id=internship.id,
                        report_number=r_num,
                        summary=f"Progress report #{r_num}: Final milestones and thesis documentation.",
                        status=ProgressReportStatus.APPROVED,
                        review_notes="Approved by Academic Supervisor.",
                        submitted_at=sub_date,
                        reviewed_at=sub_date + timedelta(days=1)
                    ))

            # -------------------------------------------------------------
            # REMAINING STUDENTS: Indices 7 to 99 (STU008 to STU100)
            # -------------------------------------------------------------
            else:
                # Category 1: Pending (Indices 7..24 ~ 18%)
                if i < 25:
                    internship = Internship(
                        student_id=student.id,
                        company_name=org_name,
                        position=f"{f_major} Intern",
                        start_date=start_date,
                        end_date=end_date,
                        status=InternshipStatus.PENDING,
                        description=f"5-month internship focusing on {f_major}.",
                        academic_supervisor_name=academic_supervisor_name,
                        academic_supervisor_id=f"SUP{(i%10)+1:03d}",
                        supervisor_name=org_supervisor_name,
                        supervisor_email=org_supervisor_email,
                        supervisor_job_title=org_supervisor_title,
                        supervisor_mobile=org_supervisor_mobile,
                        country="Egypt",
                        faculty=faculty,
                        first_major=f_major,
                        second_major=s_major,
                        source_of_internship=source,
                        workplace=workplace,
                        departments=org_dept,
                        days_per_week=5,
                        hours_per_day=8,
                        entry_date=datetime.utcnow() - timedelta(days=60),
                        proof_of_acceptance_uploaded_at=proof_uploaded_dt,
                        evaluation_form_uploaded_at=None,
                        career_center_review_status="Pending",
                        supervisor_review_status="Pending",
                        academic_final_status="Waiting",
                        career_center_final_status="Waiting"
                    )
                    session.add(internship)

                # Category 2: Rejected (Indices 25..34 ~ 10%)
                elif i < 35:
                    reason = REJECTION_REASONS[(i - 25) % len(REJECTION_REASONS)]
                    internship = Internship(
                        student_id=student.id,
                        company_name=org_name,
                        position=f"{f_major} Intern",
                        start_date=start_date,
                        end_date=end_date,
                        status=InternshipStatus.REJECTED,
                        description=f"Application for {f_major} internship.",
                        academic_supervisor_name=academic_supervisor_name,
                        academic_supervisor_id=f"SUP{(i%10)+1:03d}",
                        supervisor_name=org_supervisor_name,
                        supervisor_email=org_supervisor_email,
                        supervisor_job_title=org_supervisor_title,
                        supervisor_mobile=org_supervisor_mobile,
                        country="Egypt",
                        faculty=faculty,
                        first_major=f_major,
                        second_major=s_major,
                        source_of_internship=source,
                        workplace=workplace,
                        departments=org_dept,
                        days_per_week=5,
                        hours_per_day=8,
                        entry_date=datetime.utcnow() - timedelta(days=90),
                        proof_of_acceptance_uploaded_at=proof_uploaded_dt,
                        evaluation_form_uploaded_at=None,
                        career_center_review_status="Rejected",
                        career_center_review_reason=reason,
                        supervisor_review_status="Rejected",
                        supervisor_review_reason=reason,
                        rejection_reason=reason,
                        academic_final_status="Waiting",
                        career_center_final_status="Waiting"
                    )
                    session.add(internship)

                # Category 3: Accepted (Indices 35..99 ~ 65%)
                else:
                    if i < 80:  # < 8 accepted reports -> Academic Waiting
                        num_reports = 1 + ((i - 35) % 7)
                        academic_fulfillment = "Waiting"
                        career_final = "Waiting"
                        eval_date = None
                        int_status = InternshipStatus.IN_PROGRESS if num_reports < 7 else InternshipStatus.APPROVED
                    else:  # >= 8 accepted reports -> Academic Fulfilled
                        num_reports = 8 + ((i - 80) % 3)
                        academic_fulfillment = "Fulfilled"
                        if i <= 90:  # Full CC Fulfillment
                            eval_date = eval_uploaded_dt
                            career_final = "Fulfilled"
                            int_status = InternshipStatus.COMPLETED
                        else:  # CC Waiting
                            eval_date = None
                            career_final = "Waiting"
                            int_status = InternshipStatus.IN_PROGRESS

                    internship = Internship(
                        student_id=student.id,
                        company_name=org_name,
                        position=f"{f_major} Intern",
                        start_date=start_date,
                        end_date=end_date,
                        status=int_status,
                        description=f"Comprehensive 5-month internship in {f_major} at {org_name}.",
                        academic_supervisor_name=academic_supervisor_name,
                        academic_supervisor_id=f"SUP{(i%10)+1:03d}",
                        supervisor_name=org_supervisor_name,
                        supervisor_email=org_supervisor_email,
                        supervisor_job_title=org_supervisor_title,
                        supervisor_mobile=org_supervisor_mobile,
                        country="Egypt",
                        faculty=faculty,
                        first_major=f_major,
                        second_major=s_major,
                        source_of_internship=source,
                        workplace=workplace,
                        departments=org_dept,
                        days_per_week=5,
                        hours_per_day=8,
                        entry_date=datetime.utcnow() - timedelta(days=130),
                        proof_of_acceptance_uploaded_at=proof_uploaded_dt,
                        evaluation_form_uploaded_at=eval_date,
                        career_center_review_status="Accepted",
                        supervisor_review_status="Accepted",
                        academic_final_status=academic_fulfillment,
                        career_center_final_status=career_final
                    )
                    session.add(internship)
                    session.commit()
                    session.refresh(internship)

                    for r_num in range(1, num_reports + 1):
                        report_sub_date = datetime.utcnow() - timedelta(days=120 - (r_num * 10))
                        session.add(InternshipProgressReport(
                            internship_id=internship.id,
                            report_number=r_num,
                            summary=f"Progress report #{r_num}: Milestone review.",
                            status=ProgressReportStatus.APPROVED,
                            review_notes=f"Approved by Academic Supervisor {academic_supervisor_name}.",
                            submitted_at=report_sub_date,
                            reviewed_at=report_sub_date + timedelta(days=1)
                        ))

        session.commit()

        # Remark test user fixture internship
        test_internship = Internship(
            student_id=remark_test_user.id,
            company_name="TechCorp Egypt",
            position="Software Engineering Intern",
            start_date=start_date,
            end_date=end_date,
            status=InternshipStatus.APPROVED,
            description="Test fixture internship",
            academic_supervisor_name="Dr. Mahmoud Hassan",
            academic_supervisor_id="SUP001",
            supervisor_name="Eng. Omar Hassan",
            supervisor_email="sup.test@techcorp.com",
            supervisor_job_title="Engineering Lead",
            supervisor_mobile="+201012345678",
            country="Egypt",
            faculty="Faculty of Computer Science",
            first_major="Computer Science",
            source_of_internship="Career Fair",
            workplace="Hybrid",
            departments="Software Engineering",
            days_per_week=5,
            hours_per_day=8,
            entry_date=datetime.utcnow() - timedelta(days=120),
            proof_of_acceptance_uploaded_at=proof_uploaded_dt,
            evaluation_form_uploaded_at=eval_uploaded_dt,
            career_center_review_status="Accepted",
            supervisor_review_status="Accepted",
            academic_final_status="Fulfilled",
            career_center_final_status="Fulfilled"
        )
        session.add(test_internship)
        session.commit()
        session.refresh(test_internship)

        for r_num in range(1, 9):
            session.add(InternshipProgressReport(
                internship_id=test_internship.id,
                report_number=r_num,
                summary=f"Test fixture progress report #{r_num}",
                status=ProgressReportStatus.APPROVED,
                review_notes="Approved",
                submitted_at=datetime.utcnow() - timedelta(days=100 - (r_num * 10)),
                reviewed_at=datetime.utcnow() - timedelta(days=99 - (r_num * 10))
            ))
        session.commit()

        # Verification summary
        total_students = session.exec(select(User).where(User.role == UserRole.STUDENT)).all()
        total_internships = session.exec(select(Internship)).all()
        total_reports = session.exec(select(InternshipProgressReport)).all()

        logger.info("================ SEEDING COMPLETE ================")
        logger.info(f"Total Student Users: {len(total_students)}")
        logger.info(f"Total Internships: {len(total_internships)}")
        logger.info(f"Total Progress Reports: {len(total_reports)}")
        logger.info("==================================================")


if __name__ == "__main__":
    create_db_and_tables()
    seed_database()
