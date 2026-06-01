from app.services import appointment_service

def dispatch(llm_result: dict, session_id: str, phone: str = "0000000000") -> str:
    """
    Reads the LLM output and decides what action to take.

    If needs_more_info is True  → the LLM is still collecting details from the patient.
                                  Just return its response and keep the conversation going.

    If needs_more_info is False → the LLM has everything it needs.
                                  Take the real action (book, cancel, check slots, etc.)
    """

    intent = llm_result.get("intent")
    needs_more_info = llm_result.get("needs_more_info", True)
    entities = llm_result.get("entities", {})
    llm_response = llm_result.get("response", "")

    # Still collecting info — just speak the LLM's response back to the patient
    if needs_more_info:
        return llm_response

    # LLM has everything — take action based on intent
    if intent == "book_appointment":
        treatment = entities.get("treatment")
        date = entities.get("date")
        patient_name = entities.get("patient_name") or "Patient"

        if not treatment or not date:
            return "I need both the treatment type and date to complete the booking. Could you provide those?"

        result = appointment_service.book_appointment(
            patient_name=patient_name,
            phone=phone,
            treatment=treatment,
            preferred_date=date
        )
        return result["message"]

    elif intent == "cancel_appointment":
        appointment_id = entities.get("appointment_id")

        if not appointment_id:
            return "Could you please share your appointment ID so I can cancel it for you?"

        result = appointment_service.cancel_appointment(appointment_id)
        return result["message"]

    elif intent == "check_slots":
        treatment = entities.get("treatment")
        date = entities.get("date")

        if not treatment or not date:
            return llm_response

        slots = appointment_service.get_available_slots(date, treatment)

        if not slots:
            return f"Sorry, there are no available slots for {treatment} on {date}. Would you like to try another date?"

        # Only speak the first 5 slots — reading 18 slot times on a phone call is painful
        slots_text = ", ".join(slots[:5])
        return f"Available slots for {treatment} on {date} are {slots_text}. Which time works best for you?"

    elif intent == "human_transfer":
        return "Of course! Let me transfer you to one of our staff members right away. Please hold."

    elif intent in ["faq", "pricing"]:
        # RAG pipeline connects here on a later day
        return llm_response

    elif intent == "greeting":
        return llm_response

    else:
        return llm_response
