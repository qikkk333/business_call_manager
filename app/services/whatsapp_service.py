from twilio.rest import Client
import os
from dotenv import load_dotenv

load_dotenv()

client = Client(os.getenv("TWILIO_ACCOUNT_SID"), os.getenv("TWILIO_AUTH_TOKEN"))

WHATSAPP_FROM = "whatsapp:+14155238886"  # Twilio sandbox number


def _format_whatsapp_number(phone: str) -> str:
    """
    Convert a phone number to WhatsApp format.
    Twilio requires: whatsapp:+91XXXXXXXXXX
    """
    # Strip everything except digits
    digits = "".join(filter(str.isdigit, phone))

    # Add India country code if missing
    if len(digits) == 10:
        digits = "91" + digits

    return f"whatsapp:+{digits}"


def send_confirmation(phone: str, patient_name: str, treatment: str, date: str, time: str, appointment_id: str):
    """
    Send a booking confirmation WhatsApp message immediately after booking.
    """
    to = _format_whatsapp_number(phone)
    message = (
        f"✅ *Appointment Confirmed!*\n\n"
        f"Hello {patient_name},\n\n"
        f"Your appointment has been booked at MediVoice Dental Clinic.\n\n"
        f"📋 *Details:*\n"
        f"• Treatment: {treatment.title()}\n"
        f"• Date: {date}\n"
        f"• Time: {time}\n"
        f"• Appointment ID: {appointment_id}\n\n"
        f"Please save your Appointment ID for cancellations.\n\n"
        f"_MediVoice Dental Clinic, Kerala_"
    )
    client.messages.create(body=message, from_=WHATSAPP_FROM, to=to)


def send_24hr_reminder(phone: str, patient_name: str, treatment: str, date: str, time: str):
    """
    Send a reminder 24 hours before the appointment.
    """
    to = _format_whatsapp_number(phone)
    message = (
        f"⏰ *Appointment Reminder*\n\n"
        f"Hello {patient_name},\n\n"
        f"This is a reminder that you have a *{treatment.title()}* appointment *tomorrow* at *{time}*.\n\n"
        f"📍 MediVoice Dental Clinic, Kerala\n\n"
        f"To cancel or reschedule, please call us.\n\n"
        f"_See you tomorrow!_ 😊"
    )
    client.messages.create(body=message, from_=WHATSAPP_FROM, to=to)


def send_1hr_reminder(phone: str, patient_name: str, treatment: str, time: str):
    """
    Send a reminder 1 hour before the appointment.
    """
    to = _format_whatsapp_number(phone)
    message = (
        f"🦷 *Your appointment is in 1 hour!*\n\n"
        f"Hello {patient_name},\n\n"
        f"Just a quick reminder — your *{treatment.title()}* appointment is at *{time}* today.\n\n"
        f"📍 MediVoice Dental Clinic, Kerala\n\n"
        f"We look forward to seeing you!"
    )
    client.messages.create(body=message, from_=WHATSAPP_FROM, to=to)


def send_feedback_request(phone: str, patient_name: str, treatment: str):
    """
    Send a post-visit feedback request (sent after the appointment time has passed).
    """
    to = _format_whatsapp_number(phone)
    message = (
        f"💬 *How was your visit?*\n\n"
        f"Hello {patient_name},\n\n"
        f"We hope your *{treatment.title()}* appointment went well!\n\n"
        f"We'd love to hear your feedback. Reply to this message with your thoughts — "
        f"it helps us serve you better.\n\n"
        f"Thank you for choosing MediVoice Dental Clinic! 🙏\n\n"
        f"_MediVoice Dental Clinic, Kerala_"
    )
    client.messages.create(body=message, from_=WHATSAPP_FROM, to=to)
