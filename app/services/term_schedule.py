"""Fixed 12-week term structure and credit-driven slot generation.

The simulator no longer works off a free-form calendar date. A term is exactly
12 weeks of a Sunday-Thursday academic week, and every point in time is
addressed as ``(week_number, weekday)``. Real dates are still produced -- the
payload contract needs ``YYYY-MM-DD`` -- but they are *derived* from the term
anchor rather than picked by the user.

Slot count per week is driven by credit hours:

===============  ==========================================================
Credit hours     Slots per week
===============  ==========================================================
4                exactly 1, every week, all 12 weeks
8                exactly 2, every week, on two different randomly chosen days
6                alternating 1, 2, 1, 2 ... (odd weeks 1, even weeks 2)
===============  ==========================================================

The random day assignment happens **once**, when the term schedule is
generated, and is then persisted. It is deliberately *not* re-rolled on every
page load: a course that meets on Monday must keep meeting on Monday for the
whole term, otherwise attendance recorded against week 3 stops lining up with
the schedule shown in week 4.

Each emitted session mirrors the real portal's ``SessionDsc`` record closely
enough that downstream consumers cannot tell the two apart:

``course_code``, ``session_type``, ``date``, ``slot``, ``duration``.
"""

from __future__ import annotations

import random
from datetime import date, timedelta
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

# --------------------------------------------------------------------------
# Term shape
# --------------------------------------------------------------------------

TERM_WEEKS = 12
"""A term is exactly 12 weeks. Week numbers are 1-based (Week 1 .. Week 12)."""

# The academic week runs Sunday -> Thursday. Friday and Saturday are the
# weekend and never carry a session.
#
# Weekday numbers follow ``datetime.date.weekday()``: Mon=0 .. Sun=6.
SUNDAY, MONDAY, TUESDAY, WEDNESDAY, THURSDAY, FRIDAY, SATURDAY = 6, 0, 1, 2, 3, 4, 5

TEACHING_WEEKDAYS: Tuple[int, ...] = (SUNDAY, MONDAY, TUESDAY, WEDNESDAY, THURSDAY)
"""Days that can carry a session, in academic-week order (Sun first)."""

WEEKDAY_NAMES: Dict[int, str] = {
    SUNDAY: "Sunday",
    MONDAY: "Monday",
    TUESDAY: "Tuesday",
    WEDNESDAY: "Wednesday",
    THURSDAY: "Thursday",
    FRIDAY: "Friday",
    SATURDAY: "Saturday",
}

# Order used whenever days are listed to a human or iterated for "the whole
# week": the academic week starts on Sunday, not Monday.
WEEKDAY_ORDER: Dict[int, int] = {day: index for index, day in enumerate(TEACHING_WEEKDAYS)}

# --------------------------------------------------------------------------
# Slots
# --------------------------------------------------------------------------

# The real portal numbers its daily periods; Slot 3/4/5 are the ones the
# reference payload uses, so the simulator draws from the same pool.
AVAILABLE_SLOTS: Tuple[int, ...] = (1, 2, 3, 4, 5)
DEFAULT_SLOT_POOL: Tuple[int, ...] = (3, 4, 5)
"""Slots the generator prefers, matching the real portal's Slot 3/4/5 style."""

SLOT_DURATION_MINUTES = 90
"""Every slot is a 90-minute period, as in the real portal's SessionDsc."""

SESSION_LECTURE = "Lecture"
SESSION_TUTORIAL = "Tutorial"
SESSION_TYPES: Tuple[str, str] = (SESSION_LECTURE, SESSION_TUTORIAL)

# --------------------------------------------------------------------------
# Credit hours -> weekly slot count
# --------------------------------------------------------------------------

CREDIT_FOUR, CREDIT_SIX, CREDIT_EIGHT = 4, 6, 8
SUPPORTED_CREDIT_HOURS: Tuple[int, int, int] = (CREDIT_FOUR, CREDIT_SIX, CREDIT_EIGHT)


class UnsupportedCreditHours(ValueError):
    """Raised when a course's credit hours have no defined slot pattern."""


def slots_for_week(credit_hours: int, week_number: int) -> int:
    """How many slots a course of ``credit_hours`` holds in ``week_number``.

    * 4 credits -> 1 slot every week.
    * 8 credits -> 2 slots every week.
    * 6 credits -> alternates 1, 2, 1, 2 ... starting at 1 in Week 1, so odd
      weeks carry one slot and even weeks carry two.
    """
    if not 1 <= week_number <= TERM_WEEKS:
        raise ValueError(f"week_number must be 1..{TERM_WEEKS}, got {week_number}")

    if credit_hours == CREDIT_FOUR:
        return 1
    if credit_hours == CREDIT_EIGHT:
        return 2
    if credit_hours == CREDIT_SIX:
        return 1 if week_number % 2 == 1 else 2

    raise UnsupportedCreditHours(
        f"No slot pattern defined for {credit_hours} credit hours "
        f"(supported: {', '.join(str(c) for c in SUPPORTED_CREDIT_HOURS)})."
    )


