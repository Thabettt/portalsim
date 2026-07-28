import unittest
from datetime import date
from types import SimpleNamespace
from unittest.mock import patch

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
    send_attendance_snapshot,
)


class FakeResponse:
    def __init__(self, status_code=202, payload=None, text=""):
        self.status_code = status_code
        self._payload = payload or {}
        self.text = text

    def json(self):
        return self._payload


class FakeAsyncClient:
    response = FakeResponse()
    last_payload = None

    def __init__(self, *args, **kwargs):
        pass

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, traceback):
        return False

    async def post(self, url, json, headers):
        self.__class__.last_payload = json
        return self.__class__.response


class N8NAttendanceTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.engine = create_engine("sqlite://", connect_args={"check_same_thread": False})
        SQLModel.metadata.create_all(self.engine)
        self.session = Session(self.engine)

        student = User(
            student_id="STU-TEST-0001",
            email="student@example.com",
            full_name="Test Student",
            role=UserRole.STUDENT,
            hashed_password="unused",
        )
        warning_course = Course(code="CS-101", name="Computer Science", credits=4, semester="Test")
        good_course = Course(code="MA-101", name="Mathematics", credits=4, semester="Test")
        self.session.add(student)
        self.session.add(warning_course)
        self.session.add(good_course)
        self.session.commit()
        self.session.refresh(student)
        self.session.refresh(warning_course)
        self.session.refresh(good_course)

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

    def test_snapshot_contains_good_and_warned_courses(self):
        snapshot = build_attendance_snapshot(self.session)

        self.assertEqual(snapshot["students_count"], 1)
        self.assertEqual(snapshot["course_records_count"], 2)
        levels = {
            course["course_id"]: course["warning_level"]
            for course in snapshot["students"][0]["courses"]
        }
        self.assertEqual(levels, {"CS-101": 2, "MA-101": 0})

    async def test_successful_delivery_returns_portal_summary(self):
        FakeAsyncClient.response = FakeResponse(202, {"accepted": True, "duplicate": False})
        with (
            patch("app.services.n8n_attendance.get_settings", return_value=SimpleNamespace(
                n8n_attendance_webhook_url="https://n8n.example/webhook/attendance-end-of-day"
            )),
            patch("app.services.n8n_attendance.httpx.AsyncClient", FakeAsyncClient),
        ):
            result = await send_attendance_snapshot(self.session)

        self.assertEqual(result["students_processed"], 1)
        self.assertEqual(result["course_records_sent"], 2)
        self.assertIn("warning_level_labels", FakeAsyncClient.last_payload)

    async def test_rejected_delivery_raises_without_mutating_attendance(self):
        FakeAsyncClient.response = FakeResponse(400, {"accepted": False}, "invalid")
        with (
            patch("app.services.n8n_attendance.get_settings", return_value=SimpleNamespace(
                n8n_attendance_webhook_url="https://n8n.example/webhook/attendance-end-of-day"
            )),
            patch("app.services.n8n_attendance.httpx.AsyncClient", FakeAsyncClient),
        ):
            with self.assertRaises(AttendanceFinalizationError):
                await send_attendance_snapshot(self.session)

        attendance = self.session.exec(select(Attendance)).one()
        self.assertEqual(attendance.warning_level, AttendanceWarningLevel.SECOND_WARNING)


if __name__ == "__main__":
    unittest.main()
