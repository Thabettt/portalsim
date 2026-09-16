import asyncio
import logging
import uuid
from collections import OrderedDict
from datetime import datetime, timezone

import httpx
from sqlmodel import Session, select

from app.config import get_settings
from app.models import (
    Attendance,
    AttendanceWarningLevel,
    Course,
    CourseEnrollment,
    User,
    UserRole,
)

logger = logging.getLogger(__name__)

WARNING_LEVEL_VALUES = {
    AttendanceWarningLevel.NONE: 0,
    AttendanceWarningLevel.FIRST_WARNING: 1,
    AttendanceWarningLevel.SECOND_WARNING: 2,
    AttendanceWarningLevel.FINAL_WARNING: 3,
}

CHUNK_PENDING = "pending"
CHUNK_SENDING = "sending"
CHUNK_SENT = "sent"
CHUNK_FAILED = "failed"

JOB_RUNNING = "running"
JOB_COMPLETED = "completed"
JOB_PARTIAL = "partial"

# How many finished finalize jobs to keep in memory for progress polling.
MAX_TRACKED_JOBS = 20

_jobs: "OrderedDict[str, dict]" = OrderedDict()


class AttendanceFinalizationError(Exception):
    """Raised when the finalized snapshot cannot be accepted by n8n."""


class AttendanceFinalizationNotConfigured(AttendanceFinalizationError):
    """Raised when the n8n attendance webhook URL is missing."""


def build_attendance_snapshot(session: Session) -> dict:
    """Build the authoritative saved warning state for every student enrollment."""
    finalized_at = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    students = session.exec(
        select(User)
        .where(User.role == UserRole.STUDENT)
        .where(User.is_active == True)
        .order_by(User.student_id)
    ).all()

    student_records = []
    course_record_count = 0

    for student in students:
        enrollments = session.exec(
            select(CourseEnrollment, Course)
            .join(Course, CourseEnrollment.course_id == Course.id)
            .where(CourseEnrollment.student_id == student.id)
            .order_by(Course.code)
        ).all()

        courses = []
        for _, course in enrollments:
            latest_attendance = session.exec(
                select(Attendance)
                .where(Attendance.student_id == student.id)
                .where(Attendance.course_id == course.id)
                .order_by(Attendance.date.desc(), Attendance.marked_at.desc())
            ).first()
            warning_level = (
                latest_attendance.warning_level
                if latest_attendance
                else AttendanceWarningLevel.NONE
            )
            courses.append({
                "course_id": course.code,
                "course_name": course.name,
                "warning_level": WARNING_LEVEL_VALUES[warning_level],
            })
            course_record_count += 1

        student_records.append({
            "student_id": student.student_id,
            "student_name": student.full_name,
            "recipient": student.email,
            "courses": courses,
        })

    return {
        "batch_id": str(uuid.uuid4()),
        "finalized_at": finalized_at,
        "warning_level_labels": {
            "0": "Good",
            "1": "Warning 1",
            "2": "Warning 2",
            "3": "Drop",
        },
        "students": student_records,
        "students_count": len(student_records),
        "course_records_count": course_record_count,
    }


def split_into_chunks(students: list[dict], chunk_size: int) -> list[list[dict]]:
    """Split the student list into fixed-size chunks (config-driven, never hardcoded)."""
    if chunk_size < 1:
        raise ValueError("attendance_chunk_size must be at least 1")
    return [students[i:i + chunk_size] for i in range(0, len(students), chunk_size)]


def build_chunk_payload(
    finalize_id: str,
    finalized_at: str,
    chunk_index: int,
    chunk_count: int,
    students: list[dict],
    warning_level_labels: dict | None = None,
) -> dict:
    """Build the per-chunk request body. chunk_index is 1-based."""
    payload = {
        "finalize_id": finalize_id,
        "chunk_index": chunk_index,
        "chunk_count": chunk_count,
        "finalized_at": finalized_at,
        "students": students,
    }
    if warning_level_labels:
        payload["warning_level_labels"] = warning_level_labels
    return payload


