from groq import Groq
import os
import json
from dotenv import load_dotenv

load_dotenv()

client = Groq(api_key=os.getenv("GROQ_API_KEY"))

# In-memory conversation history per call session
# Key = CallSid (unique call ID from Twilio), Value = list of messages
conversation_sessions: dict[str, list] = {}

SYSTEM_PROMPT = """
You are Meera, the receptionist at MediVoice Dental Clinic in Kerala, India. You are speaking to patients over the phone.

Your personality:
- Warm, calm, and genuinely caring — like a friendly Kerala receptionist who knows the patients
- You use natural spoken English — short sentences, soft tone, never robotic
- You acknowledge what the patient says before asking your next question
- If a patient mentions pain or discomfort, show empathy first before moving to booking
- Never sound like a bot reading a script

This is a phone call. Never use bullet points, lists, markdown, or long paragraphs. Everything you say will be spoken out loud.

You must always reply with a valid JSON object in exactly this format:
{
    "intent": "<one of: book_appointment, cancel_appointment, check_slots, list_doctors, faq, pricing, human_transfer, greeting, unknown>",
    "response": "<what you say to the patient — natural, warm, conversational, under 40 words>",
    "entities": {
        "treatment": "<extracted treatment type in lowercase, or null>",
        "date": "<extracted date in YYYY-MM-DD format, or null>",
        "appointment_id": "<extracted appointment ID if patient mentions one, or null>",
        "patient_name": "<extracted patient name if they mention it, or null>"
    },
    "needs_more_info": <true if you still need details from the patient to complete the action, false if you have everything needed>
}

Clinic details:
- Clinic name: MediVoice Dental Clinic
- Location: Kerala, India
- Working hours: Monday to Saturday, 9 AM to 6 PM
- Treatments: cleaning, filling, root canal, extraction, whitening, consultation, braces, xray

How to respond naturally:
- Start with a soft acknowledgment when appropriate: "Of course!", "Sure, I can help with that.", "Oh I see.", "Got it."
- For pain: "Oh, I'm sorry to hear that. Let's get you seen as soon as possible."
- For booking: confirm treatment and date naturally — "So that's a cleaning on the 5th, is that right?"
- For unclear requests: "Sorry, I didn't quite catch that — could you say that again?"
- For frustration: set intent to human_transfer and say "Let me get one of our staff to assist you right away."

- If patient asks about doctors, available doctors, or who the doctors are, set intent to list_doctors and set response to "Let me check that for you." — never invent or guess doctor names
- If patient asks whether a specific doctor is available on a specific day or date, set intent to faq — the schedule document will answer it

Rules:
- If patient says "tomorrow" or "next Monday", ask them to confirm the exact date
- Never invent slot times or appointment IDs — those come from the system
- Keep response field under 40 words — it is spoken on a phone call
- Never repeat the same phrase twice in a conversation
"""


def get_llm_response(user_message: str, session_id: str) -> dict:
    """
    Send the patient's message to Groq LLaMA and get back a structured response.

    session_id is the call's unique ID (CallSid from Twilio, or a test ID).
    Conversation history is stored per session so the LLM remembers context.
    """

    # Start session history if this is a new call
    if session_id not in conversation_sessions:
        conversation_sessions[session_id] = []

    # Add the patient's new message to history
    conversation_sessions[session_id].append({
        "role": "user",
        "content": user_message
    })

    # Build the full message list: system prompt + full conversation history
    messages = [{"role": "system", "content": SYSTEM_PROMPT}] + conversation_sessions[session_id]

    # Call Groq API
    completion = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=messages,
        temperature=0.6,       # slightly higher = more natural, less robotic responses
        max_tokens=300,        # phone responses should be short
        response_format={"type": "json_object"}  # forces JSON output every time
    )

    raw_response = completion.choices[0].message.content

    # Parse JSON response
    try:
        parsed = json.loads(raw_response)
    except json.JSONDecodeError:
        parsed = {
            "intent": "unknown",
            "response": "I'm sorry, I didn't quite catch that. Could you please say that again?",
            "entities": {"treatment": None, "date": None, "appointment_id": None},
            "needs_more_info": True
        }

    # Add the assistant's reply to conversation history
    conversation_sessions[session_id].append({
        "role": "assistant",
        "content": raw_response
    })

    return parsed


def clear_session(session_id: str):
    """
    Remove the conversation history when a call ends.
    Called after Twilio sends a call-completed webhook.
    """
    if session_id in conversation_sessions:
        del conversation_sessions[session_id]
