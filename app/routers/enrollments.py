from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlmodel import Session, select
from typing import List

from app.db import get_session
from app.models import CourseEnrollment, Course, User, CourseEnrollmentStatus
from app.routers.grades import verify_grades_api_key

router = APIRouter(prefix="/api/enrollments", tags=["enrollments"])

class EnrolledCourseResponse(BaseModel):
    course_id: str
    course_name: str

@router.get("/lookup", response_model=List[EnrolledCourseResponse])
def lookup_enrollments(
    student_id: str,
    session: Session = Depends(get_session),
    api_key: str = Depends(verify_grades_api_key)
):
    student = session.exec(select(User).where(User.student_id == student_id)).first()
    if not student:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Student not found"
        )
    
    enrollments = session.exec(
        select(Course)
        .join(CourseEnrollment, CourseEnrollment.course_id == Course.id)
        .where(CourseEnrollment.student_id == student.id)
        .where(CourseEnrollment.status == CourseEnrollmentStatus.ACTIVE)
    ).all()
    
    return [
        EnrolledCourseResponse(course_id=c.code, course_name=c.name) for c in enrollments
    ]