def _job_progress(job: dict) -> dict:
    """Public, JSON-safe view of a finalize job (no raw student payloads)."""
    chunks = job["chunks"]
    sent = [c for c in chunks if c["status"] == CHUNK_SENT]
    failed = [c for c in chunks if c["status"] == CHUNK_FAILED]
    pending = [c for c in chunks if c["status"] in (CHUNK_PENDING, CHUNK_SENDING)]

    return {
        "finalize_id": job["finalize_id"],
        "finalized_at": job["finalized_at"],
        "status": job["status"],
        "chunk_size": job["chunk_size"],
        "chunk_count": job["chunk_count"],
        "chunks_sent": len(sent),
        "chunks_failed": len(failed),
        "chunks_pending": len(pending),
        "students_processed": job["students_count"],
        "course_records_sent": job["course_records_count"],
        "failed_chunks": [c["chunk_index"] for c in failed],
        "chunks": [
            {
                "chunk_index": c["chunk_index"],
                "status": c["status"],
                "students": len(c["students"]),
                "attempts": c["attempts"],
                "status_code": c["status_code"],
                "error": c["error"],
            }
            for c in chunks
        ],
        "message": job["message"],
    }


def get_finalization_progress(finalize_id: str) -> dict | None:
    job = _jobs.get(finalize_id)
    return _job_progress(job) if job else None


def _register_job(job: dict) -> None:
    _jobs[job["finalize_id"]] = job
    while len(_jobs) > MAX_TRACKED_JOBS:
        stale_id, stale_job = next(iter(_jobs.items()))
        if stale_job["status"] == JOB_RUNNING:
            break
        _jobs.pop(stale_id, None)


def _resolve_webhook_url() -> str:
    settings = get_settings()
    webhook_url = settings.n8n_attendance_webhook_url.strip()
    if not webhook_url:
        raise AttendanceFinalizationNotConfigured(
            "The n8n attendance webhook URL is not configured."
        )
    return webhook_url


async def _send_chunk(client: httpx.AsyncClient, url: str, chunk: dict, job: dict) -> None:
    """POST one chunk, retrying with exponential backoff until it is accepted or gives up."""
    settings = get_settings()
    delays = settings.attendance_retry_delays
    max_retries = max(0, settings.attendance_chunk_max_retries)

    payload = build_chunk_payload(
        finalize_id=job["finalize_id"],
        finalized_at=job["finalized_at"],
        chunk_index=chunk["chunk_index"],
        chunk_count=job["chunk_count"],
        students=chunk["students"],
        warning_level_labels=job["warning_level_labels"],
    )

    for attempt in range(max_retries + 1):
        chunk["status"] = CHUNK_SENDING
        chunk["attempts"] = attempt + 1
        try:
            response = await client.post(
                url,
                json=payload,
                headers={"Content-Type": "application/json"},
            )
        except httpx.TimeoutException:
            chunk["error"] = "Request timed out."
            chunk["status_code"] = None
            logger.warning(
                "Timeout sending chunk %s/%s of finalize %s (attempt %s)",
                chunk["chunk_index"], job["chunk_count"], job["finalize_id"], attempt + 1,
            )
        except httpx.RequestError as exc:
            chunk["error"] = f"Could not reach the notification workflow: {exc}"
            chunk["status_code"] = None
            logger.warning(
                "Network error sending chunk %s/%s of finalize %s (attempt %s): %s",
                chunk["chunk_index"], job["chunk_count"], job["finalize_id"], attempt + 1, exc,
            )
        else:
            chunk["status_code"] = response.status_code
            # n8n answers 202 Accepted per chunk: this chunk was received,
            # NOT that the whole day has been processed.
            if 200 <= response.status_code < 300:
                chunk["status"] = CHUNK_SENT
                chunk["error"] = None
                logger.info(
                    "Chunk %s/%s of finalize %s accepted with HTTP %s",
                    chunk["chunk_index"], job["chunk_count"], job["finalize_id"],
                    response.status_code,
                )
                return
            body = (response.text or "")[:500]
            chunk["error"] = f"HTTP {response.status_code}: {body}" if body else f"HTTP {response.status_code}"
            logger.warning(
                "n8n rejected chunk %s/%s of finalize %s with HTTP %s (attempt %s)",
                chunk["chunk_index"], job["chunk_count"], job["finalize_id"],
                response.status_code, attempt + 1,
            )

        if attempt < max_retries:
            delay = delays[attempt] if attempt < len(delays) else delays[-1]
            chunk["status"] = CHUNK_PENDING
            await asyncio.sleep(delay)

    chunk["status"] = CHUNK_FAILED
    logger.error(
        "Chunk %s/%s of finalize %s failed after %s attempts: %s",
        chunk["chunk_index"], job["chunk_count"], job["finalize_id"],
        chunk["attempts"], chunk["error"],
    )


