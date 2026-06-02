from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager
from supabase import create_client
import os
from dotenv import load_dotenv

from app.routers import appointments, voice
from app.services import scheduler_service

load_dotenv()#tis line loads the env var to teh memory

SUPABASE_URL = os.getenv("SUPABASE_URL")#this line loads the env var and assigns to a varible 
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)#

@asynccontextmanager
async def lifespan(app: FastAPI):
    scheduler_service.start()  # start reminder scheduler on startup
    yield
    scheduler_service.stop()   # clean shutdown when server stops

app = FastAPI(title="MediVoice", version="1.0.0", lifespan=lifespan)

app.include_router(appointments.router, prefix="/appointments", tags=["Appointments"])
app.include_router(voice.router, prefix="/voice", tags=["Voice"])

# Serve generated ElevenLabs audio files so Twilio can fetch them via URL
os.makedirs("app/static/audio", exist_ok=True)
app.mount("/audio", StaticFiles(directory="app/static/audio"), name="audio")

@app.get("/")
def health_check():
    return {"status": "MediVoice is running"}


#uvicorn app.main:app --reload   
#>C:\cloudflared\cloudflared.exe tunnel --url http://localhost:8000
