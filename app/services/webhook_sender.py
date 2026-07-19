import hmac
import hashlib
import json
import logging
import httpx
import uuid
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from sqlmodel import Session, select, func
from app.db import engine
from app.models import (
    WebhookLog, WebhookSetting, WebhookEventType,
    WebhookDeliveryStatus
)
from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


def generate_signature(payload: str, secret: str) -> str:
    """Generate HMAC-SHA256 signature for webhook payload"""
    return hmac.new(
        secret.encode("utf-8"),
        payload.encode("utf-8"),
        hashlib.sha256
    ).hexdigest()


def create_webhook_log(
    session: Session,
    event_type: WebhookEventType,
    payload: Dict[str, Any],
    target_url: str,
    shared_secret: str,
    student_id: Optional[int] = None,
    course_id: Optional[int] = None,
    payment_id: Optional[int] = None,
    assessment_id: Optional[int] = None,
    internship_id: Optional[int] = None,
    max_retries: int = 3
) -> WebhookLog:
    """Create a webhook log entry"""
    payload_json = json.dumps(payload, default=str)
    event_id = payload.get("event_id") or "unknown"

    webhook_log = WebhookLog(
        event_type=event_type,
        target_url=target_url,
        payload=payload_json,
        status=WebhookDeliveryStatus.PENDING,
        attempt_number=0,
        max_retries=max_retries,
        student_id=student_id,
        course_id=course_id,
        payment_id=payment_id,
        assessment_id=assessment_id,
        internship_id=internship_id
    )
    session.add(webhook_log)
    session.commit()
    session.refresh(webhook_log)
    return webhook_log


def create_webhook_log_sync(
    session: Session,
    event_type: WebhookEventType,
    payload: Any,
    student_id: Optional[int] = None,
    course_id: Optional[int] = None,
    payment_id: Optional[int] = None,
    assessment_id: Optional[int] = None,
    internship_id: Optional[int] = None
) -> WebhookLog:
    """Create webhook log synchronously (gets settings from DB)"""
    webhook_setting = session.exec(
        select(WebhookSetting).where(WebhookSetting.is_active == True)
    ).first()

    if not webhook_setting or not webhook_setting.webhook_target_url:
        logger.warning(f"No active webhook setting found for event {event_type}. Logging only.")
        # Still create log entry but mark as no target
        payload_dict = payload.model_dump() if hasattr(payload, "model_dump") else payload
        if "event_id" not in payload_dict:
            import uuid
            payload_dict["event_id"] = str(uuid.uuid4())

        return create_webhook_log(
            session,
            event_type,
            payload_dict,
            "NO_TARGET",
            "",
            student_id=student_id,
            course_id=course_id,
            payment_id=payment_id,
            assessment_id=assessment_id,
            internship_id=internship_id
        )

    payload_dict = payload.model_dump() if hasattr(payload, "model_dump") else payload
    if "event_id" not in payload_dict:
        import uuid
        payload_dict["event_id"] = str(uuid.uuid4())

    return create_webhook_log(
        session,
        event_type,
        payload_dict,
        webhook_setting.webhook_target_url,
        webhook_setting.shared_secret,
        student_id=student_id,
        course_id=course_id,
        payment_id=payment_id,
        assessment_id=assessment_id,
        internship_id=internship_id
    )


async def deliver_webhook(
    session: Session,
    webhook_log: WebhookLog
) -> bool:
    """Deliver webhook with retry logic"""
    if webhook_log.target_url == "NO_TARGET":
        webhook_log.status = WebhookDeliveryStatus.SENT
        webhook_log.completed_at = datetime.utcnow()
        webhook_log.status_code = 200
        webhook_log.response_body = "Logged locally (no webhook target configured)"
        session.add(webhook_log)
        session.commit()
        logger.info(f"[WEBHOOK LOGGED] type={webhook_log.event_type.value} target=local status=200")
        return True

    webhook_setting = session.exec(
        select(WebhookSetting).where(WebhookSetting.is_active == True)
    ).first()

    if not webhook_setting:
        webhook_log.status = WebhookDeliveryStatus.FAILED
        webhook_log.error_message = "No active webhook configuration"
        webhook_log.completed_at = datetime.utcnow()
        session.add(webhook_log)
        session.commit()
        return False

    payload_json = webhook_log.payload
    signature = generate_signature(payload_json, webhook_setting.shared_secret)

    headers = {
        "Content-Type": "application/json",
        "X-University-Signature": signature,
        "X-University-Event": webhook_log.event_type.value,
        "X-University-Event-ID": json.loads(payload_json).get("event_id", "unknown")
    }

    attempt = webhook_log.attempt_number + 1
    webhook_log.attempt_number = attempt
    webhook_log.status = WebhookDeliveryStatus.RETRYING if attempt > 1 else WebhookDeliveryStatus.PENDING
    session.add(webhook_log)
    session.commit()

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                webhook_log.target_url,
                content=payload_json,
                headers=headers
            )

            webhook_log.status_code = response.status_code
            webhook_log.response_body = response.text[:2000] if response.text else None
            webhook_log.sent_at = datetime.utcnow()

            if 200 <= response.status_code < 300:
                webhook_log.status = WebhookDeliveryStatus.SENT
                webhook_log.completed_at = datetime.utcnow()
                session.add(webhook_log)
                session.commit()
                logger.info(f"[WEBHOOK SENT] type={webhook_log.event_type.value} target={webhook_log.target_url} status={response.status_code} attempt={attempt}")
                return True
            else:
                raise httpx.HTTPStatusError(
                    f"HTTP {response.status_code}",
                    request=None,
                    response=response
                )

    except Exception as e:
        webhook_log.error_message = str(e)[:1000]
        logger.warning(f"[WEBHOOK RETRY] type={webhook_log.event_type.value} target={webhook_log.target_url} status={type(e).__name__} attempt={attempt}")

        if attempt >= webhook_log.max_retries:
            webhook_log.status = WebhookDeliveryStatus.FAILED
            webhook_log.completed_at = datetime.utcnow()
            session.add(webhook_log)
            session.commit()
            logger.error(f"[WEBHOOK FAILED] type={webhook_log.event_type.value} target={webhook_log.target_url} status={type(e).__name__} attempts_exhausted={webhook_log.max_retries}")
        else:
            # Schedule retry
            retry_delays = settings.retry_delays
            if attempt <= len(retry_delays):
                delay = retry_delays[attempt - 1]
            else:
                delay = retry_delays[-1]

            webhook_log.next_retry_at = datetime.utcnow() + timedelta(seconds=delay)
            webhook_log.status = WebhookDeliveryStatus.RETRYING
            session.add(webhook_log)
            session.commit()

        return False


