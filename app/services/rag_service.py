from sentence_transformers import SentenceTransformer
from groq import Groq
import numpy as np
import os
from dotenv import load_dotenv

load_dotenv()

groq_client = Groq(api_key=os.getenv("GROQ_API_KEY"))

# Small, fast embedding model — runs locally, no API key needed
embedding_model = SentenceTransformer('all-MiniLM-L6-v2')

DOCS_DIR = "documents"

# doctor_schedule.txt has highest priority — if it says a doctor is unavailable,
# that overrides whatever Supabase says
HIGH_PRIORITY_SOURCES = ["doctor_schedule.txt"]


def _load_and_chunk_documents():
    """
    Read all .txt files from the documents/ folder.
    Split them into small chunks so the embedding model can match them precisely.
    """
    chunks = []

    for filename in os.listdir(DOCS_DIR):
        if not filename.endswith(".txt"):
            continue

        filepath = os.path.join(DOCS_DIR, filename)
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()

        # Split by double newline (paragraphs/sections) first
        paragraphs = [p.strip() for p in content.split("\n\n") if p.strip()]

        for para in paragraphs:
            # If paragraph is too long, split further by single newlines
            if len(para) > 400:
                lines = [l.strip() for l in para.split("\n") if l.strip()]
                for line in lines:
                    chunks.append({"text": line, "source": filename})
            else:
                chunks.append({"text": para, "source": filename})

    return chunks


# Load documents and create embeddings once at startup
# This runs when FastAPI starts — not on every request
print("Loading RAG documents and creating embeddings...")
_chunks = _load_and_chunk_documents()
_texts = [c["text"] for c in _chunks]
_embeddings = embedding_model.encode(_texts, show_progress_bar=False)
print(f"RAG ready — {len(_chunks)} chunks loaded from {DOCS_DIR}/")


def _find_relevant_chunks(question: str, top_k: int = 4) -> list[dict]:
    """
    Embed the question and find the most similar chunks using cosine similarity.
    Returns list of chunk dicts with 'text' and 'source' keys.
    """
    question_embedding = embedding_model.encode([question])

    # Cosine similarity between question and all chunks
    dot_products = np.dot(_embeddings, question_embedding.T).flatten()
    norms = np.linalg.norm(_embeddings, axis=1) * np.linalg.norm(question_embedding) + 1e-8
    similarities = dot_products / norms

    top_indices = np.argsort(similarities)[-top_k:][::-1]
    return [_chunks[i] for i in top_indices]


def check_doctor_availability_from_docs(doctor_name: str, date: str) -> str | None:
    """
    Check doctor_schedule.txt specifically for leave or unavailability.
    Returns a warning string if the doctor is unavailable, None if all clear.

    This has HIGHER priority than Supabase — if the doc says unavailable, trust the doc.
    """
    question = f"Is {doctor_name} available on {date}? Is {doctor_name} on leave?"
    chunks = _find_relevant_chunks(question, top_k=5)

    # Only look at high priority sources (doctor_schedule.txt)
    schedule_chunks = [c for c in chunks if c["source"] in HIGH_PRIORITY_SOURCES]

    if not schedule_chunks:
        return None

    context = "\n".join([c["text"] for c in schedule_chunks])

    # Ask Groq to check specifically for unavailability
    response = groq_client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {
                "role": "system",
                "content": (
                    "You are checking a doctor's schedule document. "
                    "Answer only YES or NO followed by one short sentence. "
                    "YES means the doctor IS available. NO means the doctor is NOT available (on leave or off day)."
                )
            },
            {
                "role": "user",
                "content": f"Schedule document:\n{context}\n\nQuestion: Is {doctor_name} available on {date}?"
            }
        ],
        temperature=0,
        max_tokens=60
    )

    answer = response.choices[0].message.content.strip()

    if answer.upper().startswith("NO"):
        return answer  # Return the reason so we can tell the patient
    return None  # Doctor is available


def get_answer(question: str) -> str:
    """
    Main RAG function — finds relevant chunks and generates a natural answer using Groq.
    Used for faq and pricing intents.
    """
    relevant_chunks = _find_relevant_chunks(question, top_k=4)
    context = "\n\n".join([c["text"] for c in relevant_chunks])

    response = groq_client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {
                "role": "system",
                "content": (
                    "You are Meera, a receptionist at MediVoice Dental Clinic. "
                    "Answer the patient's question using ONLY the information in the context below. "
                    "Speak naturally and conversationally — this is a phone call, keep it under 40 words. "
                    "If the answer is not in the context, say you will check and get back to them."
                )
            },
            {
                "role": "user",
                "content": f"Context:\n{context}\n\nPatient question: {question}"
            }
        ],
        temperature=0.4,
        max_tokens=150
    )

    return response.choices[0].message.content.strip()