def total_slots_in_term(credit_hours: int) -> int:
    """Total number of slots a course holds across the whole 12-week term."""
    return sum(slots_for_week(credit_hours, week) for week in range(1, TERM_WEEKS + 1))


def weekdays_needed(credit_hours: int) -> int:
    """How many distinct weekdays a course needs assigned.

    A 4-credit course meets on one day. A 6- or 8-credit course needs two
    distinct days, because its busy weeks place two slots on *different* days
    rather than stacking both onto one.
    """
    if credit_hours == CREDIT_FOUR:
        return 1
    if credit_hours in (CREDIT_SIX, CREDIT_EIGHT):
        return 2
    raise UnsupportedCreditHours(
        f"No slot pattern defined for {credit_hours} credit hours."
    )


# --------------------------------------------------------------------------
# Term calendar
# --------------------------------------------------------------------------

def term_start_sunday(anchor: date) -> date:
    """Snap ``anchor`` back to the Sunday that opens its academic week."""
    # date.weekday(): Mon=0 .. Sun=6, so Sunday is 6 and every other day is
    # (weekday + 1) days past the preceding Sunday.
    days_since_sunday = 0 if anchor.weekday() == SUNDAY else anchor.weekday() + 1
    return anchor - timedelta(days=days_since_sunday)


def date_for(term_start: date, week_number: int, weekday: int) -> date:
    """Real calendar date of ``weekday`` in ``week_number`` of the term.

    ``term_start`` must be the Sunday opening Week 1.
    """
    if not 1 <= week_number <= TERM_WEEKS:
        raise ValueError(f"week_number must be 1..{TERM_WEEKS}, got {week_number}")
    if weekday not in WEEKDAY_ORDER:
        raise ValueError(
            f"weekday {weekday} is not a teaching day "
            f"({', '.join(WEEKDAY_NAMES[d] for d in TEACHING_WEEKDAYS)})"
        )
    return term_start + timedelta(days=(week_number - 1) * 7 + WEEKDAY_ORDER[weekday])


def week_and_weekday_for(term_start: date, target: date) -> Optional[Tuple[int, int]]:
    """Inverse of :func:`date_for`. ``None`` when ``target`` is outside the term."""
    offset = (target - term_start).days
    if offset < 0:
        return None
    week_number = offset // 7 + 1
    if week_number > TERM_WEEKS:
        return None
    position = offset % 7
    if position >= len(TEACHING_WEEKDAYS):
        return None  # Friday or Saturday
    return week_number, TEACHING_WEEKDAYS[position]


def term_days(term_start: date) -> List[dict]:
    """Every teaching day of the term, in order, as selectable descriptors."""
    days = []
    for week_number in range(1, TERM_WEEKS + 1):
        for weekday in TEACHING_WEEKDAYS:
            day = date_for(term_start, week_number, weekday)
            days.append({
                "week_number": week_number,
                "weekday": weekday,
                "weekday_name": WEEKDAY_NAMES[weekday],
                "date": day.isoformat(),
            })
    return days


# --------------------------------------------------------------------------
# Schedule generation
# --------------------------------------------------------------------------

def assign_course_days(
    credit_hours: int,
    rng: random.Random,
    teaching_days: Sequence[int] = TEACHING_WEEKDAYS,
) -> List[int]:
    """Randomly choose which weekday(s) a course's slots fall on.

    Returns days in academic-week order so "Slot 1" is consistently the earlier
    day of the week and "Slot 2" the later one.
    """
    needed = weekdays_needed(credit_hours)
    if needed > len(teaching_days):
        raise ValueError(
            f"{credit_hours}-credit course needs {needed} distinct days but only "
            f"{len(teaching_days)} teaching days are available."
        )
    chosen = rng.sample(list(teaching_days), needed)
    return sorted(chosen, key=lambda day: WEEKDAY_ORDER[day])


def assign_course_slots(
    credit_hours: int,
    rng: random.Random,
    slot_pool: Sequence[int] = DEFAULT_SLOT_POOL,
) -> List[int]:
    """Pick the period number used on each of the course's weekdays."""
    needed = weekdays_needed(credit_hours)
    pool = list(slot_pool)
    if needed <= len(pool):
        return rng.sample(pool, needed)
    return [rng.choice(pool) for _ in range(needed)]


