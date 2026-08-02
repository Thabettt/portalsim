from fastapi import APIRouter, Depends, HTTPException, Header
from sqlmodel import Session, select
from typing import List, Optional
from app.db import get_session
from app.models import User, Course, CourseInstructor
from app.config import get_settings

settings = get_settings()

router = APIRouter(
    prefix="/api/sync",
    tags=["Sync"]
)

def verify_api_key(api_key: Optional[str] = Header(None, alias="X-API-Key")):
    """Verify that the provided API key matches the shared secret."""
    valid_key = settings.shared_secret or "dev-secret-change-in-production"
    if api_key != valid_key:
        raise HTTPException(status_code=401, detail="Invalid API Key")
    return api_key


@router.get("/users")
def sync_users(session: Session = Depends(get_session), api_key: str = Depends(verify_api_key)):
    """Fetch all users to sync with Frappe"""
    users = session.exec(select(User)).all()
    
    result = []
    for u in users:
        result.append({
            "id": u.id,
            "student_id": u.student_id,
            "email": u.email,
            "full_name": u.full_name,
            "role": u.role.value,
            "is_foreigner": u.is_foreigner,
        })
    return {"users": result}


@router.get("/courses")
def sync_courses(session: Session = Depends(get_session), api_key: str = Depends(verify_api_key)):
    """Fetch all courses and their assigned instructors to sync with Frappe"""
    courses = session.exec(select(Course)).all()
    
    result = []
    for c in courses:
        # Fetch instructors for this course
        instructors = session.exec(
            select(CourseInstructor).where(CourseInstructor.course_id == c.id)
        ).all()
        
        instructor_data = []
        for inst in instructors:
            user = session.get(User, inst.instructor_id)
            if user:
                instructor_data.append({
                    "instructor_email": user.email,
                    "instructor_name": user.full_name,
                    "instructor_type": inst.instructor_type
                })
        
        result.append({
            "id": c.id,
            "code": c.code,
            "name": c.name,
            "description": c.description,
            "credits": c.credits,
            "semester": c.semester,
            "is_active": c.is_active,
            "instructors": instructor_data
        })
        
    return {"courses": result}
