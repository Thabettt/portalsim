import asyncio
import unittest
from datetime import date
from types import SimpleNamespace
from unittest.mock import patch

import httpx
from sqlmodel import Session, SQLModel, create_engine, select

from app.models import (
    Attendance,
    AttendanceStatus,
    AttendanceWarningLevel,
    Course,
    CourseEnrollment,
    User,
    UserRole,
)
from app.services.n8n_attendance import (
    AttendanceFinalizationError,
    build_attendance_snapshot,
    build_chunk_payload,
    get_finalization_progress,
    resend_failed_chunks,
    split_into_chunks,
    start_attendance_finalization,
)


def fake_settings(**overrides):
    values = {
        "n8n_attendance_webhook_url": "https://n8n.example/webhook/attendance-end-of-day",
        "attendance_chunk_size": 2,
        "attendance_chunk_max_concurrency": 5,
        "attendance_chunk_max_retries": 3,
        "attendance_retry_delays": [0, 0, 0],
        "attendance_chunk_timeout_seconds": 30.0,
    }
    values.update(overrides)
    return SimpleNamespace(**values)


class FakeResponse:
    def __init__(self, status_code=202, payload=None, text=""):
        self.status_code = status_code
        self._payload = payload or {}
        self.text = text

    def json(self):
        return self._payload


class FakeAsyncClient:
    """Records every chunk POST and answers from a scripted behaviour map."""

    posts = []
    behaviour = {}          # chunk_index -> list of FakeResponse or Exception, popped per attempt
    default_response = FakeResponse(202, {"accepted": True})
    max_in_flight = 0
    _in_flight = 0

    def __init__(self, *args, **kwargs):
        pass

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, traceback):
        return False

    @classmethod
    def reset(cls):
        cls.posts = []
        cls.behaviour = {}
        cls.default_response = FakeResponse(202, {"accepted": True})
        cls.max_in_flight = 0
        cls._in_flight = 0

    async def post(self, url, json, headers):
        cls = self.__class__
        cls._in_flight += 1
        cls.max_in_flight = max(cls.max_in_flight, cls._in_flight)
        try:
            cls.posts.append(json)
            # Yield so overlapping requests are actually observable.
            await asyncio.sleep(0)
            scripted = cls.behaviour.get(json["chunk_index"])
            outcome = scripted.pop(0) if scripted else cls.default_response
            if isinstance(outcome, Exception):
                raise outcome
            return outcome
        finally:
            cls._in_flight -= 1


class ChunkHelperTests(unittest.TestCase):
    def test_split_into_chunks_respects_configured_size(self):
        students = [{"student_id": f"S{i}"} for i in range(5)]
        chunks = split_into_chunks(students, 2)
        self.assertEqual([len(c) for c in chunks], [2, 2, 1])

    def test_split_into_chunks_rejects_zero_size(self):
        with self.assertRaises(ValueError):
            split_into_chunks([{"student_id": "S1"}], 0)

    def test_chunk_payload_shape(self):
        payload = build_chunk_payload(
            finalize_id="5f6e9c2a-1b3d-4a7e-9c11-8e2f6a0b7d44",
            finalized_at="2026-08-03T09:00:00Z",
            chunk_index=3,
            chunk_count=50,
            students=[{"student_id": "STU-1"}],
        )
        self.assertEqual(payload["finalize_id"], "5f6e9c2a-1b3d-4a7e-9c11-8e2f6a0b7d44")
        self.assertEqual(payload["chunk_index"], 3)
        self.assertEqual(payload["chunk_count"], 50)
        self.assertEqual(payload["finalized_at"], "2026-08-03T09:00:00Z")
        self.assertEqual(payload["students"], [{"student_id": "STU-1"}])