def build_course_schedule(
    course_code: str,
    credit_hours: int,
    term_start: date,
    rng: random.Random,
    slot_pool: Sequence[int] = DEFAULT_SLOT_POOL,
    teaching_days: Sequence[int] = TEACHING_WEEKDAYS,
) -> dict:
    """Generate the full 12-week schedule for one course.

    The day/slot assignment is rolled once here; every week of the term then
    reuses it, so the course keeps a stable weekly rhythm.
    """
    days = assign_course_days(credit_hours, rng, teaching_days)
    slots = assign_course_slots(credit_hours, rng, slot_pool)

    # The first weekday of a pair carries the Lecture, the second the Tutorial,
    # which is how the real portal splits a two-session course.
    session_types = (
        [SESSION_LECTURE]
        if len(days) == 1
        else [SESSION_LECTURE, SESSION_TUTORIAL]
    )

    sessions: List[dict] = []
    for week_number in range(1, TERM_WEEKS + 1):
        count = slots_for_week(credit_hours, week_number)
        for position in range(count):
            weekday = days[position]
            sessions.append(_session_record(
                course_code=course_code,
                session_type=session_types[position],
                day=date_for(term_start, week_number, weekday),
                slot=slots[position],
                week_number=week_number,
                weekday=weekday,
            ))

    return {
        "course_id": course_code,
        "credit_hours": credit_hours,
        "weekdays": days,
        "weekday_names": [WEEKDAY_NAMES[d] for d in days],
        "slots": slots,
        "session_types": session_types,
        "sessions": sessions,
    }


def _session_record(
    course_code: str,
    session_type: str,
    day: date,
    slot: int,
    week_number: int,
    weekday: int,
) -> dict:
    """One session in the real portal's ``SessionDsc`` shape.

    ``week_number`` / ``weekday`` are simulator bookkeeping and are stripped
    before the record goes into a finalize payload.
    """
    return {
        "course_code": course_code,
        "session_type": session_type,
        "date": day.isoformat(),
        "slot": slot,
        "duration": SLOT_DURATION_MINUTES,
        "week_number": week_number,
        "weekday": weekday,
    }


def build_term_schedule(
    courses: Iterable[dict],
    term_start: date,
    seed: int,
    slot_pool: Sequence[int] = DEFAULT_SLOT_POOL,
    teaching_days: Sequence[int] = TEACHING_WEEKDAYS,
) -> dict:
    """Generate the whole term's schedule, once, for every course.

    ``courses`` items need ``course_id`` and ``credit_hours``. Generation is
    deterministic for a given ``seed`` so a regenerated term reproduces exactly
    the same day/slot assignment.
    """
    rng = random.Random(seed)
    by_course: Dict[str, dict] = {}

    for course in sorted(courses, key=lambda c: c["course_id"]):
        by_course[course["course_id"]] = build_course_schedule(
            course_code=course["course_id"],
            credit_hours=int(course["credit_hours"]),
            term_start=term_start,
            rng=rng,
            slot_pool=slot_pool,
            teaching_days=teaching_days,
        )

    return {
        "term_start": term_start.isoformat(),
        "term_weeks": TERM_WEEKS,
        "random_seed": seed,
        "teaching_weekdays": list(teaching_days),
        "courses": by_course,
    }


# --------------------------------------------------------------------------
# Querying a generated schedule
# --------------------------------------------------------------------------

def sessions_on_day(schedule: dict, week_number: int, weekday: int) -> List[dict]:
    """Every session across all courses on one specific day of the term.

    A course with no slot that day contributes nothing, which is what lets the
    UI show "only the courses that actually meet today".
    """
    found: List[dict] = []
    for course in schedule["courses"].values():
        for session in course["sessions"]:
            if session["week_number"] == week_number and session["weekday"] == weekday:
                found.append(session)
    found.sort(key=lambda s: (s["slot"], s["course_code"]))
    return found


def course_sessions_on_day(schedule: dict, course_id: str, week_number: int, weekday: int) -> List[dict]:
    """Sessions for one course on one day. Empty when it does not meet."""
    course = schedule["courses"].get(course_id)
    if course is None:
        return []
    return [
        session
        for session in course["sessions"]
        if session["week_number"] == week_number and session["weekday"] == weekday
    ]


def courses_meeting_on_day(schedule: dict, week_number: int, weekday: int) -> List[str]:
    """Course codes that have at least one slot on the given day."""
    return sorted({
        session["course_code"]
        for session in sessions_on_day(schedule, week_number, weekday)
    })


def sessions_up_to(schedule: dict, course_id: str, cutoff: date) -> List[dict]:
    """All of a course's sessions dated on or before ``cutoff``.

    This is the filter behind the "send up to" control: n8n rejects a chunk
    carrying any session dated after ``today_date``, so the cutoff is applied
    here rather than downstream.
    """
    course = schedule["courses"].get(course_id)
    if course is None:
        return []
    cutoff_iso = cutoff.isoformat()
    return [session for session in course["sessions"] if session["date"] <= cutoff_iso]


def to_session_dsc(session: dict) -> dict:
    """Strip simulator bookkeeping, leaving the portal-shaped SessionDsc."""
    return {
        "course_code": session["course_code"],
        "session_type": session["session_type"],
        "date": session["date"],
        "slot": session["slot"],
        "duration": session["duration"],
    }
