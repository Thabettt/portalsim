#!/usr/bin/env python3
"""Generate the persistent attendance-simulator seed.

    python seed_attendance_sim.py                 # create enrollment (3,000 students)
    python seed_attendance_sim.py --force         # regenerate enrollment from scratch
    python seed_attendance_sim.py --students 500  # smaller run
    python seed_attendance_sim.py --reset-days    # keep enrollment, wipe warning levels
    python seed_attendance_sim.py --simulate 3    # advance 3 simulated days, print summary

Enrollment is written once to seeds/attendance_enrollment.json and is meant to
stay stable across test days. Only warning levels change, and they live in the
separate seeds/attendance_sim_state.json.
"""

import argparse
import json
import sys

from app.services.attendance_sim import (
    DEFAULT_CHUNK_SIZE,
    DEFAULT_ID_YEAR,
    DEFAULT_SEED,
    DEFAULT_STUDENT_COUNT,
    ENROLLMENT_PATH,
    STATE_PATH,
    TEST_INBOX,
    current_status,
    load_enrollment_seed,
    reset_state,
    simulate_next_day,
    write_enrollment_seed,
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--students", type=int, default=DEFAULT_STUDENT_COUNT)
    parser.add_argument("--year", type=int, default=DEFAULT_ID_YEAR, help="Year segment of STU-<year>-NNNN")
    parser.add_argument("--inbox", default=TEST_INBOX, help="Real inbox that all +tag aliases route to")
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED)
    parser.add_argument("--force", action="store_true", help="Regenerate enrollment even if it exists")
    parser.add_argument("--reset-days", action="store_true", help="Reset warning levels to day 0")
    parser.add_argument("--simulate", type=int, default=0, metavar="N", help="Advance N simulated days")
    parser.add_argument("--chunk-size", type=int, default=DEFAULT_CHUNK_SIZE)
    parser.add_argument("--dump-chunk", type=int, metavar="INDEX", help="Print one chunk (1-based) from the last simulated day")
    args = parser.parse_args()

    if args.force or not ENROLLMENT_PATH.is_file():
        enrollment = write_enrollment_seed(
            student_count=args.students,
            seed=args.seed,
            id_year=args.year,
            inbox=args.inbox,
            overwrite=True,
        )
        print(f"Wrote enrollment seed -> {ENROLLMENT_PATH}")
        print(f"  students        : {enrollment['students_count']}")
        print(f"  course records  : {enrollment['course_records_count']}")
        print(f"  course catalog  : {len(enrollment['course_catalog'])} courses")
        print(f"  sample student  : {enrollment['students'][0]['student_id']} "
              f"({enrollment['students'][0]['recipient']})")
        reset_state(enrollment)
        print(f"Initialised warning state -> {STATE_PATH} (day 0, all levels Good)")
    else:
        enrollment = load_enrollment_seed()
        print(f"Enrollment seed already present ({enrollment['students_count']} students). "
              f"Use --force to regenerate.")

    if args.reset_days:
        reset_state(enrollment)
        print("Warning levels reset to day 0. Enrollment untouched.")

    last = None
    for _ in range(max(0, args.simulate)):
        last = simulate_next_day(chunk_size=args.chunk_size)
        summary = last["summary"]
        dist = summary["level_distribution"]
        print(
            f"Day {summary['day_number']:>3} | changed {summary['changed_count']:>5} "
            f"| new drops {summary['new_drops']:>4} | repeats {summary['repeat_records']:>3} "
            f"| chunks {summary['chunk_count']:>3} "
            f"| L0 {dist['0']} L1 {dist['1']} L2 {dist['2']} L3 {dist['3']}"
        )

    if args.dump_chunk is not None:
        if last is None:
            print("Nothing to dump: pass --simulate N alongside --dump-chunk.", file=sys.stderr)
            return 1
        chunks = last["chunks"]
        if not 1 <= args.dump_chunk <= len(chunks):
            print(f"--dump-chunk must be between 1 and {len(chunks)}", file=sys.stderr)
            return 1
        chunk = dict(chunks[args.dump_chunk - 1])
        chunk["students"] = chunk["students"][:2]
        print(json.dumps(chunk, indent=2))

    status = current_status()
    print(f"\nCurrent day: {status['day_number']} | distribution: {status['level_distribution']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
