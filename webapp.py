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
import asyncio
import os
import tempfile
import subprocess
import logging
from typing import Optional
from urllib.parse import urljoin

import yaml
import openai
import httpx
from fastapi import FastAPI, Request, UploadFile, File, Form
from fastapi.responses import HTMLResponse, FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

# Reuse existing repo modules
from rag import Retriever  # reuse existing Retriever
from stt_openai import transcribe_file  # reuse existing STT helper
from n8n_config import load_n8n_config, save_n8n_config

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

N8N_TIMEOUT = 6.0
n8n_config = load_n8n_config()


def _normalize_base_url(base_url: str) -> str:
    base_url = (base_url or "").strip()
    if not base_url:
        raise ValueError("Bas-URL saknas")
    if not base_url.startswith("http://") and not base_url.startswith("https://"):
        base_url = "http://" + base_url
    return base_url.rstrip("/")


def _n8n_enabled() -> bool:
    return bool(n8n_config.get("base_url") and n8n_config.get("webhook_path"))


async def _post_to_n8n(event: str, payload: dict) -> None:
    if not _n8n_enabled():
        return

    base_url = _normalize_base_url(n8n_config["base_url"])
    webhook_path = (n8n_config["webhook_path"] or "").lstrip("/")
    webhook_url = urljoin(base_url + "/", webhook_path)

    headers = {"Content-Type": "application/json"}
    if n8n_config.get("api_key"):
        headers["X-N8N-API-KEY"] = n8n_config["api_key"].strip()

    data = {"event": event, "payload": payload}
    try:
        async with httpx.AsyncClient(timeout=N8N_TIMEOUT) as client:
            resp = await client.post(webhook_url, json=data, headers=headers)
            resp.raise_for_status()
        LOG.info("n8n notifierade via %s", webhook_url)
    except Exception:
        LOG.exception("Kunde inte skicka händelse till n8n")

SYSTEM_PROMPT = (
    "Du är en hjälpsam assistent som svarar på svenska. "
    "Använd korta, tydliga svar och referera till dokument om de är relevanta."
)


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@app.get("/install", response_class=HTMLResponse)
async def install(request: Request):
    return templates.TemplateResponse(
        "setup.html",
        {"request": request, "n8n_config": n8n_config, "n8n_enabled": _n8n_enabled()},
    )


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
        if _n8n_enabled():
            asyncio.create_task(
                _post_to_n8n(
                    "chat", {"message": message, "assistant_reply": content}
                )
            )
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


@app.get("/api/n8n/config")
async def get_n8n_config():
    return {"config": n8n_config, "enabled": _n8n_enabled()}


@app.post("/api/n8n/test-base")
async def test_n8n_base(base_url: str = Form(...)):
    try:
        normalized = _normalize_base_url(base_url)
    except ValueError as exc:
        return JSONResponse({"success": False, "detail": str(exc)}, status_code=400)

    health_url = urljoin(normalized + "/", "healthz")
    try:
        async with httpx.AsyncClient(timeout=N8N_TIMEOUT) as client:
            resp = await client.get(health_url)
        if resp.status_code == 200:
            return {"success": True, "detail": f"Anslutning OK mot {health_url}"}
        return JSONResponse(
            {
                "success": False,
                "detail": f"Fick status {resp.status_code} från {health_url}",
            },
            status_code=502,
        )
    except httpx.RequestError as exc:
        return JSONResponse(
            {
                "success": False,
                "detail": f"Kunde inte nå {health_url}: {exc}",
            },
            status_code=502,
        )


@app.post("/api/n8n/test-webhook")
async def test_n8n_webhook(base_url: str = Form(...), webhook_path: str = Form(...)):
    try:
        normalized = _normalize_base_url(base_url)
    except ValueError as exc:
        return JSONResponse({"success": False, "detail": str(exc)}, status_code=400)

    path = (webhook_path or "").lstrip("/")
    if not path:
        return JSONResponse({"success": False, "detail": "Webhook-sökväg saknas"}, status_code=400)

    webhook_url = urljoin(normalized + "/", path)
    headers = {"Content-Type": "application/json"}
    try:
        async with httpx.AsyncClient(timeout=N8N_TIMEOUT) as client:
            resp = await client.post(webhook_url, json={"event": "test", "ping": "genio-ai"})
        if resp.status_code in {200, 201, 202, 204}:
            return {"success": True, "detail": f"Webhook svarade med {resp.status_code}"}
        return JSONResponse(
            {
                "success": False,
                "detail": f"Webhook svarade med status {resp.status_code}",
            },
            status_code=502,
        )
    except httpx.RequestError as exc:
        return JSONResponse(
            {
                "success": False,
                "detail": f"Kunde inte nå webhook {webhook_url}: {exc}",
            },
            status_code=502,
        )


@app.post("/api/n8n/test-api-key")
async def test_n8n_api_key(base_url: str = Form(...), api_key: str = Form("")):
    try:
        normalized = _normalize_base_url(base_url)
    except ValueError as exc:
        return JSONResponse({"success": False, "detail": str(exc)}, status_code=400)

    if not api_key.strip():
        return JSONResponse({"success": False, "detail": "API-nyckel saknas"}, status_code=400)

    rest_url = urljoin(normalized + "/", "rest/workflows")
    headers = {"X-N8N-API-KEY": api_key.strip()}
    try:
        async with httpx.AsyncClient(timeout=N8N_TIMEOUT) as client:
            resp = await client.get(rest_url, headers=headers)
        if resp.status_code == 200:
            return {"success": True, "detail": "API-nyckeln fungerar"}
        return JSONResponse(
            {
                "success": False,
                "detail": f"Status {resp.status_code} från {rest_url}",
            },
            status_code=502,
        )
    except httpx.RequestError as exc:
        return JSONResponse(
            {
                "success": False,
                "detail": f"Kunde inte kontakta {rest_url}: {exc}",
            },
            status_code=502,
        )


@app.post("/api/n8n/save")
async def save_n8n_settings(
    base_url: str = Form(""), webhook_path: str = Form(""), api_key: str = Form("")
):
    try:
        normalized = _normalize_base_url(base_url)
    except ValueError as exc:
        return JSONResponse({"success": False, "detail": str(exc)}, status_code=400)

    config = {
        "base_url": normalized,
        "webhook_path": (webhook_path or "").strip(),
        "api_key": (api_key or "").strip(),
    }
    save_n8n_config(config)
    n8n_config.update(config)
    return {"success": True, "detail": "Konfiguration sparad", "enabled": _n8n_enabled()}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("webapp:app", host="0.0.0.0", port=8080, reload=False)
