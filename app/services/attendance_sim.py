"""Test-only attendance warning simulator.

Generates a large, reusable seed dataset (students + fixed enrollment) and a
"simulate next day" generator that evolves warning levels over repeated calls so
the n8n notification flow can be exercised across many simulated days.

Design notes
------------
* Enrollment is **immutable** across simulated days. It lives in
  ``seeds/attendance_enrollment.json`` and is never rewritten by the generator.
* Warning levels are **mutable** and live in ``seeds/attendance_sim_state.json``
  alongside the day counter and per-day transition history.
* Nothing here touches the real database, the finalize endpoint, or the
  ``build_attendance_snapshot`` production path. It is import-safe and
  side-effect free until a function is called.
"""

from __future__ import annotations

import json
import os
import random
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

# --------------------------------------------------------------------------
# Paths / configuration
# --------------------------------------------------------------------------

REPO_ROOT = Path(__file__).resolve().parents[2]
SEED_DIR = Path(os.getenv("ATTENDANCE_SIM_SEED_DIR", REPO_ROOT / "seeds"))
ENROLLMENT_PATH = SEED_DIR / "attendance_enrollment.json"
STATE_PATH = SEED_DIR / "attendance_sim_state.json"

DEFAULT_STUDENT_COUNT = int(os.getenv("ATTENDANCE_SIM_STUDENTS", "3000"))
DEFAULT_ID_YEAR = int(os.getenv("ATTENDANCE_SIM_ID_YEAR", "2024"))
DEFAULT_SEED = int(os.getenv("ATTENDANCE_SIM_RANDOM_SEED", "20240001"))

# Every generated recipient routes through one real inbox using +tag aliasing,
# so a live run can never fan out to 3,000 unrelated addresses.
TEST_INBOX = os.getenv("ATTENDANCE_SIM_TEST_INBOX", "lakshyrupani.lr@gmail.com")

# Chunk size for the finalize submission. Kept as a parameter everywhere; this
# is only the fallback default. Prefers the backend's configured value
# (settings.attendance_chunk_size) so the simulator and the real chunked
# submitter never drift apart.
def _default_chunk_size() -> int:
    override = os.getenv("ATTENDANCE_CHUNK_SIZE")
    if override:
        return int(override)
    try:
        from app.config import get_settings

        return int(getattr(get_settings(), "attendance_chunk_size", 200))
    except Exception:  # pragma: no cover - config import is optional here
        return 200


DEFAULT_CHUNK_SIZE = _default_chunk_size()

WARNING_LEVEL_LABELS = {"0": "Good", "1": "Warning 1", "2": "Warning 2", "3": "Drop"}
MIN_LEVEL, MAX_LEVEL = 0, 3

# Transition weights (must sum to 1.0).
W_SAME = 0.70          # most student-courses do not move on a given day
W_STEP_1 = 0.20        # move by exactly one level, up or down
W_JUMP = 0.10          # multi-level jump or a straight drop to level 3

# Share of student-courses that replay an already-seen transition on the SAME
# simulated day, to stress the repeat-notification path.
REPEAT_RATE = float(os.getenv("ATTENDANCE_SIM_REPEAT_RATE", "0.025"))

# --------------------------------------------------------------------------
# Course catalog (18 courses, mixed departments and levels)
# --------------------------------------------------------------------------

COURSE_CATALOG: List[Tuple[str, str]] = [
    ("CS-101", "Introduction to Computer Science"),
    ("CS-201", "Data Structures and Algorithms"),
    ("CS-301", "Database Systems"),
    ("CS-302", "Operating Systems"),
    ("CS-401", "Machine Learning"),
    ("CS-402", "Computer Networks"),
    ("SE-210", "Software Engineering Principles"),
    ("SE-330", "Web Application Development"),
    ("DS-220", "Statistical Methods for Data Science"),
    ("DS-410", "Big Data Analytics"),
    ("MA-101", "Calculus I"),
    ("MA-201", "Linear Algebra"),
    ("MA-305", "Discrete Mathematics"),
    ("PH-101", "Physics I"),
    ("PH-202", "Electricity and Magnetism"),
    ("EN-101", "Technical English"),
    ("BA-150", "Principles of Management"),
    ("EE-240", "Digital Logic Design"),
]

