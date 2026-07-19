from datetime import datetime, date, timedelta
from typing import List, Optional
from sqlmodel import Session, select, func
from app.models import (
    User, Payment, PaymentStatus, PaymentType, WebhookEventType,
    WebhookSetting
)
from app.services.webhook_sender import create_webhook_log_sync, fire_webhook
from app.schemas.webhook_payloads import (
    PaymentReminderPayload, PaymentStatusChangePayload, WebhookEventType as SchemaWebhookEventType
)
import logging

logger = logging.getLogger(__name__)


def get_payments_due_soon(session: Session, days_ahead: int = 7) -> List[Payment]:
    """Get pending payments due within the specified number of days"""
    cutoff_date = date.today() + timedelta(days=days_ahead)
    return session.exec(
        select(Payment)
        .where(Payment.status == PaymentStatus.PENDING)
        .where(Payment.due_date <= cutoff_date)
        .where(Payment.due_date >= date.today())
    ).all()


def get_overdue_payments(session: Session) -> List[Payment]:
    """Get all overdue payments"""
    return session.exec(
        select(Payment)
        .where(Payment.status == PaymentStatus.PENDING)
        .where(Payment.due_date < date.today())
    ).all()


def fire_payment_reminder(session: Session, payment: Payment, reminder_type: str):
    """Fire payment reminder webhook for a payment"""
    student = session.get(User, payment.student_id)
    if not student:
        logger.warning(f"Student not found for payment {payment.id}")
        return

    payload = PaymentReminderPayload(
        event_type=SchemaWebhookEventType.PAYMENT_REMINDER,
        student_id=student.student_id,
        student_name=student.full_name,
        amount_due=payment.amount - payment.paid_amount,
        currency="EGP",
        due_date=payment.due_date,
        reminder_type=reminder_type,
        payment_type=payment.payment_type.value,
        invoice_number=payment.invoice_number
    )
    create_webhook_log_sync(
        session,
        WebhookEventType.PAYMENT_REMINDER,
        payload,
        student.id,
        payment_id=payment.id
    )
    logger.info(f"Payment reminder fired: {student.student_id} - {payment.payment_type.value} - {reminder_type}")


def fire_payment_status_change(
    session: Session,
    payment: Payment,
    old_status: PaymentStatus,
    new_status: PaymentStatus
):
    """Fire payment status change webhook"""
    student = session.get(User, payment.student_id)
    if not student:
        return

    payload = PaymentStatusChangePayload(
        event_type=SchemaWebhookEventType.PAYMENT_STATUS_CHANGE,
        student_id=student.student_id,
        student_name=student.full_name,
        student_email=student.email,
        payment_id=payment.id,
        payment_type=payment.payment_type.value,
        previous_status=old_status.value,
        new_status=new_status.value,
        amount_paid=payment.paid_amount,
        total_amount=payment.amount
    )
    create_webhook_log_sync(
        session,
        WebhookEventType.PAYMENT_STATUS_CHANGE,
        payload,
        student.id,
        payment_id=payment.id
    )


def update_payment_status(
    session: Session,
    payment_id: int,
    new_status: PaymentStatus,
    paid_amount: Optional[float] = None
) -> Optional[Payment]:
    """Update payment status and fire webhook if changed"""
    payment = session.get(Payment, payment_id)
    if not payment:
        return None

    old_status = payment.status
    payment.status = new_status
    if paid_amount is not None:
        payment.paid_amount = paid_amount
        if paid_amount >= payment.amount:
            payment.status = PaymentStatus.PAID
            payment.paid_at = datetime.utcnow()
    elif new_status == PaymentStatus.PAID:
        payment.paid_amount = payment.amount
        payment.paid_at = datetime.utcnow()

    payment.updated_at = datetime.utcnow()
    session.add(payment)
    session.commit()
    session.refresh(payment)

    if old_status != new_status:
        fire_payment_status_change(session, payment, old_status, new_status)

    return payment


def simulate_payment_reminders(session: Session, days_ahead: int = 7) -> dict:
    """Simulate sending payment reminders for payments due within days_ahead"""
    payments = get_payments_due_soon(session, days_ahead)
    overdue = get_overdue_payments(session)

    results = {
        "reminders_sent": 0,
        "overdue_count": len(overdue),
        "upcoming_count": len(payments),
        "errors": 0
    }

    # Fire reminders for upcoming payments
    for payment in payments:
        try:
            days_until_due = (payment.due_date - date.today()).days
            if days_until_due <= 0:
                reminder_type = "overdue"
            elif days_until_due <= 1:
                reminder_type = "1_day_before"
            elif days_until_due <= 3:
                reminder_type = "3_days_before"
            elif days_until_due <= 7:
                reminder_type = "7_days_before"
            else:
                reminder_type = "upcoming"

            fire_payment_reminder(session, payment, reminder_type)
            results["reminders_sent"] += 1
        except Exception as e:
            logger.error(f"Error sending payment reminder for payment {payment.id}: {e}")
            results["errors"] += 1

    return results


def get_student_payment_summary(session: Session, student_id: int) -> dict:
    """Get payment summary for a student"""
    payments = session.exec(
        select(Payment).where(Payment.student_id == student_id)
    ).all()

    total_due = sum(p.amount for p in payments)
    total_paid = sum(p.paid_amount for p in payments)
    pending = sum(p.amount - p.paid_amount for p in payments if p.status == PaymentStatus.PENDING)
    overdue = sum(p.amount - p.paid_amount for p in payments if p.status == PaymentStatus.OVERDUE)

    return {
        "total_payments": len(payments),
        "total_amount_due": total_due,
        "total_amount_paid": total_paid,
        "pending_amount": pending,
        "overdue_amount": overdue,
        "payments": [
            {
                "id": p.id,
                "type": p.payment_type.value,
                "amount": p.amount,
                "paid": p.paid_amount,
                "due_date": p.due_date.isoformat(),
                "status": p.status.value,
                "invoice": p.invoice_number
            }
            for p in payments
        ]
    }