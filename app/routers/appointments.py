from fastapi import APIRouter, HTTPException
from app.models.appointment import BookAppointmentRequest, CancelAppointmentRequest, AppointmentResponse
from app.services import appointment_service

router = APIRouter()


@router.get("/slots")
def get_available_slots(date: str, treatment: str):
    slots = appointment_service.get_available_slots(date, treatment)
    return {"date": date, "treatment": treatment, "available_slots": slots}


@router.post("/book", response_model=AppointmentResponse)
def book_appointment(request: BookAppointmentRequest):
    result = appointment_service.book_appointment(
        patient_name=request.patient_name,
        phone=request.phone,
        treatment=request.treatment,
        preferred_date=request.preferred_date,
        doctor_id=request.doctor_id
    )
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["message"])
    return AppointmentResponse(success=True, message=result["message"], data=result.get("data"))


@router.delete("/cancel", response_model=AppointmentResponse)
def cancel_appointment(request: CancelAppointmentRequest):
    result = appointment_service.cancel_appointment(request.appointment_id)
    if not result["success"]:
        raise HTTPException(status_code=404, detail=result["message"])
    return AppointmentResponse(success=True, message=result["message"])
