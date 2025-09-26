#!/usr/bin/env python3
"""
FastAPI web UI for the Raspberry Pi voice assistant.

Features:
- Simple web UI to send text chat messages (Swedish).
- Upload/record audio from the browser to transcribe via OpenAI Whisper.
- Server-side TTS via espeak-ng; returns generated WAV so the browser can play it.
- Uses the same Retriever (RAG) and OpenAI chat flow as the main app.

Place this file at the project root next to config.yaml and other modules.
"""
import os
import tempfile
import subprocess
import logging
from typing import Optional

import yaml
import openai
from fastapi import FastAPI, Request, UploadFile, File, Form
from fastapi.responses import HTMLResponse, FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

# Reuse existing repo modules
from rag import Retriever  # reuse existing Retriever
from stt_openai import transcribe_file  # reuse existing STT helper

LOG = logging.getLogger("webui")
logging.basicConfig(level=logging.INFO)

app = FastAPI()
templates = Jinja2Templates(directory="templates")

# mount static folder if present
if os.path.isdir("static"):
    app.mount("/static", StaticFiles(directory="static"), name="static")


def load_config(path="config.yaml"):
    if not os.path.exists(path):
        LOG.warning("config.yaml not found at %s. Using minimal defaults.", path)
        return {
            "openai": {"api_key_env": "OPENAI_API_KEY", "chat_model": "gpt-4o-mini"},
            "language": {"speech": "sv"},
            "rag": {"top_k": 5},
            "tts": {"rate": 130},
        }
    with open(path, "r") as f:
        return yaml.safe_load(f)


cfg = load_config()
openai_api_env = cfg["openai"].get("api_key_env", "OPENAI_API_KEY")
openai.api_key = os.getenv(openai_api_env, None)
if not openai.api_key:
    LOG.warning("OPENAI API key not found in environment (%s); API calls will fail.", openai_api_env)

# Initialize retriever for RAG queries
retriever = Retriever(cfg)

SYSTEM_PROMPT = (
    "Du är en hjälpsam assistent som svarar på svenska. "
    "Använd korta, tydliga svar och referera till dokument om de är relevanta."
)


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@app.post("/api/chat")
async def api_chat(message: str = Form(...)):
    """
    Accepts a text message (Swedish), runs RAG retrieval, calls OpenAI Chat and returns assistant text.
    """
    if not openai.api_key:
        return JSONResponse({"error": "OpenAI API key not configured on server"}, status_code=500)

    try:
        docs = retriever.query(message, top_k=cfg["rag"].get("top_k", 5))
        doc_texts = [d["text"] for d in docs] if docs else None

        messages = [{"role": "system", "content": SYSTEM_PROMPT}]
        if doc_texts:
            messages.append({"role": "system", "content": "Relevant documents:\n" + "\n\n".join(doc_texts)})
        messages.append({"role": "user", "content": message})

        model = cfg["openai"].get("chat_model", "gpt-4o-mini")
        LOG.info("Sending chat request to model %s", model)
        resp = openai.ChatCompletion.create(
            model=model,
            messages=messages,
            max_tokens=700,
            temperature=0.2,
        )
        content = resp["choices"][0]["message"]["content"]
        return {"reply": content}
    except Exception as e:
        LOG.exception("Chat failed")
        return JSONResponse({"error": str(e)}, status_code=500)


@app.post("/api/transcribe")
async def api_transcribe(file: UploadFile = File(...)):
    """
    Accepts uploaded audio from the browser and transcribes it via OpenAI Whisper (server-side).
    Returns the transcribed text.
    """
    if not openai.api_key:
        return JSONResponse({"error": "OpenAI API key not configured on server"}, status_code=500)

    suffix = os.path.splitext(file.filename)[1] or ".wav"
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        tmp_path = tmp.name
        content = await file.read()
        tmp.write(content)
    try:
        text = transcribe_file(tmp_path, language=cfg["language"].get("speech", "sv"), cfg=cfg)
        return {"transcript": text}
    except Exception as e:
        LOG.exception("Transcription error")
        return JSONResponse({"error": str(e)}, status_code=500)
    finally:
        try:
            os.remove(tmp_path)
        except Exception:
            pass


@app.post("/api/synthesize")
async def api_synthesize(text: str = Form(...), rate: Optional[int] = Form(None)):
    """
    Synthesize Swedish text to WAV using espeak-ng and return the generated file for playback.
    """
    rate_val = rate or cfg.get("tts", {}).get("rate", 130)
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
        wav_path = tmp.name

    try:
        cmd = [
            "espeak-ng",
            "-v",
            "sv",
            "-s",
            str(rate_val),
            "-w",
            wav_path,
            text,
        ]
        LOG.info("Running TTS command: %s", " ".join(cmd[:4]) + " ...")
        subprocess.run(cmd, check=True)
        return FileResponse(wav_path, media_type="audio/wav", filename="reply.wav")
    except FileNotFoundError:
        LOG.exception("espeak-ng not found on server")
        return JSONResponse({"error": "espeak-ng not installed on server"}, status_code=500)
    except subprocess.CalledProcessError as e:
        LOG.exception("TTS failed")
        return JSONResponse({"error": str(e)}, status_code=500)


@app.get("/api/health")
async def health():
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("webapp:app", host="0.0.0.0", port=8080, reload=False)
