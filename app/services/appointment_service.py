from supabase import create_client
from datetime import datetime, timedelta
import os
from dotenv import load_dotenv

load_dotenv()

supabase = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_KEY"))

# How long each treatment takes in minutes
TREATMENT_DURATIONS = {
    "cleaning": 30,
    "filling": 45,
    "root canal": 90,
    "extraction": 45,
    "whitening": 60,
    "consultation": 30,
    "braces": 60,
    "xray": 15,
}

CLINIC_START = 9   # 9:00 AM
CLINIC_END = 18    # 6:00 PM


def get_or_create_patient(name: str, phone: str) -> str:
    """
    Check if a patient with this phone number exists.
    If yes, return their ID.
    If no, create them and return the new ID.
    """
    result = supabase.table("patients").select("id").eq("phone", phone).execute()

    if result.data:
        return result.data[0]["id"]

    new_patient = supabase.table("patients").insert({
        "name": name,
        "phone": phone,
    }).execute()

    return new_patient.data[0]["id"]


def get_available_slots(date: str, treatment: str) -> list:
    """
    Given a date and treatment type, return a list of free start times.

    Logic:
    1. Get treatment duration
    2. Generate all possible slots for that day (every 30 min from 9am to 6pm)
    3. Fetch already booked appointments for that day
    4. Remove slots that overlap with existing bookings
    5. Return what's free
    """
    duration = TREATMENT_DURATIONS.get(treatment.lower(), 30)

    # Build all possible slot start times for the day
    possible_slots = []
    current = datetime.strptime(f"{date} {CLINIC_START}:00", "%Y-%m-%d %H:%M")
    end_of_day = datetime.strptime(f"{date} {CLINIC_END}:00", "%Y-%m-%d %H:%M")

    while current + timedelta(minutes=duration) <= end_of_day:
        possible_slots.append(current)
        current += timedelta(minutes=30)

    # Fetch booked appointments for this date
    day_start = f"{date}T00:00:00"
    day_end = f"{date}T23:59:59"

    booked = supabase.table("appointments") \
        .select("slot_start, slot_end") \
        .gte("slot_start", day_start) \
        .lte("slot_start", day_end) \
        .neq("status", "cancelled") \
        .execute()

    booked_ranges = [
        (
            datetime.fromisoformat(b["slot_start"]),
            datetime.fromisoformat(b["slot_end"])
        )
        for b in booked.data
    ]

    # Filter out slots that overlap with any booked range
    free_slots = []
    for slot_start in possible_slots:
        slot_end = slot_start + timedelta(minutes=duration)
        overlap = any(
            slot_start < booked_end and slot_end > booked_start
            for booked_start, booked_end in booked_ranges
        )
        if not overlap:
            free_slots.append(slot_start.strftime("%H:%M"))

    return free_slots


def book_appointment(patient_name: str, phone: str, treatment: str, preferred_date: str, doctor_id: str = None) -> dict:
    """
    Book the first available slot for the given treatment on the preferred date.
    Creates the patient if they don't exist.
    """
    patient_id = get_or_create_patient(patient_name, phone)
    duration = TREATMENT_DURATIONS.get(treatment.lower(), 30)
    free_slots = get_available_slots(preferred_date, treatment)

    if not free_slots:
        return {"success": False, "message": "No available slots for this date. Please try another day."}

    # Pick the first free slot
    slot_start = datetime.strptime(f"{preferred_date} {free_slots[0]}", "%Y-%m-%d %H:%M")
    slot_end = slot_start + timedelta(minutes=duration)

    # If no doctor specified, pick the first available one
    if not doctor_id:
        doctor = supabase.table("doctors").select("id").eq("is_available", True).limit(1).execute()
        if not doctor.data:
            return {"success": False, "message": "No doctors available at the moment."}
        doctor_id = doctor.data[0]["id"]

    appointment = supabase.table("appointments").insert({
        "patient_id": patient_id,
        "doctor_id": doctor_id,
        "treatment": treatment,
        "slot_start": slot_start.isoformat(),
        "slot_end": slot_end.isoformat(),
        "status": "booked",
    }).execute()

    return {
        "success": True,
        "message": f"Appointment booked for {patient_name} on {preferred_date} at {free_slots[0]}",
        "data": appointment.data[0]
    }


def cancel_appointment(appointment_id: str) -> dict:
    """
    Cancel an appointment by setting its status to 'cancelled'.
    We never delete rows — cancellation is a status change for audit trail.
    """
    result = supabase.table("appointments") \
        .update({"status": "cancelled"}) \
        .eq("id", appointment_id) \
        .execute()

    if not result.data:
        return {"success": False, "message": "Appointment not found."}

    return {"success": True, "message": "Appointment successfully cancelled."}
