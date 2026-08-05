"""Tests for the fixed 12-week term: schedule rules, derived levels, cutoff."""

import shutil
import tempfile
import unittest
from collections import Counter
from datetime import date
from pathlib import Path
from unittest.mock import patch

from app.services import attendance_sim, term_attendance
from app.services import term_schedule as ts


class TermScheduleRulesTests(unittest.TestCase):
    """The credit-hour rules that decide how many slots a course gets."""

    TERM_START = date(2026, 8, 2)  # a Sunday

    def _schedule(self, credit_hours, seed=7):
        return ts.build_term_schedule(
            [{"course_id": "X-100", "credit_hours": credit_hours}],
            term_start=self.TERM_START,
            seed=seed,
        )["courses"]["X-100"]

    def test_term_start_is_normalised_to_a_sunday(self):
        for offset in range(7):
            probe = date(2026, 8, 3) + __import__("datetime").timedelta(days=offset)
            start = ts.term_start_sunday(probe)
            self.assertEqual(start.weekday(), ts.SUNDAY)
            self.assertLessEqual(start, probe)

    def test_four_credits_is_one_slot_every_week_for_twelve_weeks(self):
        course = self._schedule(4)
        per_week = Counter(s["week_number"] for s in course["sessions"])
        self.assertEqual(sorted(per_week), list(range(1, 13)))
        self.assertEqual(set(per_week.values()), {1})
        self.assertEqual(len(course["sessions"]), 12)

    def test_eight_credits_is_two_slots_every_week_on_two_distinct_days(self):
        course = self._schedule(8)
        per_week = Counter(s["week_number"] for s in course["sessions"])
        self.assertEqual(sorted(per_week), list(range(1, 13)))
        self.assertEqual(set(per_week.values()), {2})
        self.assertEqual(len(course["sessions"]), 24)

        self.assertEqual(len(set(course["weekdays"])), 2, "slots must fall on two different days")
        for week in range(1, 13):
            days = {s["weekday"] for s in course["sessions"] if s["week_number"] == week}
            self.assertEqual(len(days), 2, f"week {week} put both slots on one day")

    def test_six_credits_alternates_one_then_two_slots_per_week(self):
        course = self._schedule(6)
        per_week = Counter(s["week_number"] for s in course["sessions"])
        counts = [per_week[w] for w in range(1, 13)]
        self.assertEqual(counts, [1, 2, 1, 2, 1, 2, 1, 2, 1, 2, 1, 2])
        self.assertEqual(len(course["sessions"]), 18)

    def test_sessions_only_ever_fall_on_teaching_days(self):
        for credits in (4, 6, 8):
            course = self._schedule(credits)
            for session in course["sessions"]:
                self.assertIn(session["weekday"], ts.TEACHING_WEEKDAYS)
                self.assertIn(
                    date.fromisoformat(session["date"]).weekday(), ts.TEACHING_WEEKDAYS
                )

    def test_session_date_matches_its_week_and_weekday(self):
        course = self._schedule(8)
        for session in course["sessions"]:
            expected = ts.date_for(self.TERM_START, session["week_number"], session["weekday"])
            self.assertEqual(session["date"], expected.isoformat())

    def test_slot_assignment_is_random_but_stable_for_a_seed(self):
        first = self._schedule(8, seed=11)
        again = self._schedule(8, seed=11)
        self.assertEqual(first["sessions"], again["sessions"], "same seed must reproduce")

        # Across many courses the chosen days should not collapse to one day.
        schedule = ts.build_term_schedule(
            [{"course_id": f"C-{i}", "credit_hours": 4} for i in range(20)],
            term_start=self.TERM_START,
            seed=3,
        )
        chosen = {c["weekdays"][0] for c in schedule["courses"].values()}
        self.assertGreater(len(chosen), 1, "day assignment looks constant, not random")

    def test_session_dsc_shape_mirrors_the_real_portal(self):
        course = self._schedule(6)
        dsc = ts.to_session_dsc(course["sessions"][0])
        self.assertEqual(
            set(dsc),
            {"course_code", "session_type", "date", "slot", "duration"},
        )
        self.assertIn(dsc["session_type"], {"Lecture", "Tutorial"})
        self.assertIn(dsc["slot"], ts.AVAILABLE_SLOTS)


