from fastapi import APIRouter, Form, Response
from twilio.twiml.voice_response import VoiceResponse, Gather
from app.services import patient_service, llm_service, action_dispatcher, tts_service
from pydantic import BaseModel
import os

router = APIRouter()

# Base URL of this server — Twilio needs a public URL to fetch the audio files
# Update this in .env whenever your Cloudflare tunnel URL changes
BASE_URL = os.getenv("BASE_URL", "http://localhost:8000")


def make_gather(action: str = "/voice/respond", timeout: int = 10) -> Gather:
    """Helper to create a Gather with consistent speech settings."""
    return Gather(
        input="speech",
        action=action,
        method="POST",
        timeout=timeout,
        language="en-IN",
        speech_timeout="auto"
    )


def play_text(gather_or_response, text: str):
    """
    Generate audio with ElevenLabs and attach it to a Gather or VoiceResponse.
    Twilio fetches the audio file from our /audio/ static endpoint and plays it.
    """
    filename = tts_service.text_to_speech(text)
    audio_url = f"{BASE_URL}/audio/{filename}"
    gather_or_response.play(audio_url)


class TestMessageRequest(BaseModel):
    message: str
    session_id: str = "test-session"
    phone: str = "9876543210"


@router.post("/test-llm")
def test_llm(request: TestMessageRequest):
    """
    Test the full brain without needing a real phone call.
    Sends message through LLM then dispatcher and returns both raw LLM result and the final action taken.
    """
    llm_result = llm_service.get_llm_response(request.message, request.session_id)
    final_response = action_dispatcher.dispatch(llm_result, request.session_id, request.phone)
    return {
        "llm_result": llm_result,
        "action_taken": final_response
    }


@router.post("/incoming")
async def incoming_call(
    From: str = Form(...),
    CallSid: str = Form(default="")
):
    """
    Twilio hits this endpoint the moment a patient calls.
    We greet them and immediately listen for what they need.
    """
    response = VoiceResponse()
    gather = make_gather()
    play_text(gather, "Hello, MediVoice here.")
    response.append(gather)

    # If patient says nothing, loop back
    response.redirect("/voice/incoming", method="POST")

    return Response(content=str(response), media_type="application/xml")


@router.post("/respond")
async def respond_to_patient(
    SpeechResult: str = Form(default=""),
    From: str = Form(default=""),
    CallSid: str = Form(default="")
):
    """
    Twilio sends the patient's transcribed speech here after Gather captures it.
    We run it through the LLM → dispatcher → ElevenLabs TTS → speak back to patient.
    """
    response = VoiceResponse()

    if not SpeechResult:
        gather = make_gather()
        play_text(gather, "I didn't catch that. Could you please say that again?")
        response.append(gather)
        return Response(content=str(response), media_type="application/xml")

    # Run through LLM and dispatcher
    llm_result = llm_service.get_llm_response(SpeechResult, CallSid)
    final_response = action_dispatcher.dispatch(llm_result, CallSid, From)

    # Speak the LLM response and wait for patient's next input
    gather = make_gather()
    play_text(gather, final_response)
    response.append(gather)

    # Fallback — if patient goes silent, ask once more before ending
    fallback_gather = make_gather(timeout=8)
    play_text(fallback_gather, "Is there anything else I can help you with?")
    response.append(fallback_gather)

    # Only reaches here if patient stays silent through both gathers
    play_text(response, "Thank you for calling MediVoice. Have a great day. Goodbye!")

    return Response(content=str(response), media_type="application/xml")
