"""Dev-only endpoints for the attendance warning simulator.

Mounted under ``/dev/attendance-sim`` and gated on ``settings.debug`` so the
routes 404 in a non-debug deployment. This router is deliberately separate from
``admin.py`` and never touches the real finalize path.
"""

import logging

from fastapi import APIRouter, HTTPException, Query

from app.config import get_settings
from app.services import attendance_sim

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/dev/attendance-sim", tags=["dev-simulator"])


def _guard() -> None:
    if not get_settings().debug:
        raise HTTPException(404, "Not found")


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