COURSE_NAMES: Dict[str, str] = dict(COURSE_CATALOG)

MIN_COURSES_PER_STUDENT = 3
MAX_COURSES_PER_STUDENT = 6

FIRST_NAMES = [
    "Ahmed", "Fatima", "Mohamed", "Aisha", "Youssef", "Mariam", "Karim", "Nour",
    "Sara", "Omar", "Laila", "Hassan", "Salma", "Tarek", "Habiba", "Khaled",
    "Rana", "Amir", "Dina", "Mostafa", "Yara", "Ali", "Hana", "Bilal",
    "Zeinab", "Adel", "Malak", "Ibrahim", "Farida", "Seif", "Nadia", "Ziad",
    "Rania", "Hamza", "Layla", "Tamer", "Alia", "Sherif", "Amina", "Wael",
    "Lakshy", "Ananya", "Rohan", "Priya", "Arjun", "Meera", "Kabir", "Ishita",
    "Daniel", "Sophia", "Lucas", "Emma", "Noah", "Olivia", "Ethan", "Mia",
]

LAST_NAMES = [
    "Hassan", "Ali", "Omar", "Mahmoud", "Ibrahim", "Adel", "Mostafa", "El-Din",
    "Khaled", "Tarek", "Samir", "Nabil", "Fouad", "Zaki", "Rashad", "Gamal",
    "Sabry", "Lotfy", "Hegazy", "Shafik", "Badr", "Ezzat", "Fahmy", "Ragab",
    "Rupani", "Sharma", "Patel", "Nair", "Iyer", "Kapoor", "Reddy", "Bose",
    "Silva", "Novak", "Kovacs", "Fischer", "Moreau", "Rossi", "Andersen", "Costa",
]


# --------------------------------------------------------------------------
# Helpers
# --------------------------------------------------------------------------

def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def _student_id(sequence: int, year: int = DEFAULT_ID_YEAR) -> str:
    return f"STU-{year}-{sequence:04d}"


def recipient_for(student_id: str, inbox: str = TEST_INBOX) -> str:
    """Build a +tag alias so every notification lands in one real test inbox."""
    local, _, domain = inbox.partition("@")
    tag = student_id.replace("-", "")
    return f"{local}+{tag}@{domain}"


def _ensure_seed_dir() -> None:
    SEED_DIR.mkdir(parents=True, exist_ok=True)


def _read_json(path: Path) -> Optional[dict]:
    if not path.is_file():
        return None
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def _write_json(path: Path, payload: dict) -> None:
    _ensure_seed_dir()
    tmp = path.with_suffix(path.suffix + ".tmp")
    with tmp.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2)
        handle.write("\n")
    tmp.replace(path)


# --------------------------------------------------------------------------
# Enrollment seed (immutable "current enrollment")
# --------------------------------------------------------------------------

def build_enrollment_seed(
    student_count: int = DEFAULT_STUDENT_COUNT,
    seed: int = DEFAULT_SEED,
    id_year: int = DEFAULT_ID_YEAR,
    inbox: str = TEST_INBOX,
) -> dict:
    """Build the deterministic enrollment seed. Does not write to disk."""
    rng = random.Random(seed)
    students: List[dict] = []

    for sequence in range(1, student_count + 1):
        sid = _student_id(sequence, id_year)
        name = f"{rng.choice(FIRST_NAMES)} {rng.choice(LAST_NAMES)}"
        n_courses = rng.randint(MIN_COURSES_PER_STUDENT, MAX_COURSES_PER_STUDENT)
        codes = sorted(rng.sample([code for code, _ in COURSE_CATALOG], n_courses))
        students.append({
            "student_id": sid,
            "student_name": name,
            "recipient": recipient_for(sid, inbox),
            "courses": [{"course_id": code, "course_name": COURSE_NAMES[code]} for code in codes],
        })

    course_records = sum(len(s["courses"]) for s in students)
    return {
        "generated_at": _utc_now_iso(),
        "random_seed": seed,
        "test_inbox": inbox,
        "students_count": len(students),
        "course_records_count": course_records,
        "course_catalog": [{"course_id": c, "course_name": n} for c, n in COURSE_CATALOG],
        "students": students,
    }


