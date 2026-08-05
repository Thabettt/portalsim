"""Dev-only endpoints for the attendance warning simulator.

Mounted under ``/dev/attendance-sim`` and gated on ``settings.debug`` so the
routes 404 in a non-debug deployment. This router is deliberately separate from
``admin.py`` and never touches the real finalize path.
"""

import logging

from fastapi import APIRouter, HTTPException, Query

from app.config import get_settings
from app.services import attendance_sim, term_schedule
from app.services.n8n_attendance import (
    AttendanceFinalizationError,
    AttendanceFinalizationNotConfigured,
    get_finalization_progress,
    resend_failed_chunks,
    start_chunked_submission,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/dev/attendance-sim", tags=["dev-simulator"])

WEEKDAY_QUERY = Query(
    ...,
    description="Weekday as datetime.date().weekday(): Mon=0 .. Sun=6. Teaching days are Sun-Thu.",
)


def _guard() -> None:
    if not get_settings().debug:
        raise HTTPException(404, "Not found")


def _validate_point(week_number: int, weekday: int) -> None:
    """Reject points that fall outside the fixed 12-week Sunday-Thursday term."""
    if not 1 <= week_number <= term_schedule.TERM_WEEKS:
        raise HTTPException(
            400, f"week_number must be between 1 and {term_schedule.TERM_WEEKS}."
        )
    if weekday not in term_schedule.TEACHING_WEEKDAYS:
        allowed = ", ".join(
            f"{term_schedule.WEEKDAY_NAMES[d]}={d}" for d in term_schedule.TEACHING_WEEKDAYS
        )
        raise HTTPException(400, f"weekday must be a teaching day ({allowed}).")


@router.get("/status")
async def sim_status():
    """Seed metadata, current simulated day, and level distribution."""
    _guard()
    try:
        return attendance_sim.current_status()
    except FileNotFoundError as exc:
        raise HTTPException(409, str(exc)) from exc


@router.post("/seed")
async def sim_seed(
    students: int = Query(attendance_sim.DEFAULT_STUDENT_COUNT, ge=1, le=50000),
    force: bool = Query(False, description="Regenerate enrollment even if it already exists"),
):
    """Create the enrollment seed. Refuses to clobber unless force=true."""
    _guard()
    try:
        enrollment = attendance_sim.write_enrollment_seed(student_count=students, overwrite=force)
    except FileExistsError as exc:
        raise HTTPException(409, str(exc)) from exc
    attendance_sim.reset_state(enrollment)
    return {
        "students_count": enrollment["students_count"],
        "course_records_count": enrollment["course_records_count"],
        "test_inbox": enrollment["test_inbox"],
        "enrollment_path": str(attendance_sim.ENROLLMENT_PATH),
        "message": "Enrollment seeded and warning levels reset to day 0.",
    }


@router.post("/next-day")
async def sim_next_day(
    chunk_size: int = Query(attendance_sim.DEFAULT_CHUNK_SIZE, ge=1, le=5000),
    include_chunks: bool = Query(False, description="Return the full chunk payloads, not just the summary"),
    preview_chunk: int = Query(0, ge=0, description="1-based chunk index to return as a sample"),
):
    """Advance one simulated day and return the chunked finalize payload set.

    The default response is summary-only because 3,000 students is a multi-MB
    body; pass ``include_chunks=true`` when you actually want the payloads.
    """
    _guard()
    try:
        result = attendance_sim.simulate_next_day(chunk_size=chunk_size)
    except FileNotFoundError as exc:
        raise HTTPException(409, str(exc)) from exc

    response = {"summary": result["summary"]}
    if include_chunks:
        response["chunks"] = result["chunks"]
    elif preview_chunk:
        chunks = result["chunks"]
        if preview_chunk > len(chunks):
            raise HTTPException(400, f"preview_chunk must be <= {len(chunks)}")
        sample = dict(chunks[preview_chunk - 1])
        sample["students"] = sample["students"][:3]
        sample["_note"] = "students[] truncated to 3 for preview"
        response["chunk_preview"] = sample
    return response


@router.post("/reset")
async def sim_reset():
    """Reset warning levels to day 0. Enrollment is preserved."""
    _guard()
    try:
        state = attendance_sim.reset_state()
    except FileNotFoundError as exc:
        raise HTTPException(409, str(exc)) from exc
    return {"day_number": state["day_number"], "message": "Warning levels reset to day 0."}


@router.get("/student/{student_id}")
async def sim_student(student_id: str):
    """Current per-course warning levels for one simulated student."""
    _guard()
    try:
        return attendance_sim.student_timeline(student_id)
    except KeyError as exc:
        raise HTTPException(404, f"Unknown student_id: {student_id}") from exc
    except FileNotFoundError as exc:
        raise HTTPException(409, str(exc)) from exc


# --------------------------------------------------------------------------
# Fixed 12-week term: schedule, day view, and chunked finalize
# --------------------------------------------------------------------------

@router.get("/term")
async def sim_term():
    """Term shape (Week 1-12, Sun-Thu) and each course's assigned days/slots."""
    _guard()
    try:
        return attendance_sim.term_overview()
    except FileNotFoundError as exc:
        raise HTTPException(409, str(exc)) from exc


@router.post("/term/regenerate")
async def sim_regenerate_term(
    seed: int = Query(None, description="Random seed for the slot-day assignment"),
    absence_rate: float = Query(
        attendance_sim.DEFAULT_ABSENCE_RATE, ge=0.0, le=1.0,
        description="Share of scheduled sessions a student misses",
    ),
):
    """Re-roll the term schedule and its attendance, then reset the day pointer.

    Slot days are randomised once per term, so this is the only way to move
    them. Existing attendance is regenerated against the new schedule.
    """
    _guard()
    try:
        term = attendance_sim.regenerate_term(seed=seed, absence_rate=absence_rate)
    except FileNotFoundError as exc:
        raise HTTPException(409, str(exc)) from exc
    return {
        "term_start": term["term_start"],
        "term_weeks": term["term_weeks"],
        "random_seed": term["random_seed"],
        "absence_rate": term["absence_rate"],
        "message": "Term schedule regenerated and simulated day reset to Week 1.",
    }


@router.get("/term/day")
async def sim_day(
    week_number: int = Query(..., ge=1, le=term_schedule.TERM_WEEKS),
    weekday: int = WEEKDAY_QUERY,
):
    """Courses meeting on one specific day. Courses with no slot that day are omitted."""
    _guard()
    _validate_point(week_number, weekday)
    try:
        return attendance_sim.day_schedule(week_number, weekday)
    except FileNotFoundError as exc:
        raise HTTPException(409, str(exc)) from exc


@router.get("/term/point")
async def sim_point():
    """Where the simulation currently is in the term (the simulated 'today')."""
    _guard()
    try:
        return attendance_sim.current_point()
    except FileNotFoundError as exc:
        raise HTTPException(409, str(exc)) from exc


@router.post("/term/point")
async def sim_set_point(
    week_number: int = Query(..., ge=1, le=term_schedule.TERM_WEEKS),
    weekday: int = WEEKDAY_QUERY,
):
    """Move the simulated 'today' to a chosen point in the term."""
    _guard()
    _validate_point(week_number, weekday)
    try:
        return attendance_sim.set_simulated_day(week_number, weekday)
    except FileNotFoundError as exc:
        raise HTTPException(409, str(exc)) from exc


@router.post("/term/finalize-preview")
async def sim_finalize_preview(
    week_number: int = Query(..., ge=1, le=term_schedule.TERM_WEEKS),
    weekday: int = WEEKDAY_QUERY,
    chunk_size: int = Query(attendance_sim.DEFAULT_CHUNK_SIZE, ge=1, le=5000),
    preview_chunk: int = Query(1, ge=1, description="1-based chunk index to sample"),
):
    """Build the finalize payload for a point WITHOUT sending it to n8n.

    Returns the summary plus one truncated chunk, because a 3,000-student term
    payload is many megabytes.
    """
    _guard()
    _validate_point(week_number, weekday)
    try:
        result = attendance_sim.finalize_through(week_number, weekday, chunk_size=chunk_size)
    except FileNotFoundError as exc:
        raise HTTPException(409, str(exc)) from exc

    chunks = result["chunks"]
    if preview_chunk > len(chunks):
        raise HTTPException(400, f"preview_chunk must be <= {len(chunks)}")

    sample = dict(chunks[preview_chunk - 1])
    sample["students"] = sample["students"][:2]
    sample["_note"] = "students[] truncated to 2 for preview"
    return {"summary": result["summary"], "chunk_preview": sample}


@router.post("/term/finalize", status_code=202)
async def sim_finalize(
    week_number: int = Query(..., ge=1, le=term_schedule.TERM_WEEKS),
    weekday: int = WEEKDAY_QUERY,
    chunk_size: int = Query(None, ge=1, le=5000),
):
    """Finalize the term through a chosen point and POST it to n8n in chunks.

    Sending happens in the background with bounded concurrency, so this returns
    as soon as the chunks are queued. Poll ``/term/finalize/{finalize_id}`` for
    per-chunk progress.
    """
    _guard()
    _validate_point(week_number, weekday)

    try:
        result = attendance_sim.finalize_through(week_number, weekday, chunk_size=chunk_size)
    except FileNotFoundError as exc:
        raise HTTPException(409, str(exc)) from exc

    summary = result["summary"]
    try:
        progress = await start_chunked_submission(
            students=result["students"],
            finalized_at=summary["finalized_at"],
            today_date=summary["today_date"],
            chunk_size=summary["chunk_size"],
            warning_level_labels=attendance_sim.WARNING_LEVEL_LABELS,
        )
    except AttendanceFinalizationNotConfigured as exc:
        raise HTTPException(503, str(exc)) from exc
    except AttendanceFinalizationError as exc:
        raise HTTPException(400, str(exc)) from exc

    attendance_sim.set_simulated_day(week_number, weekday)
    return {"summary": summary, "progress": progress}


@router.get("/term/finalize/{finalize_id}")
async def sim_finalize_progress(finalize_id: str):
    """Per-chunk progress for a simulated finalize run ("32 / 50 chunks sent")."""
    _guard()
    progress = get_finalization_progress(finalize_id)
    if progress is None:
        raise HTTPException(404, f"No finalize run found for id {finalize_id}.")
    return progress


@router.post("/term/finalize/{finalize_id}/resend-failed", status_code=202)
async def sim_resend_failed(finalize_id: str):
    """Resend only the chunks that failed after their retries."""
    _guard()
    try:
        return await resend_failed_chunks(finalize_id)
    except AttendanceFinalizationError as exc:
        raise HTTPException(400, str(exc)) from exc
