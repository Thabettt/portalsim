"""Term-based attendance simulation: schedule -> attendance -> levels -> finalize.

This is the order of operations the simulator enforces, and the order matters:

1. **Schedule** is generated once for the whole 12-week term
   (:mod:`app.services.term_schedule`). Each course gets its slot days rolled
   randomly at generation time and then keeps them for the whole term.
2. **Attendance** is recorded against those scheduled slots, one record per
   (student, course, session).
3. **Warning levels** are computed *from* that recorded attendance.
4. **Finalize** sends the already-updated levels.

Because of (3), the ``warning_level`` in a finalize payload is a fact derived
from the attendance recorded up to ``today_date`` -- it is not something n8n has
to predict or recompute.

"Today" is simulated. The user steps through the term, so the current day is
wherever they have stepped to, and every finalize submission carries it
explicitly as ``today_date``.
"""

from __future__ import annotations

import math
import random
import uuid
from datetime import date, datetime, timezone
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

from app.services import term_schedule as ts

# --------------------------------------------------------------------------
# Attendance statuses
# --------------------------------------------------------------------------

PRESENT = "present"
ABSENT = "absent"

WARNING_LEVEL_LABELS = {"0": "Good", "1": "Warning 1", "2": "Warning 2", "3": "Drop"}
MIN_LEVEL, MAX_LEVEL = 0, 3


def utc_now_iso() -> str:
    """Real-world wall-clock timestamp, for ``finalized_at``."""
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


# --------------------------------------------------------------------------
# Warning levels derived from attendance
# --------------------------------------------------------------------------

def warning_level_for(absences: int, total_sessions: int) -> int:
    """Warning level implied by ``absences`` out of ``total_sessions``.

    Mirrors ``app.services.attendance.calculate_warning_level`` so the
    simulator and the real portal agree on what an absence count means:

    * level 3 (Drop)      -- at or past ceil(total/4) + 1 absences
    * level 2 (Warning 2) -- one absence short of the drop threshold
    * level 1 (Warning 1) -- 2 or more absences
    * level 0 (Good)      -- fewer than 2
    """
    if total_sessions <= 0:
        return MIN_LEVEL

    drop_threshold = math.ceil(total_sessions / 4) + 1
    if absences >= drop_threshold:
        return 3
    if absences >= drop_threshold - 1:
        return 2
    if absences >= 2:
        return 1
    return MIN_LEVEL


def level_from_sessions(sessions: Sequence[dict], total_sessions: int) -> int:
    """Warning level from a list of recorded sessions.

    ``total_sessions`` is the course's full term-length session count, not just
    the sessions held so far: the drop threshold is a share of the whole course.
    """
    absences = sum(1 for session in sessions if session.get("status") == ABSENT)
    return warning_level_for(absences, total_sessions)


# --------------------------------------------------------------------------
# Attendance recording
# --------------------------------------------------------------------------

def record_attendance(
    student_id: str,
    course_id: str,
    sessions: Sequence[dict],
    rng: random.Random,
    absence_rate: float = 0.15,
) -> List[dict]:
    """Mark one student present/absent across a course's scheduled sessions.

    Returns the sessions in payload shape: ``date``, ``slot``, ``session_type``
    and ``status``. A single date can legitimately appear more than once with
    different slots and different statuses, exactly like the real portal.
    """
    marked: List[dict] = []
    for session in sessions:
        status = ABSENT if rng.random() < absence_rate else PRESENT
        marked.append({
            "date": session["date"],
            "slot": session["slot"],
            "session_type": session["session_type"],
            "status": status,
        })
    return marked


def _student_rng(seed: int, student_id: str, course_id: str) -> random.Random:
    """Deterministic per-(student, course) RNG.

    Keying the stream this way means attendance for a given student-course is
    stable no matter which point of the term is finalized: finalizing through
    Week 4 and then through Week 8 yields the same first four weeks of records,
    rather than re-rolling history under the user.
    """
    return random.Random(f"{seed}:{student_id}:{course_id}")


# --------------------------------------------------------------------------
# Term state
# --------------------------------------------------------------------------

def build_term_state(
    enrollment: dict,
    term_start: date,
    seed: int,
    absence_rate: float = 0.15,
    courses: Optional[List[dict]] = None,
) -> dict:
    """Generate the schedule and the full-term attendance behind it.

    Attendance is generated for the entire term up front and then *revealed*
    up to whatever day the user has simulated to. That keeps stepping forward
    monotonic -- moving from Week 3 to Week 4 adds records without rewriting
    the ones already sent.

    ``courses`` lets the caller supply the credit hours explicitly, which
    matters for older enrollment seeds that predate the field.
    """
    if courses is None:
        catalog = enrollment.get("course_catalog") or []
        courses = [
            {"course_id": c["course_id"], "credit_hours": int(c.get("credit_hours", 4))}
            for c in catalog
        ]
    schedule = ts.build_term_schedule(courses, term_start=term_start, seed=seed)

    attendance: Dict[str, Dict[str, List[dict]]] = {}
    for student in enrollment["students"]:
        sid = student["student_id"]
        per_course: Dict[str, List[dict]] = {}
        for course in student["courses"]:
            code = course["course_id"]
            course_schedule = schedule["courses"].get(code)
            if course_schedule is None:
                per_course[code] = []
                continue
            per_course[code] = record_attendance(
                student_id=sid,
                course_id=code,
                sessions=course_schedule["sessions"],
                rng=_student_rng(seed, sid, code),
                absence_rate=absence_rate,
            )
        attendance[sid] = per_course

    return {
        "term_start": term_start.isoformat(),
        "term_weeks": ts.TERM_WEEKS,
        "random_seed": seed,
        "absence_rate": absence_rate,
        "schedule": schedule,
        "attendance": attendance,
    }