def write_enrollment_seed(
    student_count: int = DEFAULT_STUDENT_COUNT,
    seed: int = DEFAULT_SEED,
    id_year: int = DEFAULT_ID_YEAR,
    inbox: str = TEST_INBOX,
    overwrite: bool = False,
) -> dict:
    """Persist the enrollment seed, refusing to clobber it unless asked."""
    if ENROLLMENT_PATH.is_file() and not overwrite:
        raise FileExistsError(
            f"{ENROLLMENT_PATH} already exists. Pass overwrite=True to regenerate "
            "(this resets enrollment, which should stay stable across test days)."
        )
    payload = build_enrollment_seed(student_count, seed, id_year, inbox)
    _write_json(ENROLLMENT_PATH, payload)
    return payload


def load_enrollment_seed(auto_create: bool = True) -> dict:
    """Load enrollment, generating it on first use when allowed."""
    existing = _read_json(ENROLLMENT_PATH)
    if existing is not None:
        return existing
    if not auto_create:
        raise FileNotFoundError(
            f"No enrollment seed at {ENROLLMENT_PATH}. Run seed_attendance_sim.py first."
        )
    return write_enrollment_seed(overwrite=False)


# --------------------------------------------------------------------------
# Simulation state (mutable warning levels)
# --------------------------------------------------------------------------

def _new_state(enrollment: dict) -> dict:
    """Day 0: everyone starts clean, matching a fresh term."""
    return {
        "created_at": _utc_now_iso(),
        "updated_at": _utc_now_iso(),
        "day_number": 0,
        "last_finalize_id": None,
        "history": [],
        "levels": {
            student["student_id"]: {course["course_id"]: 0 for course in student["courses"]}
            for student in enrollment["students"]
        },
    }


def load_state(enrollment: Optional[dict] = None) -> dict:
    enrollment = enrollment or load_enrollment_seed()
    existing = _read_json(STATE_PATH)
    if existing is None:
        state = _new_state(enrollment)
        _write_json(STATE_PATH, state)
        return state

    # Heal the state if enrollment gained/lost rows (should be rare).
    levels = existing.setdefault("levels", {})
    for student in enrollment["students"]:
        bucket = levels.setdefault(student["student_id"], {})
        for course in student["courses"]:
            bucket.setdefault(course["course_id"], 0)
    return existing


def save_state(state: dict) -> None:
    state["updated_at"] = _utc_now_iso()
    _write_json(STATE_PATH, state)


def reset_state(enrollment: Optional[dict] = None) -> dict:
    """Back to day 0 with every level at Good. Enrollment is untouched."""
    enrollment = enrollment or load_enrollment_seed()
    state = _new_state(enrollment)
    _write_json(STATE_PATH, state)
    return state


# --------------------------------------------------------------------------
# Transition engine
# --------------------------------------------------------------------------

