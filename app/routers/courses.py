from fastapi import APIRouter, Depends, Header, Query
from sqlmodel import Session, select
from typing import Optional
from app.db import get_session
from app.models import Course, CourseInstructor, User
from app.config import get_settings

settings = get_settings()

router = APIRouter(
    prefix="/api/courses",
    tags=["Courses"]
)

def verify_api_key(api_key: Optional[str] = Header(None, alias="X-API-Key")):
    valid_key = settings.shared_secret or "dev-secret-change-in-production"
    if api_key != valid_key:
        from fastapi import HTTPException
        raise HTTPException(status_code=401, detail="Invalid API Key")
    return api_key


@router.get("/instructors")
def get_course_instructors(
    course_ids: Optional[str] = Query(None, description="Comma-separated portal course IDs"),
    session: Session = Depends(get_session),
    api_key: str = Depends(verify_api_key),
):
    """Return courses with their instructors for Frappe consumption."""
    courses = session.exec(select(Course)).all()

    if course_ids:
        id_list = [int(cid.strip()) for cid in course_ids.split(",") if cid.strip().isdigit()]
        courses = [c for c in courses if c.id in id_list]

    result = []
    for c in courses:
        instructors = session.exec(
            select(CourseInstructor).where(CourseInstructor.course_id == c.id)
        ).all()

        instructor_data = []
        for inst in instructors:
            user = session.get(User, inst.instructor_id)
            if user:
                instructor_data.append({
                    "email": user.email,
                    "name": user.full_name,
                    "type": inst.instructor_type,
                })

        result.append({
            "id": c.id,
            "code": c.code,
            "name": c.name,
            "instructors": instructor_data,
        })

    return {"courses": result}
