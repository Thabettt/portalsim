from datetime import datetime, date
from fastapi import APIRouter, Depends, HTTPException, Header, status, Response
from pydantic import BaseModel, Field
from sqlmodel import Session, select
from app.db import get_session
from app.models import Payment, User, PaymentStatus, PaymentType
from app.config import get_settings
from sqlalchemy.exc import IntegrityError

router = APIRouter(prefix="/api/webhooks/charges", tags=["webhooks"])

def verify_api_key(x_api_key: str = Header(default=None)):
    settings = get_settings()
    if not x_api_key or not settings.exam_remark_webhook_api_key or x_api_key != settings.exam_remark_webhook_api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API Key"
        )
    return x_api_key


class ChargeRequest(BaseModel):
    student_id: str
    external_reference_id: str
    amount: float = Field(..., gt=0)
    currency: str
    reason: str
    source: str = "exam_remark"


@router.post("", status_code=status.HTTP_201_CREATED)
def create_charge(
    request: ChargeRequest,
    response: Response,
    session: Session = Depends(get_session),
    api_key: str = Depends(verify_api_key)
):
    # Idempotency check: query for an existing row
    existing_payment = session.exec(
        select(Payment).where(Payment.external_reference_id == request.external_reference_id)
    ).first()

    if existing_payment:
        # Return 200 OK if duplicate
        response.status_code = status.HTTP_200_OK
        return existing_payment

    # Validate student exists
    student = session.exec(
        select(User).where(User.student_id == request.student_id)
    ).first()

    if not student:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Student not found"
        )

    # Create the payment record
    new_payment = Payment(
        student_id=student.id,
        payment_type=PaymentType.OTHER,
        amount=request.amount,
        due_date=date.today(),
        status=PaymentStatus.PENDING,
        description=request.reason,
        external_reference_id=request.external_reference_id,
        source=request.source
    )
    session.add(new_payment)
    
    try:
        session.commit()
        session.refresh(new_payment)
        return new_payment
    except IntegrityError:
        session.rollback()
        # Handle race condition: check again if it was created
        existing_payment = session.exec(
            select(Payment).where(Payment.external_reference_id == request.external_reference_id)
        ).first()
        if existing_payment:
            response.status_code = status.HTTP_200_OK
            return existing_payment
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create charge due to database integrity error"
            )


@router.get("/{external_reference_id}")
def get_charge(
    external_reference_id: str,
    session: Session = Depends(get_session),
    api_key: str = Depends(verify_api_key)
):
    payment = session.exec(
        select(Payment).where(Payment.external_reference_id == external_reference_id)
    ).first()

    if not payment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Charge not found"
        )

    return payment
