from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class BookAppointmentRequest(BaseModel):
    patient_name: str
    phone: str
    treatment: str
    preferred_date: str        # format: "YYYY-MM-DD"
    doctor_id: Optional[str] = None


class CancelAppointmentRequest(BaseModel):
    appointment_id: str


class AppointmentResponse(BaseModel):
    success: bool
    message: str
    data: Optional[dict] = None
