from supabase import create_client
import os
from dotenv import load_dotenv

load_dotenv()

supabase = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_KEY"))


def get_patient_by_phone(phone: str) -> dict | None:
    """
    Look up a patient by phone number.
    Twilio sends numbers in E.164 format e.g. +919876543210
    We normalize it to the last 10 digits to match what's stored in Supabase.
    """
    normalized = phone.replace("+", "").replace("-", "").replace(" ", "")
    if normalized.startswith("91") and len(normalized) == 12:
        normalized = normalized[2:]

    result = supabase.table("patients").select("*").eq("phone", normalized).execute()

    if result.data:
        return result.data[0]
    return None
