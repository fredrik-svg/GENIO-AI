# Web UI + Docker for Raspberry Pi Voice Assistant

What I added
- A small FastAPI web UI (webapp.py) with:
  - Text chat endpoint (/api/chat) using the same RAG + OpenAI chat flow.
  - Audio upload endpoint (/api/transcribe) to accept browser recordings and transcribe with OpenAI Whisper.
  - TTS endpoint (/api/synthesize) that calls espeak-ng server-side and returns a WAV file for playback.
  - A minimal HTML/JS frontend (templates/index.html + static/main.js) for text chat, recording, and playback.
  - **New:** n8n setup wizard (/install) for step-by-step webhook integration and verification.

- Dockerfile optimized for Raspberry Pi 5 (arm64).
  - Installs espeak-ng, ffmpeg and required system libraries.
  - Installs Python dependencies from requirements-web.txt.
  - Exposes port 8080 and runs the FastAPI app with uvicorn.

- docker-compose.yml to run the container easily.

How to use (on the Pi)
1. Ensure you have a config.yaml in the project root and your OpenAI API key exported:
   export OPENAI_API_KEY="sk-..."

2. Build and run with docker (native build on the Pi):
   docker build -t raspi-voice-web:latest .
   docker run --rm -p 8080:8080 -e OPENAI_API_KEY=$OPENAI_API_KEY -v $(pwd)/data:/app/data raspi-voice-web:latest

   Or using docker-compose:
   OPENAI_API_KEY=sk-... docker-compose up --build

3. Open http://<raspberry-pi-ip>:8080 in a browser on the same network.

### Connect the app to n8n (Swedish walkthrough)

1. Öppna `http://<raspberry-pi-ip>:8080/install` i webbläsaren på din Raspberry Pi eller en dator i samma nätverk.
2. Mata in bas-URL till n8n (t.ex. `http://192.168.1.50:5678`) och kör anslutningstestet – appen kontrollerar `/healthz`.
3. Skriv in webhook-sökvägen (t.ex. `/webhook/genio-ai`) och tryck på “Testa webhook” för att skicka ett testpayload.
4. Valfritt: Fyll i en API-nyckel (`X-N8N-API-KEY`) och verifiera den mot `rest/workflows`.
5. Klicka “Spara konfiguration”. Inställningarna lagras i `n8n_config.yaml` och aktiveras direkt. När användare chattar skickas händelserna till n8n-flödet som JSON (`{"event": "chat", ...}`).
6. Om något steg misslyckas får du ett tydligt felmeddelande i guiden så att du kan felsöka n8n eller dina nätverksinställningar.

Notes & recommendations
- The container requires espeak-ng for server-side TTS. The Dockerfile installs it.
- For best performance and lower cost, consider:
  - Using a smaller chat model or caching answers.
  - Running RAG ingestion ahead of time (python rag.py --ingest docs/).
- If you want full offline STT, swap /api/transcribe to call a local whisper.cpp binary instead of OpenAI Whisper.
- If you plan to expose the UI to the internet, secure the service (reverse proxy, HTTPS, auth).

Troubleshooting
---------------

- **Permission denied when pulling/building images**: If Docker prints `permission denied`
  for `/var/run/docker.sock`, run the command with `sudo` or add your user to the
  `docker` group and start a new shell (`sudo usermod -aG docker $USER && newgrp docker`).
  Also confirm the Docker daemon is running (`sudo systemctl status docker`).