def next_warning_level(current: int, rng: random.Random) -> Tuple[int, str]:
    """Pick the next level for one student-course.

    Returns ``(level, kind)`` where kind is one of ``same``, ``step_1``,
    ``jump_drop`` or ``jump``. Weights hold at the boundaries by redirecting an
    impossible move to the only legal direction rather than silently clamping
    back to ``same`` (which would inflate the 70% bucket).
    """
    roll = rng.random()

    if roll < W_SAME:
        return current, "same"

    if roll < W_SAME + W_STEP_1:
        options = []
        if current > MIN_LEVEL:
            options.append(current - 1)
        if current < MAX_LEVEL:
            options.append(current + 1)
        return rng.choice(options), "step_1"

    # Remaining ~10%: a jump of 2+ levels, biased toward the level-3 drop so
    # drop-notice emails get exercised every day.
    if current != MAX_LEVEL and rng.random() < 0.5:
        return MAX_LEVEL, "jump_drop"

    candidates = [lvl for lvl in range(MIN_LEVEL, MAX_LEVEL + 1) if abs(lvl - current) >= 2]
    if not candidates:
        candidates = [MAX_LEVEL if current != MAX_LEVEL else MIN_LEVEL]
    return rng.choice(candidates), "jump"


# --------------------------------------------------------------------------
# Day generator
# --------------------------------------------------------------------------

def simulate_next_day(
    chunk_size: int = DEFAULT_CHUNK_SIZE,
    seed: Optional[int] = None,
    persist: bool = True,
    repeat_rate: float = REPEAT_RATE,
    finalized_at: Optional[str] = None,
) -> dict:
    """Advance the simulation by one day and return the chunked payload set.

    Each call re-rolls every student-course against the weighted transition
    table, advances the stored day counter, and returns ready-to-POST chunks in
    the exact envelope the finalize submission uses.
    """
    if chunk_size < 1:
        raise ValueError("chunk_size must be >= 1")

    enrollment = load_enrollment_seed()
    state = load_state(enrollment)

    day_number = int(state.get("day_number", 0)) + 1
    rng = random.Random(seed if seed is not None else f"{DEFAULT_SEED}:{day_number}:{uuid.uuid4()}")

    levels: Dict[str, Dict[str, int]] = state["levels"]
    counts = {"same": 0, "step_1": 0, "jump_drop": 0, "jump": 0}
    changed = 0
    drops = 0
    transitions: List[dict] = []          # every student-course that MOVED today
    student_records: List[dict] = []

    for student in enrollment["students"]:
        sid = student["student_id"]
        bucket = levels.setdefault(sid, {})
        courses_out: List[dict] = []

        for course in student["courses"]:
            code = course["course_id"]
            previous = int(bucket.get(code, 0))
            level, kind = next_warning_level(previous, rng)

            bucket[code] = level
            counts[kind] += 1
            if level != previous:
                changed += 1
                transitions.append({
                    "student_id": sid,
                    "course_id": code,
                    "from": previous,
                    "to": level,
                    "kind": kind,
                })
            if level == MAX_LEVEL and previous != MAX_LEVEL:
                drops += 1

            courses_out.append({
                "course_id": code,
                "course_name": course["course_name"],
                "warning_level": level,
            })

        student_records.append({
            "student_id": sid,
            "student_name": student["student_name"],
            "recipient": student["recipient"],
            "courses": courses_out,
        })

    # ---- same-day repeat records -----------------------------------------
    # Replay a slice of today's transitions as additional student entries.
    # Appending them at the end pushes each duplicate into a later chunk than
    # its original, which is what actually stresses the repeat-notification
    # path (the workflow must dedupe across chunks, not just within one).
    repeats: List[dict] = []
    total_pairs = sum(len(s["courses"]) for s in student_records)
    repeat_target = int(round(total_pairs * max(0.0, repeat_rate)))
    if repeat_target and transitions:
        by_student: Dict[str, List[dict]] = {}
        for pick in rng.sample(transitions, min(repeat_target, len(transitions))):
            by_student.setdefault(pick["student_id"], []).append(pick)
            repeats.append(pick)

        index = {s["student_id"]: s for s in student_records}
        for sid in by_student:
            origin = index[sid]
            # A repeat is the SAME student submitted twice in one day, so it
            # carries the full enrolled course set. Sending only the replayed
            # courses would look like a shrunken enrollment, which the
            # workflow reads as "no longer enrolled".
            student_records.append({
                **origin,
                "courses": [dict(course) for course in origin["courses"]],
            })

    finalize_id = str(uuid.uuid4())
    finalized_at = finalized_at or _utc_now_iso()
    chunks = chunk_students(
        student_records,
        finalize_id=finalize_id,
        finalized_at=finalized_at,
        chunk_size=chunk_size,
    )

    summary = {
        "day_number": day_number,
        "finalize_id": finalize_id,
        "finalized_at": finalized_at,
        "students_count": len(enrollment["students"]),
        "student_records_sent": len(student_records),
        "course_records_sent": sum(len(s["courses"]) for s in student_records),
        "chunk_size": chunk_size,
        "chunk_count": len(chunks),
        "changed_count": changed,
        "unchanged_count": counts["same"],
        "new_drops": drops,
        "repeat_records": len(repeats),
        "transition_breakdown": counts,
        "level_distribution": level_distribution(levels),
    }

    if persist:
        state["day_number"] = day_number
        state["last_finalize_id"] = finalize_id
        history = state.setdefault("history", [])
        history.append({k: summary[k] for k in (
            "day_number", "finalize_id", "finalized_at", "changed_count",
            "new_drops", "repeat_records", "chunk_count", "level_distribution",
        )})
        state["history"] = history[-100:]
        save_state(state)

    return {"summary": summary, "chunks": chunks, "repeats": repeats}


