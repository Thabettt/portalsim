from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from sqlmodel import Session
from app.db import engine
from app.services.attendance import simulate_day_end_attendance
from app.services.payments import simulate_payment_reminders
from app.services.grades_internships import simulate_deadline_check
from app.config import get_settings
import logging

logger = logging.getLogger(__name__)
settings = get_settings()

scheduler = BackgroundScheduler(timezone=settings.scheduler_timezone)


def run_daily_attendance_simulation():
    """Daily job to simulate end-of-day attendance marking"""
    logger.info("Running daily attendance simulation")
    with Session(engine) as session:
        try:
            results = simulate_day_end_attendance(session)
            logger.info(f"Attendance simulation completed: {results}")
        except Exception as e:
            logger.error(f"Error in daily attendance simulation: {e}")


def run_payment_reminders():
    """Daily job to check and send payment reminders"""
    logger.info("Running payment reminders check")
    with Session(engine) as session:
        try:
            results = simulate_payment_reminders(session)
            logger.info(f"Payment reminders completed: {results}")
        except Exception as e:
            logger.error(f"Error in payment reminders: {e}")


def run_deadline_check():
    """Daily job to check upcoming deadlines"""
    logger.info("Running deadline check")
    with Session(engine) as session:
        try:
            results = simulate_deadline_check(session)
            logger.info(f"Deadline check completed: {results}")
        except Exception as e:
            logger.error(f"Error in deadline check: {e}")


def start_scheduler():
    """Start the background scheduler with all jobs"""
    # Daily at 23:00 - simulate end-of-day attendance
    scheduler.add_job(
        run_daily_attendance_simulation,
        CronTrigger(hour=23, minute=0),
        id="daily_attendance",
        name="Daily Attendance Simulation",
        replace_existing=True
    )

    # Daily at 09:00 - check payment reminders
    scheduler.add_job(
        run_payment_reminders,
        CronTrigger(hour=9, minute=0),
        id="payment_reminders",
        name="Payment Reminders Check",
        replace_existing=True
    )

    # Daily at 10:00 - check deadlines
    scheduler.add_job(
        run_deadline_check,
        CronTrigger(hour=10, minute=0),
        id="deadline_check",
        name="Deadline Check",
        replace_existing=True
    )

    scheduler.start()
    logger.info("Scheduler started with jobs:")
    for job in scheduler.get_jobs():
        logger.info(f"  - {job.name}: {job.next_run_time}")


def stop_scheduler():
    """Stop the scheduler"""
    scheduler.shutdown()
    logger.info("Scheduler stopped")


def run_job_now(job_id: str) -> dict:
    """Manually trigger a scheduled job"""
    job = scheduler.get_job(job_id)
    if not job:
        return {"success": False, "error": f"Job {job_id} not found"}

    try:
        if job_id == "daily_attendance":
            with Session(engine) as session:
                result = simulate_day_end_attendance(session)
        elif job_id == "payment_reminders":
            with Session(engine) as session:
                result = simulate_payment_reminders(session)
        elif job_id == "deadline_check":
            with Session(engine) as session:
                result = simulate_deadline_check(session)
        else:
            return {"success": False, "error": f"Unknown job {job_id}"}

        return {"success": True, "result": result}
    except Exception as e:
        logger.error(f"Error running job {job_id}: {e}")
        return {"success": False, "error": str(e)}


def get_job_status() -> list:
    """Get status of all scheduled jobs"""
    jobs = []
    for job in scheduler.get_jobs():
        jobs.append({
            "id": job.id,
            "name": job.name,
            "next_run_time": job.next_run_time.isoformat() if job.next_run_time else None,
            "trigger": str(job.trigger)
        })
    return jobs