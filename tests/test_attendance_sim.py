import json
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from app.services import attendance_sim


class AttendanceSimTests(unittest.TestCase):
    """Exercises the simulator against a throwaway seed dir, never the real one."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.patchers = [
            patch.object(attendance_sim, "SEED_DIR", self.tmp),
            patch.object(attendance_sim, "ENROLLMENT_PATH", self.tmp / "enrollment.json"),
            patch.object(attendance_sim, "STATE_PATH", self.tmp / "state.json"),
        ]
        for p in self.patchers:
            p.start()
        self.enrollment = attendance_sim.write_enrollment_seed(student_count=300, overwrite=True)
        attendance_sim.reset_state(self.enrollment)

    def tearDown(self):
        for p in self.patchers:
            p.stop()
        shutil.rmtree(self.tmp, ignore_errors=True)

    # ---- enrollment completeness ----------------------------------------

    def test_every_payload_entry_carries_the_full_enrolled_course_set(self):
        """Enrollment is fixed: every student entry on every day must list all
        of that student's courses, including level-0 ones, and including the
        same-day repeat entries."""
        enrolled = {
            s["student_id"]: {c["course_id"] for c in s["courses"]}
            for s in self.enrollment["students"]
        }
        for _ in range(5):
            result = attendance_sim.simulate_next_day(chunk_size=50)
            for chunk in result["chunks"]:
                for entry in chunk["students"]:
                    got = {c["course_id"] for c in entry["courses"]}
                    self.assertEqual(
                        got,
                        enrolled[entry["student_id"]],
                        f"{entry['student_id']} payload course set differs from enrollment",
                    )

    def test_repeat_entries_are_full_duplicates_of_their_origin(self):
        """A same-day repeat is the same student sent twice; both entries must
        carry an identical course array."""
        for _ in range(5):
            result = attendance_sim.simulate_next_day(chunk_size=50)
            by_student = {}
            for chunk in result["chunks"]:
                for entry in chunk["students"]:
                    by_student.setdefault(entry["student_id"], []).append(entry)
            repeated = {k: v for k, v in by_student.items() if len(v) > 1}
            self.assertTrue(repeated, "expected at least one same-day repeat")
            for sid, entries in repeated.items():
                first = {c["course_id"]: c["warning_level"] for c in entries[0]["courses"]}
                for other in entries[1:]:
                    self.assertEqual(
                        {c["course_id"]: c["warning_level"] for c in other["courses"]},
                        first,
                        f"repeat entry for {sid} does not match its origin",
                    )

    def test_level_zero_courses_are_never_dropped(self):
        result = attendance_sim.simulate_next_day(chunk_size=50)
        zeros = sum(
            1
            for chunk in result["chunks"]
            for entry in chunk["students"]
            for course in entry["courses"]
            if course["warning_level"] == 0
        )
        self.assertGreater(zeros, 0, "level-0 courses are missing from the payload")

    # ---- seed shape ------------------------------------------------------

    def test_seed_ids_names_and_tagged_recipients(self):
        students = self.enrollment["students"]
        self.assertEqual(len(students), 300)
        self.assertEqual(students[0]["student_id"], "STU-2024-0001")
        self.assertEqual(students[-1]["student_id"], "STU-2024-0300")
        for student in students:
            self.assertTrue(student["student_name"].strip())
            self.assertIn("+", student["recipient"])
            tag = student["student_id"].replace("-", "")
            self.assertIn(f"+{tag}@", student["recipient"])

    def test_every_student_has_3_to_6_unique_courses_from_catalog(self):
        catalog = {c for c, _ in attendance_sim.COURSE_CATALOG}
        self.assertGreaterEqual(len(catalog), 15)
        self.assertLessEqual(len(catalog), 20)
        for student in self.enrollment["students"]:
            codes = [c["course_id"] for c in student["courses"]]
            self.assertTrue(3 <= len(codes) <= 6)
            self.assertEqual(len(codes), len(set(codes)))
            self.assertTrue(set(codes) <= catalog)

    def test_seed_is_deterministic_for_a_given_random_seed(self):
        a = attendance_sim.build_enrollment_seed(student_count=50, seed=42)
        b = attendance_sim.build_enrollment_seed(student_count=50, seed=42)
        self.assertEqual(a["students"], b["students"])

    def test_seed_refuses_to_clobber_without_overwrite(self):
        with self.assertRaises(FileExistsError):
            attendance_sim.write_enrollment_seed(student_count=10, overwrite=False)

    # ---- enrollment stability -------------------------------------------

    def test_enrollment_is_unchanged_by_simulated_days(self):
        before = json.dumps(attendance_sim.load_enrollment_seed(), sort_keys=True)
        for _ in range(5):
            attendance_sim.simulate_next_day(chunk_size=50)
        after = json.dumps(attendance_sim.load_enrollment_seed(), sort_keys=True)
        self.assertEqual(before, after)

    def test_day_counter_advances_and_persists(self):
        self.assertEqual(attendance_sim.current_status()["day_number"], 0)
        for expected in (1, 2, 3):
            result = attendance_sim.simulate_next_day(chunk_size=50)
            self.assertEqual(result["summary"]["day_number"], expected)
            self.assertEqual(attendance_sim.current_status()["day_number"], expected)

    def test_reset_clears_levels_but_keeps_enrollment(self):
        attendance_sim.simulate_next_day(chunk_size=50)
        attendance_sim.reset_state()
        status = attendance_sim.current_status()
        self.assertEqual(status["day_number"], 0)
        self.assertEqual(status["level_distribution"]["1"], 0)
        self.assertEqual(status["students_count"], 300)

    # ---- transition weighting -------------------------------------------

    def test_transition_weights_match_70_20_10(self):
        totals = {"same": 0, "step_1": 0, "jump_drop": 0, "jump": 0}
        for _ in range(12):
            summary = attendance_sim.simulate_next_day(chunk_size=100)["summary"]
            for key, value in summary["transition_breakdown"].items():
                totals[key] += value

        grand = sum(totals.values())
        same = totals["same"] / grand
        step = totals["step_1"] / grand
        jump = (totals["jump"] + totals["jump_drop"]) / grand

        self.assertAlmostEqual(same, 0.70, delta=0.03)
        self.assertAlmostEqual(step, 0.20, delta=0.03)
        self.assertAlmostEqual(jump, 0.10, delta=0.03)

    def test_levels_stay_within_0_to_3(self):
        for _ in range(8):
            result = attendance_sim.simulate_next_day(chunk_size=100)
            for chunk in result["chunks"]:
                for student in chunk["students"]:
                    for course in student["courses"]:
                        self.assertIn(course["warning_level"], (0, 1, 2, 3))

    def test_step_1_moves_exactly_one_level(self):
        import random
        rng = random.Random(7)
        for current in (0, 1, 2, 3):
            for _ in range(300):
                level, kind = attendance_sim.next_warning_level(current, rng)
                if kind == "step_1":
                    self.assertEqual(abs(level - current), 1)
                elif kind == "same":
                    self.assertEqual(level, current)
                elif kind == "jump":
                    self.assertGreaterEqual(abs(level - current), 2)

    def test_drops_are_produced_every_day(self):
        for _ in range(3):
            summary = attendance_sim.simulate_next_day(chunk_size=100)["summary"]
            self.assertGreater(summary["new_drops"], 0)

    # ---- same-day repeats ------------------------------------------------

    def test_same_day_repeats_are_generated_in_range(self):
        result = attendance_sim.simulate_next_day(chunk_size=50)
        summary = result["summary"]
        pairs = sum(len(s["courses"]) for s in self.enrollment["students"])
        rate = summary["repeat_records"] / pairs
        self.assertGreater(summary["repeat_records"], 0)
        self.assertTrue(0.01 <= rate <= 0.05, f"repeat rate {rate:.4f} outside 1-5%")

    def test_repeats_duplicate_a_student_course_within_the_same_day(self):
        result = attendance_sim.simulate_next_day(chunk_size=50)
        seen = {}
        entries_per_student = {}
        for chunk in result["chunks"]:
            for student in chunk["students"]:
                entries_per_student.setdefault(student["student_id"], []).append(
                    chunk["chunk_index"]
                )
                for course in student["courses"]:
                    key = (student["student_id"], course["course_id"])
                    seen.setdefault(key, []).append(chunk["chunk_index"])

        duplicated = {k: v for k, v in seen.items() if len(v) > 1}
        self.assertTrue(duplicated, "expected same-day duplicate student-courses")

        # A repeat re-sends the student's FULL course array, so the number of
        # duplicated student-course pairs is the total enrolment of the
        # repeated students -- not the count of replayed transitions. What must
        # hold is that every duplicated pair belongs to a student who appears
        # more than once, and that repeat_records never exceeds those pairs.
        repeated_students = {s for s, idx in entries_per_student.items() if len(idx) > 1}
        self.assertTrue(repeated_students)
        for student_id, _course_id in duplicated:
            self.assertIn(student_id, repeated_students)
        self.assertLessEqual(result["summary"]["repeat_records"], len(duplicated))

        # Each duplicate must land in a different chunk than its original, so
        # the workflow's dedupe is tested across chunk boundaries.
        for key, indices in duplicated.items():
            self.assertGreater(len(set(indices)), 1, f"{key} repeated inside one chunk only")

    # ---- chunking --------------------------------------------------------

    def test_chunk_envelope_matches_finalize_contract(self):
        result = attendance_sim.simulate_next_day(chunk_size=200)
        chunks = result["chunks"]
        self.assertGreater(len(chunks), 1)

        finalize_ids = {c["finalize_id"] for c in chunks}
        self.assertEqual(len(finalize_ids), 1)

        for position, chunk in enumerate(chunks, start=1):
            self.assertEqual(chunk["chunk_index"], position)          # 1-based
            self.assertEqual(chunk["chunk_count"], len(chunks))       # identical everywhere
            self.assertEqual(set(chunk), {
                "finalize_id", "chunk_index", "chunk_count",
                "finalized_at", "warning_level_labels", "students",
            })
            self.assertLessEqual(len(chunk["students"]), 200)
            self.assertTrue(chunk["finalized_at"].endswith("Z"))

    def test_student_entry_shape_matches_snapshot_builder(self):
        chunk = attendance_sim.simulate_next_day(chunk_size=50)["chunks"][0]
        student = chunk["students"][0]
        self.assertEqual(set(student), {"student_id", "student_name", "recipient", "courses"})
        self.assertEqual(set(student["courses"][0]), {"course_id", "course_name", "warning_level"})
        self.assertIsInstance(student["courses"][0]["warning_level"], int)

    def test_no_student_records_are_lost_across_chunks(self):
        result = attendance_sim.simulate_next_day(chunk_size=37)
        emitted = sum(len(c["students"]) for c in result["chunks"])
        self.assertEqual(emitted, result["summary"]["student_records_sent"])

    def test_chunk_size_one_and_oversized_chunk_size(self):
        single = attendance_sim.chunk_students(
            [{"student_id": "A"}, {"student_id": "B"}], "fid", "2026-01-01T00:00:00Z", chunk_size=1
        )
        self.assertEqual([c["chunk_index"] for c in single], [1, 2])
        self.assertTrue(all(c["chunk_count"] == 2 for c in single))

        huge = attendance_sim.chunk_students(
            [{"student_id": "A"}], "fid", "2026-01-01T00:00:00Z", chunk_size=10_000
        )
        self.assertEqual(len(huge), 1)
        self.assertEqual(huge[0]["chunk_count"], 1)

    def test_invalid_chunk_size_rejected(self):
        with self.assertRaises(ValueError):
            attendance_sim.simulate_next_day(chunk_size=0)

    # ---- misc ------------------------------------------------------------

    def test_persist_false_leaves_state_untouched(self):
        attendance_sim.simulate_next_day(chunk_size=50)
        day = attendance_sim.current_status()["day_number"]
        attendance_sim.simulate_next_day(chunk_size=50, persist=False)
        self.assertEqual(attendance_sim.current_status()["day_number"], day)

    def test_student_timeline_lookup(self):
        attendance_sim.simulate_next_day(chunk_size=50)
        timeline = attendance_sim.student_timeline("STU-2024-0002")
        self.assertEqual(timeline["student_id"], "STU-2024-0002")
        self.assertTrue(3 <= len(timeline["courses"]) <= 6)
        with self.assertRaises(KeyError):
            attendance_sim.student_timeline("STU-9999-9999")


if __name__ == "__main__":
    unittest.main()