class N8NAttendanceTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        FakeAsyncClient.reset()
        self.engine = create_engine("sqlite://", connect_args={"check_same_thread": False})
        SQLModel.metadata.create_all(self.engine)
        self.session = Session(self.engine)

        warning_course = Course(code="CS-101", name="Computer Science", credits=4, semester="Test")
        good_course = Course(code="MA-101", name="Mathematics", credits=4, semester="Test")
        self.session.add(warning_course)
        self.session.add(good_course)
        self.session.commit()
        self.session.refresh(warning_course)
        self.session.refresh(good_course)
        self.warning_course_id = warning_course.id

        # 5 students so a chunk size of 2 yields 3 chunks (2 + 2 + 1).
        for index in range(5):
            student = User(
                student_id=f"STU-TEST-{index:04d}",
                email=f"student{index}@example.com",
                full_name=f"Test Student {index}",
                role=UserRole.STUDENT,
                hashed_password="unused",
            )
            self.session.add(student)
            self.session.commit()
            self.session.refresh(student)
            self.session.add(CourseEnrollment(student_id=student.id, course_id=warning_course.id))
            self.session.add(CourseEnrollment(student_id=student.id, course_id=good_course.id))
            self.session.add(Attendance(
                student_id=student.id,
                course_id=warning_course.id,
                date=date(2026, 7, 22),
                status=AttendanceStatus.ABSENT,
                warning_level=AttendanceWarningLevel.SECOND_WARNING,
            ))
        self.session.commit()

    def tearDown(self):
        self.session.close()

    async def _finalize_and_wait(self, settings):
        with (
            patch("app.services.n8n_attendance.get_settings", return_value=settings),
            patch("app.services.n8n_attendance.httpx.AsyncClient", FakeAsyncClient),
        ):
            started = await start_attendance_finalization(self.session)
            await asyncio.wait_for(
                asyncio.shield(asyncio.ensure_future(self._await_job(started["finalize_id"]))),
                timeout=10,
            )
        return started

    async def _await_job(self, finalize_id):
        from app.services.n8n_attendance import _jobs
        task = _jobs[finalize_id].get("task")
        if task:
            await task

    def test_snapshot_contains_good_and_warned_courses(self):
        snapshot = build_attendance_snapshot(self.session)

        self.assertEqual(snapshot["students_count"], 5)
        self.assertEqual(snapshot["course_records_count"], 10)
        levels = {
            course["course_id"]: course["warning_level"]
            for course in snapshot["students"][0]["courses"]
        }
        self.assertEqual(levels, {"CS-101": 2, "MA-101": 0})

    async def test_students_are_split_into_chunks_with_shared_finalize_id(self):
        started = await self._finalize_and_wait(fake_settings())
        progress = get_finalization_progress(started["finalize_id"])

        self.assertEqual(progress["chunk_count"], 3)
        self.assertEqual(progress["chunks_sent"], 3)
        self.assertEqual(progress["chunks_failed"], 0)
        self.assertEqual(progress["status"], "completed")

        posts = sorted(FakeAsyncClient.posts, key=lambda p: p["chunk_index"])
        self.assertEqual([p["chunk_index"] for p in posts], [1, 2, 3])
        self.assertTrue(all(p["chunk_count"] == 3 for p in posts))
        self.assertEqual({p["finalize_id"] for p in posts}, {started["finalize_id"]})
        self.assertEqual([len(p["students"]) for p in posts], [2, 2, 1])
        # Every student made it into exactly one chunk.
        sent_ids = [s["student_id"] for p in posts for s in p["students"]]
        self.assertEqual(len(sent_ids), 5)
        self.assertEqual(len(set(sent_ids)), 5)

    async def test_start_returns_immediately_without_waiting_for_all_chunks(self):
        with (
            patch("app.services.n8n_attendance.get_settings", return_value=fake_settings()),
            patch("app.services.n8n_attendance.httpx.AsyncClient", FakeAsyncClient),
        ):
            started = await start_attendance_finalization(self.session)
            # The sender has not run yet: the response is available before any POST lands.
            self.assertEqual(started["status"], "running")
            self.assertEqual(started["chunks_sent"], 0)
            self.assertEqual(started["chunk_count"], 3)
            self.assertEqual(FakeAsyncClient.posts, [])
            await self._await_job(started["finalize_id"])

    async def test_concurrency_is_capped(self):
        settings = fake_settings(attendance_chunk_size=1, attendance_chunk_max_concurrency=2)
        await self._finalize_and_wait(settings)
        self.assertEqual(len(FakeAsyncClient.posts), 5)
        self.assertLessEqual(FakeAsyncClient.max_in_flight, 2)

    async def test_failing_chunk_is_retried_then_marked_failed(self):
        FakeAsyncClient.behaviour = {
            2: [FakeResponse(500, text="boom")] * 4,  # initial attempt + 3 retries
        }
        started = await self._finalize_and_wait(fake_settings())
        progress = get_finalization_progress(started["finalize_id"])

        self.assertEqual(progress["status"], "partial")
        self.assertEqual(progress["chunks_sent"], 2)
        self.assertEqual(progress["chunks_failed"], 1)
        self.assertEqual(progress["failed_chunks"], [2])

        failed_chunk = next(c for c in progress["chunks"] if c["chunk_index"] == 2)
        self.assertEqual(failed_chunk["attempts"], 4)
        self.assertEqual(failed_chunk["status_code"], 500)

    async def test_chunk_recovers_on_retry_after_transient_error(self):
        FakeAsyncClient.behaviour = {
            1: [httpx.ConnectError("connection reset"), FakeResponse(202, {"accepted": True})],
        }
        started = await self._finalize_and_wait(fake_settings())
        progress = get_finalization_progress(started["finalize_id"])

        self.assertEqual(progress["status"], "completed")
        self.assertEqual(progress["chunks_failed"], 0)
        recovered = next(c for c in progress["chunks"] if c["chunk_index"] == 1)
        self.assertEqual(recovered["attempts"], 2)

    async def test_timeout_is_retried(self):
        FakeAsyncClient.behaviour = {
            3: [httpx.ReadTimeout("too slow")] * 4,
        }
        started = await self._finalize_and_wait(fake_settings())
        progress = get_finalization_progress(started["finalize_id"])

        self.assertEqual(progress["failed_chunks"], [3])
        failed_chunk = next(c for c in progress["chunks"] if c["chunk_index"] == 3)
        self.assertEqual(failed_chunk["attempts"], 4)
        self.assertEqual(failed_chunk["error"], "Request timed out.")

    async def test_resend_failed_only_retries_failed_chunks(self):
        FakeAsyncClient.behaviour = {2: [FakeResponse(503, text="unavailable")] * 4}
        started = await self._finalize_and_wait(fake_settings())
        self.assertEqual(get_finalization_progress(started["finalize_id"])["failed_chunks"], [2])

        FakeAsyncClient.posts = []
        FakeAsyncClient.behaviour = {}
        with (
            patch("app.services.n8n_attendance.get_settings", return_value=fake_settings()),
            patch("app.services.n8n_attendance.httpx.AsyncClient", FakeAsyncClient),
        ):
            await resend_failed_chunks(started["finalize_id"])
            await self._await_job(started["finalize_id"])

        progress = get_finalization_progress(started["finalize_id"])
        self.assertEqual(progress["status"], "completed")
        self.assertEqual(progress["chunks_failed"], 0)
        self.assertEqual([p["chunk_index"] for p in FakeAsyncClient.posts], [2])

    async def test_202_per_chunk_does_not_mutate_attendance(self):
        FakeAsyncClient.behaviour = {1: [FakeResponse(400, text="invalid")] * 4}
        await self._finalize_and_wait(fake_settings())

        attendance_rows = self.session.exec(
            select(Attendance).where(Attendance.course_id == self.warning_course_id)
        ).all()
        self.assertEqual(len(attendance_rows), 5)
        self.assertTrue(all(
            row.warning_level == AttendanceWarningLevel.SECOND_WARNING for row in attendance_rows
        ))

    async def test_missing_webhook_url_raises_before_starting(self):
        from app.services.n8n_attendance import AttendanceFinalizationNotConfigured

        with patch(
            "app.services.n8n_attendance.get_settings",
            return_value=fake_settings(n8n_attendance_webhook_url="  "),
        ):
            with self.assertRaises(AttendanceFinalizationNotConfigured):
                await start_attendance_finalization(self.session)

    async def test_resend_unknown_finalize_id_raises(self):
        with self.assertRaises(AttendanceFinalizationError):
            await resend_failed_chunks("not-a-real-id")


if __name__ == "__main__":
    unittest.main()
