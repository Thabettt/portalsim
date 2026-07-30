from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import Session, select
from app.db import get_session
from app.models import User
from app.schemas import UserRead
import logging

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/students",
    tags=["Students"]
)

@router.get("/lookup", response_model=UserRead)
def lookup_student(
    student_id: Optional[str] = Query(None, description="Student ID (e.g. STU-2024-0001)"),
    email: Optional[str] = Query(None, description="Student Email"),
    session: Session = Depends(get_session)
):
    """
    Lookup a student profile by student_id or email.
    """
    if not student_id and not email:
        raise HTTPException(status_code=400, detail="Must provide student_id or email")
        
    query = select(User)
    if student_id:
        query = query.where(User.student_id == student_id)
    if email:
        query = query.where(User.email == email)
        
    user = session.exec(query).first()
    
    if not user:
        raise HTTPException(status_code=404, detail="Student not found")
        
    return user