async def _run_finalization(job: dict, chunks: list[dict]) -> None:
    """Send the given chunks with bounded concurrency, then settle the job status."""
    settings = get_settings()
    concurrency = max(1, settings.attendance_chunk_max_concurrency)
    semaphore = asyncio.Semaphore(concurrency)
    timeout = settings.attendance_chunk_timeout_seconds

    try:
        url = _resolve_webhook_url()
    except AttendanceFinalizationNotConfigured as exc:
        for chunk in chunks:
            chunk["status"] = CHUNK_FAILED
            chunk["error"] = str(exc)
        job["status"] = JOB_PARTIAL
        job["message"] = str(exc)
        return

    async with httpx.AsyncClient(timeout=timeout) as client:
        async def guarded(chunk: dict) -> None:
            async with semaphore:
                await _send_chunk(client, url, chunk, job)

        await asyncio.gather(*(guarded(chunk) for chunk in chunks), return_exceptions=False)

    failed = [c for c in job["chunks"] if c["status"] == CHUNK_FAILED]
    if failed:
        job["status"] = JOB_PARTIAL
        job["message"] = (
            f"{len(job['chunks']) - len(failed)} of {job['chunk_count']} chunks were accepted. "
            f"Chunks {', '.join(str(c['chunk_index']) for c in failed)} failed after retries and can be resent."
        )
    else:
        job["status"] = JOB_COMPLETED
        job["message"] = f"All {job['chunk_count']} chunks were accepted by the notification workflow."


async def start_attendance_finalization(session: Session) -> dict:
    """Build the snapshot, split it into chunks and start sending them in the background.

    Returns immediately with the initial progress payload so the UI is never blocked
    on the full delivery.
    """
    _resolve_webhook_url()

    settings = get_settings()
    snapshot = build_attendance_snapshot(session)
    students = snapshot["students"]
    if not students:
        raise AttendanceFinalizationError("There are no active students to finalize.")

    chunk_size = max(1, settings.attendance_chunk_size)
    student_chunks = split_into_chunks(students, chunk_size)

    finalize_id = str(uuid.uuid4())
    job = {
        "finalize_id": finalize_id,
        "finalized_at": snapshot["finalized_at"],
        "warning_level_labels": snapshot["warning_level_labels"],
        "status": JOB_RUNNING,
        "chunk_size": chunk_size,
        "chunk_count": len(student_chunks),
        "students_count": snapshot["students_count"],
        "course_records_count": snapshot["course_records_count"],
        "message": f"Sending {len(student_chunks)} chunks to the notification workflow.",
        "chunks": [
            {
                "chunk_index": index,
                "students": chunk_students,
                "status": CHUNK_PENDING,
                "attempts": 0,
                "status_code": None,
                "error": None,
            }
            for index, chunk_students in enumerate(student_chunks, start=1)
        ],
    }
    _register_job(job)

    job["task"] = asyncio.create_task(_run_finalization(job, job["chunks"]))
    return _job_progress(job)


async def resend_failed_chunks(finalize_id: str) -> dict:
    """Re-send only the chunks that failed after retries, for a human-triggered resend."""
    job = _jobs.get(finalize_id)
    if job is None:
        raise AttendanceFinalizationError(f"Unknown finalize_id: {finalize_id}")
    if job["status"] == JOB_RUNNING:
        raise AttendanceFinalizationError("This finalize run is still in progress.")

    failed = [c for c in job["chunks"] if c["status"] == CHUNK_FAILED]
    if not failed:
        return _job_progress(job)

    for chunk in failed:
        chunk["status"] = CHUNK_PENDING
        chunk["attempts"] = 0
        chunk["status_code"] = None
        chunk["error"] = None

    job["status"] = JOB_RUNNING
    job["message"] = f"Resending {len(failed)} failed chunks."
    job["task"] = asyncio.create_task(_run_finalization(job, failed))
    return _job_progress(job)
