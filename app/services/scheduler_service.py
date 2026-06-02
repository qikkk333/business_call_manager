from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.date import DateTrigger
from datetime import datetime, timedelta
from app.services import whatsapp_service
import pytz

# Use IST timezone — clinic is in Kerala, India
IST = pytz.timezone("Asia/Kolkata")

# Single shared scheduler instance — started once when FastAPI starts
scheduler = BackgroundScheduler(timezone=IST)


def schedule_reminders(
    phone: str,
    patient_name: str,
    treatment: str,
    slot_start: str,  # ISO format: "2026-06-05T10:00:00"
    appointment_id: str
):
    """
    Schedule 3 jobs after a booking is made:
    1. 24 hours before → reminder
    2. 1 hour before   → reminder
    3. 2 hours after   → feedback request

    All times are in IST.
    """
    # Parse the slot start time
    appointment_dt = datetime.fromisoformat(slot_start)

    # Make timezone-aware if it isn't already
    if appointment_dt.tzinfo is None:
        appointment_dt = IST.localize(appointment_dt)

    date_str = appointment_dt.strftime("%d %B %Y")   # e.g. "05 June 2026"
    time_str = appointment_dt.strftime("%I:%M %p")   # e.g. "10:00 AM"

    reminder_24hr = appointment_dt - timedelta(hours=24)
    reminder_1hr  = appointment_dt - timedelta(hours=1)
    feedback_time = appointment_dt + timedelta(hours=2)

    now = datetime.now(IST)

    # Only schedule if the time hasn't already passed
    if reminder_24hr > now:
        scheduler.add_job(
            whatsapp_service.send_24hr_reminder,
            trigger=DateTrigger(run_date=reminder_24hr),
            args=[phone, patient_name, treatment, date_str, time_str],
            id=f"24hr_{appointment_id}",
            replace_existing=True
        )

    if reminder_1hr > now:
        scheduler.add_job(
            whatsapp_service.send_1hr_reminder,
            trigger=DateTrigger(run_date=reminder_1hr),
            args=[phone, patient_name, treatment, time_str],
            id=f"1hr_{appointment_id}",
            replace_existing=True
        )

    if feedback_time > now:
        scheduler.add_job(
            whatsapp_service.send_feedback_request,
            trigger=DateTrigger(run_date=feedback_time),
            args=[phone, patient_name, treatment],
            id=f"feedback_{appointment_id}",
            replace_existing=True
        )


def start():
    """Start the scheduler — called once when FastAPI starts."""
    if not scheduler.running:
        scheduler.start()


def stop():
    """Stop the scheduler — called when FastAPI shuts down."""
    if scheduler.running:
        scheduler.shutdown()
