from fastapi import APIRouter, Depends, HTTPException, Header, status
from pydantic import BaseModel
from sqlmodel import Session, select
from typing import Optional
from datetime import datetime

from app.db import get_session
from app.models import Assessment, User, Course, AssessmentType
from app.config import get_settings

router = APIRouter(prefix="/api/grades", tags=["grades"])

def verify_grades_api_key(x_api_key: str = Header(default=None)):
    settings = get_settings()
    if not x_api_key or not settings.grades_lookup_api_key or x_api_key != settings.grades_lookup_api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API Key"
        )
    return x_api_key

class GradeLookupResponse(BaseModel):
    student_id: str
    course_id: str
    assessment_type: str
    score: float
    max_score: float
    published_at: Optional[datetime] = None

@router.get("/lookup", response_model=GradeLookupResponse)
def lookup_grade(
    student_id: str,
    course_id: str,
    assessment_type: str,
    session: Session = Depends(get_session),
    api_key: str = Depends(verify_grades_api_key)
):
    # Validate assessment_type
    try:
        assessment_type_enum = AssessmentType(assessment_type)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid assessment_type. Must be one of: {[e.value for e in AssessmentType]}"
        )
        
    # Step 1: Does the assessment exist at all (regardless of publication)?
    assessment = session.exec(
        select(Assessment)
        .join(User, Assessment.student_id == User.id)
        .join(Course, Assessment.course_id == Course.id)
        .where(User.student_id == student_id)
        .where(Course.code == course_id)
        .where(Assessment.assessment_type == assessment_type_enum)
    ).first()

    if not assessment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No matching grade record found."
        )

    # Step 2: Is it published?
    if not assessment.is_published:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Grade exists but has not been published yet."
        )
        
    # Return 200 OK with data
    published_at_utc = None
    if assessment.published_at:
        from datetime import timezone
        published_at_utc = assessment.published_at.replace(tzinfo=timezone.utc)

    return GradeLookupResponse(
        student_id=student_id,
        course_id=course_id,
        assessment_type=assessment_type,
        score=assessment.score or 0.0,
        max_score=assessment.max_score,
        published_at=published_at_utc
    )