def total_sessions_for(schedule: dict, course_id: str) -> int:
    """Full-term session count for a course, used as the warning denominator."""
    course = schedule["courses"].get(course_id)
    return len(course["sessions"]) if course else 0


# --------------------------------------------------------------------------
# Building a finalize payload up to a chosen point
# --------------------------------------------------------------------------

def sessions_up_to(sessions: Sequence[dict], cutoff_iso: str) -> List[dict]:
    """Only the sessions dated on or before the simulated ``today_date``."""
    return [session for session in sessions if session["date"] <= cutoff_iso]


def build_student_records(
    enrollment: dict,
    term_state: dict,
    today: date,
) -> List[dict]:
    """Build the ``students[]`` array for a finalize run, cut off at ``today``.

    Every course a student is enrolled in appears every time -- including
    courses at level 0 and courses with no sessions yet. A course missing from
    the array reads downstream as "no longer enrolled", which is a different
    fact from "enrolled and doing fine".
    """
    cutoff_iso = today.isoformat()
    schedule = term_state["schedule"]
    attendance = term_state["attendance"]
    records: List[dict] = []

    for student in enrollment["students"]:
        sid = student["student_id"]
        student_attendance = attendance.get(sid, {})
        courses_out: List[dict] = []

        for course in student["courses"]:
            code = course["course_id"]
            visible = sessions_up_to(student_attendance.get(code, []), cutoff_iso)
            # Levels come from the attendance recorded so far, against the
            # course's full term length -- step 3 of the order of operations.
            level = level_from_sessions(visible, total_sessions_for(schedule, code))
            courses_out.append({
                "course_id": code,
                "course_name": course["course_name"],
                "warning_level": level,
                "sessions": visible,
            })

        records.append({
            "student_id": sid,
            "student_name": student["student_name"],
            "recipient": student["recipient"],
            "courses": courses_out,
        })

    return records


def chunk_students(
    students: List[dict],
    finalize_id: str,
    finalized_at: str,
    today_date: str,
    chunk_size: int,
    warning_level_labels: Optional[dict] = None,
) -> List[dict]:
    """Split ``students`` into the 1-based chunk envelopes the webhook expects.

    ``chunk_count`` is identical on every chunk so the receiver can tell that a
    chunk is missing for a given ``finalize_id``.
    """
    if chunk_size < 1:
        raise ValueError("chunk_size must be >= 1")

    batches = [students[i:i + chunk_size] for i in range(0, len(students), chunk_size)] or [[]]
    total = len(batches)
    return [
        {
            "finalize_id": finalize_id,
            "chunk_index": position,
            "chunk_count": total,
            "finalized_at": finalized_at,
            "today_date": today_date,
            "warning_level_labels": warning_level_labels or WARNING_LEVEL_LABELS,
            "students": batch,
        }
        for position, batch in enumerate(batches, start=1)
    ]


def build_finalize_payload(
    enrollment: dict,
    term_state: dict,
    today: date,
    chunk_size: int,
    finalize_id: Optional[str] = None,
    finalized_at: Optional[str] = None,
) -> dict:
    """Full finalize run for everything dated on or before ``today``.

    ``today`` is the *simulated* current day chosen with the "send up to"
    control, not the real calendar date.
    """
    students = build_student_records(enrollment, term_state, today)
    finalize_id = finalize_id or str(uuid.uuid4())
    finalized_at = finalized_at or utc_now_iso()

    chunks = chunk_students(
        students,
        finalize_id=finalize_id,
        finalized_at=finalized_at,
        today_date=today.isoformat(),
        chunk_size=chunk_size,
    )

    session_count = sum(
        len(course["sessions"]) for student in students for course in student["courses"]
    )
    absence_count = sum(
        1
        for student in students
        for course in student["courses"]
        for session in course["sessions"]
        if session["status"] == ABSENT
    )
    distribution = {"0": 0, "1": 0, "2": 0, "3": 0}
    for student in students:
        for course in student["courses"]:
            distribution[str(course["warning_level"])] += 1

    return {
        "summary": {
            "finalize_id": finalize_id,
            "finalized_at": finalized_at,
            "today_date": today.isoformat(),
            "students_count": len(students),
            "course_records_count": sum(len(s["courses"]) for s in students),
            "sessions_count": session_count,
            "absences_count": absence_count,
            "chunk_size": chunk_size,
            "chunk_count": len(chunks),
            "level_distribution": distribution,
        },
        "chunks": chunks,
        "students": students,
    }


# --------------------------------------------------------------------------
# Day view (what the UI shows for a selected week + day)
# --------------------------------------------------------------------------

def day_view(term_state: dict, week_number: int, weekday: int) -> dict:
    """Courses meeting on one specific day of the term.

    Courses with no slot that day are absent from the result entirely, so the
    UI naturally shows nothing for them.
    """
    schedule = term_state["schedule"]
    term_start = date.fromisoformat(term_state["term_start"])
    day = ts.date_for(term_start, week_number, weekday)
    sessions = ts.sessions_on_day(schedule, week_number, weekday)

    by_course: Dict[str, dict] = {}
    for session in sessions:
        entry = by_course.setdefault(session["course_code"], {
            "course_id": session["course_code"],
            "credit_hours": schedule["courses"][session["course_code"]]["credit_hours"],
            "sessions": [],
        })
        entry["sessions"].append(ts.to_session_dsc(session))

    return {
        "week_number": week_number,
        "weekday": weekday,
        "weekday_name": ts.WEEKDAY_NAMES[weekday],
        "date": day.isoformat(),
        "courses": [by_course[key] for key in sorted(by_course)],
        "session_count": len(sessions),
    }