def level_distribution(levels: Dict[str, Dict[str, int]]) -> Dict[str, int]:
    dist = {"0": 0, "1": 0, "2": 0, "3": 0}
    for bucket in levels.values():
        for value in bucket.values():
            dist[str(int(value))] += 1
    return dist


# --------------------------------------------------------------------------
# Chunking
# --------------------------------------------------------------------------

def chunk_students(
    students: List[dict],
    finalize_id: str,
    finalized_at: str,
    chunk_size: int = DEFAULT_CHUNK_SIZE,
) -> List[dict]:
    """Split ``students`` into the 1-based chunk envelopes the webhook expects.

    ``chunk_count`` is identical on every chunk so the receiver can detect a
    missing chunk for a given ``finalize_id``.
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
            "warning_level_labels": WARNING_LEVEL_LABELS,
            "students": batch,
        }
        for position, batch in enumerate(batches, start=1)
    ]


# --------------------------------------------------------------------------
# Read-only inspection helpers (used by the dev UI)
# --------------------------------------------------------------------------

def current_status() -> dict:
    enrollment = load_enrollment_seed()
    state = load_state(enrollment)
    return {
        "students_count": enrollment["students_count"],
        "course_records_count": enrollment["course_records_count"],
        "course_catalog_size": len(enrollment["course_catalog"]),
        "test_inbox": enrollment.get("test_inbox", TEST_INBOX),
        "day_number": state.get("day_number", 0),
        "last_finalize_id": state.get("last_finalize_id"),
        "level_distribution": level_distribution(state["levels"]),
        "history": state.get("history", [])[-20:],
        "enrollment_path": str(ENROLLMENT_PATH),
        "state_path": str(STATE_PATH),
    }


def student_timeline(student_id: str) -> dict:
    """Current per-course levels for one student, for spot-checking the UI."""
    enrollment = load_enrollment_seed()
    state = load_state(enrollment)
    match = next((s for s in enrollment["students"] if s["student_id"] == student_id), None)
    if match is None:
        raise KeyError(student_id)
    bucket = state["levels"].get(student_id, {})
    return {
        "student_id": student_id,
        "student_name": match["student_name"],
        "recipient": match["recipient"],
        "day_number": state.get("day_number", 0),
        "courses": [
            {
                "course_id": course["course_id"],
                "course_name": course["course_name"],
                "warning_level": int(bucket.get(course["course_id"], 0)),
            }
            for course in match["courses"]
        ],
    }
