from elevenlabs import ElevenLabs
import os
import uuid
from dotenv import load_dotenv

load_dotenv()

client = ElevenLabs(api_key=os.getenv("ELEVENLABS_API_KEY"))

# Voice ID for Indian English — configurable via .env
# Default: "Meera" — natural Indian English female voice
VOICE_ID = os.getenv("ELEVENLABS_VOICE_ID", "nPczCjzI2devNBz1zQrb")

AUDIO_DIR = "app/static/audio"


def text_to_speech(text: str) -> str:
    """
    Convert text to speech using ElevenLabs.
    Saves the audio as an mp3 file and returns the filename.

    We use eleven_turbo_v2 — ElevenLabs' fastest model.
    Speed matters here because this is a live phone call.
    """
    os.makedirs(AUDIO_DIR, exist_ok=True)

    audio = client.text_to_speech.convert(
        voice_id=VOICE_ID,
        text=text,
        model_id="eleven_turbo_v2",
        output_format="mp3_22050_32"  # low bitrate = smaller file = faster to serve
    )

    filename = f"{uuid.uuid4()}.mp3"
    filepath = os.path.join(AUDIO_DIR, filename)

    with open(filepath, "wb") as f:
        for chunk in audio:
            f.write(chunk)

    return filename


def delete_audio(filename: str):
    """
    Delete the audio file after Twilio has played it.
    Keeps the disk clean — we don't need these files after the call.
    """
    filepath = os.path.join(AUDIO_DIR, filename)
    if os.path.exists(filepath):
        os.remove(filepath)
