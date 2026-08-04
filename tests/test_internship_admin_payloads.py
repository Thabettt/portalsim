from datetime import date, datetime

from app.models import Internship, InternshipStatus, User, UserRole
from app.services.internship_admin import build_internship_admin_record, sort_internship_records


def test_build_internship_admin_record_uses_student_identity_and_spec_fields():
    student = User(
        id=7,
        student_id="STU-2024-0001",
        email="ahmed@example.edu",
        full_name="Ahmed Ali",
        role=UserRole.STUDENT,
    )
    internship = Internship(
        id=42,
        student_id=student.id,
        company_name="Acme Labs",
        position="Data Analyst Intern",
        start_date=date(2026, 6, 1),
        end_date=date(2026, 8, 31),
        status=InternshipStatus.APPROVED,
        description="Support analytics reporting.",
        supervisor_name="Mona Hassan",
        supervisor_email="mona@acme.com",
        proof_of_acceptance_uploaded_at=datetime(2026, 6, 2, 9, 30),
        evaluation_form_uploaded_at=datetime(2026, 6, 10, 13, 0),
        career_center_review_status="accepted",
        supervisor_review_status="accepted",
        academic_final_status="fulfilled",
        career_center_final_status="waiting",
        created_at=datetime(2026, 6, 1, 8, 0),
    )

    record = build_internship_admin_record(internship, student, report_count=3)

    assert record["student_display_name"] == "(STU-2024-0001) Ahmed Ali"
    assert record["student_name"] == "Ahmed Ali"
    assert record["student_email"] == "ahmed@example.edu"
    assert record["organization"] == "Acme Labs"
    assert record["training"] == "Data Analyst Intern"
    assert record["duration_from"] == "2026-06-01"
    assert record["duration_to"] == "2026-08-31"
    assert record["entry_date"] == "2026-06-01T08:00:00"
    assert record["proof_of_acceptance_upload_status"] == "Yes"
    assert record["evaluation_form_upload_status"] == "Yes"
    assert record["report_summary"]["total_reports"] == 3
    assert record["academic_final_status"] == "fulfilled"


def test_sort_internship_records_orders_by_student_full_name():
    records = [
        {"student_name": "Zara Khan"},
        {"student_name": "Ahmed Ali"},
        {"student_name": "Bob Smith"},
    ]

    sorted_records = sort_internship_records(records)

    assert [record["student_name"] for record in sorted_records] == ["Ahmed Ali", "Bob Smith", "Zara Khan"]
