from __future__ import annotations

from datetime import datetime, date
from typing import Any, Optional


def _coerce_datetime(value: Any) -> Optional[datetime]:
    if not value:
        return None
    if isinstance(value, datetime):
        return value
    if isinstance(value, str):
        try:
            return datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return None
    return None


def _coerce_date(value: Any) -> Optional[date]:
    if not value:
        return None
    if isinstance(value, date) and not isinstance(value, datetime):
        return value
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, str):
        try:
            return date.fromisoformat(value)
        except ValueError:
            try:
                return datetime.fromisoformat(value.replace("Z", "+00:00")).date()
            except ValueError:
                return None
    return None


def _to_iso_date(value: Any) -> Optional[str]:
    parsed_date = _coerce_date(value)
    if parsed_date is None:
        return None
    return parsed_date.isoformat()


def _to_iso_datetime(value: Any) -> Optional[str]:
    parsed_dt = _coerce_datetime(value)
    if parsed_dt is None:
        return None
    return parsed_dt.isoformat()


def _status_label(value: Optional[str]) -> str:
    if not value:
        return "waiting"
    return str(value).strip().lower()


def build_internship_admin_record(internship: Any, student: Any, report_count: int = 0) -> dict[str, Any]:
    student_name = getattr(student, "full_name", None) or getattr(student, "student_name", None) or ""
    student_id = getattr(student, "student_id", None) or getattr(student, "student_string_id", None) or getattr(internship, "student_id", None)
    student_email = getattr(student, "email", None) or getattr(student, "student_email", None) or ""

    status_value = getattr(internship, "status", None)
    if hasattr(status_value, "value"):
        status_value = status_value.value
    status_value = str(status_value or "pending").lower()

    return {
        "id": getattr(internship, "id", None),
        "student_db_id": getattr(student, "id", None),
        "student_id": student_id,
        "student_name": student_name,
        "student_display_name": f"({student_id}) {student_name}" if student_id and student_name else student_name,
        "student_email": student_email,
        "student_string_id": student_id,
        "organization": getattr(internship, "company_name", None) or "Not available",
        "duration_from": _to_iso_date(getattr(internship, "start_date", None)),
        "duration_to": _to_iso_date(getattr(internship, "end_date", None)),
        "entry_date": _to_iso_datetime(getattr(internship, "created_at", None)),
        "source_of_internship": getattr(internship, "source_of_internship", None) or "Not provided",
        "workplace": getattr(internship, "workplace", None) or "Not provided",
        "training": getattr(internship, "position", None) or "Not available",
        "departments": getattr(internship, "departments", None) or "",
        "days_per_week": getattr(internship, "days_per_week", None),
        "hours_per_day": getattr(internship, "hours_per_day", None),
        "job_description": getattr(internship, "description", None) or "Not provided",
        "country": getattr(internship, "country", None) or "Not provided",
        "faculty": getattr(internship, "faculty", None) or "Not provided",
        "first_major": getattr(internship, "first_major", None) or "Not provided",
        "second_major": getattr(internship, "second_major", None) or "",
        "academic_supervisor_name": getattr(internship, "academic_supervisor_name", None) or "Not provided",
        "academic_supervisor_id": getattr(internship, "academic_supervisor_id", None) or "",
        "supervisor_name": getattr(internship, "supervisor_name", None) or "Not provided",
        "supervisor_job_title": getattr(internship, "supervisor_job_title", None) or "Not provided",
        "supervisor_mobile": getattr(internship, "supervisor_mobile", None) or "",
        "supervisor_email": getattr(internship, "supervisor_email", None) or "",
        "career_center_review_status": _status_label(getattr(internship, "career_center_review_status", None)),
        "career_center_review_reason": getattr(internship, "career_center_review_reason", None) or "",
        "supervisor_review_status": _status_label(getattr(internship, "supervisor_review_status", None)),
        "supervisor_review_reason": getattr(internship, "supervisor_review_reason", None) or "",
        "proof_of_acceptance_upload_status": "Yes" if getattr(internship, "proof_of_acceptance_uploaded_at", None) else "No",
        "proof_of_acceptance_upload_date": _to_iso_datetime(getattr(internship, "proof_of_acceptance_uploaded_at", None)),
        "evaluation_form_upload_status": "Yes" if getattr(internship, "evaluation_form_uploaded_at", None) else "No",
        "evaluation_form_upload_date": _to_iso_datetime(getattr(internship, "evaluation_form_uploaded_at", None)),
        "academic_final_status": _status_label(getattr(internship, "academic_final_status", None)),
        "career_center_final_status": _status_label(getattr(internship, "career_center_final_status", None)),
        "status": status_value,
        "approved_at": _to_iso_datetime(getattr(internship, "approved_at", None)),
        "rejection_reason": getattr(internship, "rejection_reason", None),
        "report_summary": {
            "total_reports": report_count,
            "waiting_for_review": 0,
            "accepted": 0,
            "rejected": 0,
        },
    }


def sort_internship_records(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return sorted(records, key=lambda record: str(record.get("student_id") or record.get("student_string_id") or "").casefold())