class WarningLevelDerivationTests(unittest.TestCase):
    """Levels are computed from attendance, not invented."""

    def test_level_thresholds_match_the_portal_rule(self):
        # 12-session course -> drop threshold ceil(12/4)+1 = 4
        self.assertEqual(term_attendance.warning_level_for(0, 12), 0)
        self.assertEqual(term_attendance.warning_level_for(1, 12), 0)
        self.assertEqual(term_attendance.warning_level_for(2, 12), 1)
        self.assertEqual(term_attendance.warning_level_for(3, 12), 2)
        self.assertEqual(term_attendance.warning_level_for(4, 12), 3)
        self.assertEqual(term_attendance.warning_level_for(9, 12), 3)

    def test_level_is_zero_when_no_sessions_have_happened(self):
        self.assertEqual(term_attendance.warning_level_for(0, 0), 0)
        self.assertEqual(term_attendance.level_from_sessions([], 0), 0)

    def test_level_counts_absences_only(self):
        sessions = [
            {"status": "absent"}, {"status": "present"},
            {"status": "absent"}, {"status": "present"},
        ]
        self.assertEqual(term_attendance.level_from_sessions(sessions, 12), 1)


class TermFinalizePayloadTests(unittest.TestCase):
    """End-to-end payload behaviour against a throwaway seed dir."""

    @classmethod
    def setUpClass(cls):
        cls.tmp = Path(tempfile.mkdtemp())
        cls.patchers = [
            patch.object(attendance_sim, "SEED_DIR", cls.tmp),
            patch.object(attendance_sim, "ENROLLMENT_PATH", cls.tmp / "enrollment.json"),
            patch.object(attendance_sim, "STATE_PATH", cls.tmp / "state.json"),
            patch.object(attendance_sim, "TERM_PATH", cls.tmp / "term.json"),
        ]
        for p in cls.patchers:
            p.start()
        cls.enrollment = attendance_sim.write_enrollment_seed(student_count=40, overwrite=True)
        attendance_sim.reset_state(cls.enrollment)
        cls.term = attendance_sim.load_term(cls.enrollment)

    @classmethod
    def tearDownClass(cls):
        for p in cls.patchers:
            p.stop()
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def test_legacy_seed_without_credit_hours_still_gets_real_credits(self):
        """A seed written before credit_hours existed must not collapse every
        course to 4 credits (1 slot/week) -- that silently kills the 6/8 rules."""
        legacy = {
            "course_catalog": [
                {"course_id": "CS-201", "course_name": "Data Structures"},
                {"course_id": "CS-301", "course_name": "Database Systems"},
                {"course_id": "CS-101", "course_name": "Intro"},
            ],
            "students": [],
        }
        resolved = {
            c["course_id"]: c["credit_hours"]
            for c in attendance_sim._catalog_with_credit_hours(legacy)
        }
        self.assertEqual(resolved["CS-201"], 8)
        self.assertEqual(resolved["CS-301"], 6)
        self.assertEqual(resolved["CS-101"], 4)

    def test_term_overview_reports_the_catalog_credit_hours(self):
        overview = attendance_sim.term_overview()
        by_course = {c["course_id"]: c for c in overview["courses"]}
        self.assertEqual(by_course["CS-201"]["credit_hours"], 8)
        self.assertEqual(by_course["CS-201"]["total_sessions"], 24)
        self.assertEqual(by_course["CS-301"]["credit_hours"], 6)
        self.assertEqual(by_course["CS-301"]["total_sessions"], 18)
        self.assertEqual(by_course["CS-101"]["credit_hours"], 4)
        self.assertEqual(by_course["CS-101"]["total_sessions"], 12)
        self.assertGreater(
            len({c["credit_hours"] for c in overview["courses"]}), 1,
            "all courses share one credit-hour value; the catalog was flattened",
        )

    def test_schedule_is_generated_once_and_not_rerolled_on_load(self):
        self.assertEqual(attendance_sim.load_term(self.enrollment), self.term)

    def test_no_session_is_dated_after_today_date(self):
        result = attendance_sim.finalize_through(3, ts.TUESDAY, chunk_size=10)
        cutoff = result["summary"]["today_date"]
        for chunk in result["chunks"]:
            self.assertEqual(chunk["today_date"], cutoff)
            for student in chunk["students"]:
                for course in student["courses"]:
                    for session in course["sessions"]:
                        self.assertLessEqual(session["date"], cutoff)

    def test_send_up_to_a_later_point_includes_strictly_more_sessions(self):
        early = attendance_sim.finalize_through(2, ts.SUNDAY, chunk_size=10)
        late = attendance_sim.finalize_through(8, ts.THURSDAY, chunk_size=10)
        self.assertLess(early["summary"]["sessions_count"], late["summary"]["sessions_count"])

    def test_history_is_not_rewritten_when_finalizing_further_ahead(self):
        def index(result):
            out = {}
            for chunk in result["chunks"]:
                for student in chunk["students"]:
                    for course in student["courses"]:
                        for s in course["sessions"]:
                            key = (student["student_id"], course["course_id"], s["date"], s["slot"])
                            out[key] = s["status"]
            return out

        early = index(attendance_sim.finalize_through(3, ts.MONDAY, chunk_size=10))
        late = index(attendance_sim.finalize_through(7, ts.MONDAY, chunk_size=10))
        for key, status in early.items():
            self.assertEqual(late[key], status, f"attendance changed under us for {key}")

    def test_every_enrolled_course_is_present_even_at_level_zero(self):
        enrolled = {
            s["student_id"]: {c["course_id"] for c in s["courses"]}
            for s in self.enrollment["students"]
        }
        # Week 1 Sunday: most courses have no session yet, but must still appear.
        result = attendance_sim.finalize_through(1, ts.SUNDAY, chunk_size=10)
        seen = set()
        for chunk in result["chunks"]:
            for student in chunk["students"]:
                got = {c["course_id"] for c in student["courses"]}
                self.assertEqual(got, enrolled[student["student_id"]])
                seen.add(student["student_id"])
        self.assertEqual(seen, set(enrolled))

    def test_courses_with_no_sessions_yet_are_still_listed(self):
        result = attendance_sim.finalize_through(1, ts.SUNDAY, chunk_size=10)
        empty = [
            course
            for chunk in result["chunks"]
            for student in chunk["students"]
            for course in student["courses"]
            if not course["sessions"]
        ]
        self.assertTrue(empty, "expected some courses to have no session on week 1 Sunday")
        for course in empty:
            self.assertEqual(course["warning_level"], 0)

    def test_warning_level_matches_the_absences_in_the_payload(self):
        result = attendance_sim.finalize_through(10, ts.THURSDAY, chunk_size=10)
        schedule = self.term["schedule"]
        for chunk in result["chunks"]:
            for student in chunk["students"]:
                for course in student["courses"]:
                    absences = sum(1 for s in course["sessions"] if s["status"] == "absent")
                    total = len(schedule["courses"][course["course_id"]]["sessions"])
                    self.assertEqual(
                        course["warning_level"],
                        term_attendance.warning_level_for(absences, total),
                        f"level does not follow from attendance for {course['course_id']}",
                    )

    def test_sessions_include_present_as_well_as_absent(self):
        result = attendance_sim.finalize_through(12, ts.THURSDAY, chunk_size=20)
        statuses = {
            s["status"]
            for chunk in result["chunks"]
            for student in chunk["students"]
            for course in student["courses"]
            for s in course["sessions"]
        }
        self.assertEqual(statuses, {"present", "absent"})

    def test_one_course_holds_at_most_one_session_per_date(self):
        """Spec section 2 puts a course's weekly slots on *different* days, so
        within a single course a date never repeats.

        NOTE: the section 7 example payload shows one course holding slots 3, 4
        and 5 on the same date (a multi-slot block). That contradicts section 2
        and is an open question for the spec owner -- see the handoff notes.
        Downstream must still tolerate repeated dates, which
        ``test_student_can_hold_several_sessions_on_one_date`` covers.
        """
        result = attendance_sim.finalize_through(12, ts.THURSDAY, chunk_size=20)
        for chunk in result["chunks"]:
            for student in chunk["students"]:
                for course in student["courses"]:
                    dates = [s["date"] for s in course["sessions"]]
                    self.assertEqual(
                        len(dates), len(set(dates)),
                        f"{course['course_id']} repeated a date; slots should be on distinct days",
                    )

    def test_student_can_hold_several_sessions_on_one_date(self):
        """Across courses a student really does sit multiple slots in a day, and
        those slots must not collide."""
        result = attendance_sim.finalize_through(12, ts.THURSDAY, chunk_size=20)
        found = False
        for chunk in result["chunks"]:
            for student in chunk["students"]:
                per_date = {}
                for course in student["courses"]:
                    for session in course["sessions"]:
                        per_date.setdefault(session["date"], []).append(session["slot"])
                if any(len(slots) > 1 for slots in per_date.values()):
                    found = True
        self.assertTrue(found, "expected a student to have multiple sessions on some date")

    # ---- chunk envelope --------------------------------------------------

    def test_chunk_envelope_fields(self):
        result = attendance_sim.finalize_through(4, ts.MONDAY, chunk_size=7)
        chunks = result["chunks"]
        finalize_ids = {c["finalize_id"] for c in chunks}
        self.assertEqual(len(finalize_ids), 1, "finalize_id must be shared across chunks")

        self.assertEqual([c["chunk_index"] for c in chunks], list(range(1, len(chunks) + 1)))
        self.assertEqual({c["chunk_count"] for c in chunks}, {len(chunks)})
        self.assertEqual({c["finalized_at"] for c in chunks}, {result["summary"]["finalized_at"]})

        sizes = [len(c["students"]) for c in chunks]
        self.assertTrue(all(size <= 7 for size in sizes))
        self.assertEqual(sum(sizes), result["summary"]["students_count"])

    def test_chunk_size_is_configurable(self):
        small = attendance_sim.finalize_through(4, ts.MONDAY, chunk_size=5)
        large = attendance_sim.finalize_through(4, ts.MONDAY, chunk_size=40)
        self.assertGreater(small["summary"]["chunk_count"], large["summary"]["chunk_count"])
        self.assertEqual(large["summary"]["chunk_count"], 1)

    def test_finalize_id_differs_between_runs(self):
        first = attendance_sim.finalize_through(4, ts.MONDAY, chunk_size=10)
        second = attendance_sim.finalize_through(4, ts.MONDAY, chunk_size=10)
        self.assertNotEqual(
            first["summary"]["finalize_id"], second["summary"]["finalize_id"]
        )

    # ---- day view --------------------------------------------------------

    def test_day_view_only_lists_courses_scheduled_that_day(self):
        view = attendance_sim.day_schedule(5, ts.WEDNESDAY)
        schedule = self.term["schedule"]
        for course in view["courses"]:
            weekdays = schedule["courses"][course["course_id"]]["weekdays"]
            self.assertIn(ts.WEDNESDAY, weekdays)
            self.assertTrue(course["sessions"])

    def test_day_view_dates_line_up_with_the_selected_point(self):
        view = attendance_sim.day_schedule(6, ts.MONDAY)
        expected = attendance_sim.resolve_point(6, ts.MONDAY, self.term)
        self.assertEqual(view["date"], expected.isoformat())
        for course in view["courses"]:
            for session in course["sessions"]:
                self.assertEqual(session["date"], expected.isoformat())


if __name__ == "__main__":
    unittest.main()