async def process_pending_webhooks(session: Session) -> int:
    """Process pending and retryable webhooks"""
    now = datetime.utcnow()

    pending_logs = session.exec(
        select(WebhookLog)
        .where(
            (WebhookLog.status == WebhookDeliveryStatus.PENDING) |
            (WebhookLog.status == WebhookDeliveryStatus.RETRYING) &
            (WebhookLog.next_retry_at <= now)
        )
        .order_by(WebhookLog.created_at)
        .limit(50)
    ).all()

    processed = 0
    for log in pending_logs:
        await deliver_webhook(session, log)
        processed += 1

    return processed


async def fire_webhook(
    event_type: WebhookEventType,
    payload: Dict[str, Any],
    student_id: Optional[int] = None,
    course_id: Optional[int] = None,
    payment_id: Optional[int] = None,
    assessment_id: Optional[int] = None,
    internship_id: Optional[int] = None
):
    """Fire a webhook asynchronously (fire and forget)"""
    if "event_id" not in payload:
        payload["event_id"] = str(uuid.uuid4())
    if "timestamp" not in payload:
        payload["timestamp"] = datetime.utcnow().isoformat()

    # Get webhook settings
    with Session(engine) as session:
        webhook_setting = session.exec(
            select(WebhookSetting).where(WebhookSetting.is_active == True)
        ).first()

        if not webhook_setting or not webhook_setting.webhook_target_url:
            # Still log locally
            create_webhook_log(
                session,
                event_type,
                payload,
                "NO_TARGET",
                "",
                student_id=student_id,
                course_id=course_id,
                payment_id=payment_id,
                assessment_id=assessment_id,
                internship_id=internship_id
            )
            logger.info(f"[WEBHOOK LOGGED] type={event_type.value} target=local (no webhook configured)")
            return

        # Create log entry
        webhook_log = create_webhook_log(
            session,
            event_type,
            payload,
            webhook_setting.webhook_target_url,
            webhook_setting.shared_secret,
            student_id=student_id,
            course_id=course_id,
            payment_id=payment_id,
            assessment_id=assessment_id,
            internship_id=internship_id
        )

        # Fire asynchronously (don't wait)
        import asyncio
        asyncio.create_task(deliver_webhook(session, webhook_log))


def get_webhook_logs(
    session: Session,
    page: int = 1,
    page_size: int = 50,
    event_type: Optional[WebhookEventType] = None,
    status: Optional[WebhookDeliveryStatus] = None,
    student_id: Optional[int] = None
) -> Dict[str, Any]:
    """Get paginated webhook logs"""
    query = select(WebhookLog)

    if event_type:
        query = query.where(WebhookLog.event_type == event_type)
    if status:
        query = query.where(WebhookLog.status == status)
    if student_id:
        query = query.where(WebhookLog.student_id == student_id)

    query = query.order_by(WebhookLog.created_at.desc())

    total = session.exec(select(func.count()).select_from(query.subquery())).one()
    logs = session.exec(query.offset((page - 1) * page_size).limit(page_size)).all()

    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "pages": (total + page_size - 1) // page_size,
        "logs": [
            {
                "id": log.id,
                "event_type": log.event_type.value,
                "target_url": log.target_url,
                "payload": json.loads(log.payload) if log.payload else {},
                "status": log.status.value,
                "status_code": log.status_code,
                "response_body": log.response_body,
                "error_message": log.error_message,
                "attempt_number": log.attempt_number,
                "max_retries": log.max_retries,
                "next_retry_at": log.next_retry_at.isoformat() if log.next_retry_at else None,
                "created_at": log.created_at.isoformat(),
                "sent_at": log.sent_at.isoformat() if log.sent_at else None,
                "completed_at": log.completed_at.isoformat() if log.completed_at else None,
                "student_id": log.student_id,
                "course_id": log.course_id,
                "payment_id": log.payment_id,
                "assessment_id": log.assessment_id,
                "internship_id": log.internship_id
            }
            for log in logs
        ]
    }