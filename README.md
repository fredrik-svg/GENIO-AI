# GENIO-AI - Raspberry Pi Voice Assistant

A Swedish voice assistant for Raspberry Pi featuring RAG (Retrieval-Augmented Generation), speech-to-text, text-to-speech, and a modern web interface.

## Features

- **Voice Interaction**: Record audio via web interface or direct microphone input
- **Speech-to-Text**: OpenAI Whisper integration for accurate Swedish transcription
- **Text-to-Speech**: Server-side espeak-ng synthesis with adjustable speech rate
- **RAG Chat**: Retrieval-Augmented Generation using OpenAI GPT models with document context
- **Web Interface**: Modern HTML/JavaScript UI for text chat, voice recording, and audio playback
- **Docker Support**: Optimized containers for easy deployment on Raspberry Pi 5 (arm64)
- **Swedish Language**: Native Swedish language support throughout the system

## Architecture

The system consists of several key components:

- **Web UI** (`webapp.py`): FastAPI-based web server with REST endpoints
- **RAG Module** (`rag.py`): Document retrieval and context management
- **STT Module** (`stt_openai.py`): Speech-to-text via OpenAI Whisper
- **Frontend**: HTML/CSS/JavaScript interface with audio recording capabilities
- **Docker Environment**: Containerized deployment with all dependencies

## Quick Start

### Prerequisites

- Raspberry Pi 5 (recommended) or other arm64/x86_64 system
- Docker and Docker Compose
- OpenAI API key

### Install Docker on Raspberry Pi OS

If you are starting from a clean Raspberry Pi OS installation, follow these steps to install Docker and Docker Compose:

1. **Update the operating system**
   ```bash
   sudo apt update
   sudo apt full-upgrade -y
   sudo reboot
   ```
   Rebooting ensures the kernel and firmware updates are applied before installing Docker.

2. **Install Docker using the official convenience script**
   ```bash
   curl -fsSL https://get.docker.com | sh
   ```
   The script detects the Raspberry Pi architecture and installs the latest supported Docker Engine packages.

3. **Enable non-root Docker usage (optional but recommended)**
   ```bash
   sudo usermod -aG docker $USER
   newgrp docker
   ```
   Adding your user to the `docker` group lets you run Docker commands without `sudo`.

4. **Install Docker Compose plugin**
   ```bash
   sudo apt install -y docker-compose-plugin
   ```
   The plugin provides the `docker compose` command (`docker-compose` remains available through compatibility symlinks).

5. **Verify the installation**
   ```bash
   docker --version
   docker compose version
   ```
   Both commands should print version information without errors.

With Docker available, you can continue with the project-specific steps below.

### Installation

1. **Clone the repository**:
   ```bash
   git clone https://github.com/fredrik-svg/GENIO-AI.git
   cd GENIO-AI
   ```

2. **Set up your OpenAI API key**:
   ```bash
   export OPENAI_API_KEY="sk-your-api-key-here"
   ```

3. **Run with Docker Compose**:
   ```bash
   docker compose up --build
   ```
   > **Note:** If your system only provides the legacy `docker-compose` binary, the
   > command above may print `-bash: docker-compose: command not found`. Install the
   > Docker Compose plugin as shown in the prerequisites section or run
   > `docker-compose up --build` instead.
   >
   > If Docker reports `permission denied` when connecting to `/var/run/docker.sock`,
   > it means your current user is not allowed to talk to the Docker daemon. Run the
   > command with `sudo` or add your user to the `docker` group and log out and back
   > in (`sudo usermod -aG docker $USER && newgrp docker`). On systems that use
   > `systemd`, you may also need to ensure the Docker service is running with
   > `sudo systemctl start docker`.

4. **Access the web interface**:
   Open your browser to `http://localhost:8080` (or your Raspberry Pi's IP address)

### Manual Installation (without Docker)

1. **Install system dependencies** (Ubuntu/Debian):
   ```bash
   sudo apt update
   sudo apt install python3 python3-pip espeak-ng ffmpeg portaudio19-dev libsndfile1
   ```

2. **Install Python dependencies**:
   ```bash
   pip install -r requirements-web.txt
   ```

3. **Run the web server**:
   ```bash
   export OPENAI_API_KEY="sk-your-api-key-here"
   python webapp.py
   ```

## Configuration

The system uses a `config.yaml` file for configuration. If not present, sensible defaults are used:

```yaml
openai:
  api_key_env: "OPENAI_API_KEY"
  chat_model: "gpt-4o-mini"

language:
  speech: "sv"  # Swedish

rag:
  top_k: 5  # Number of retrieved documents

tts:
  rate: 130  # Speech rate for espeak-ng
```

## Usage

### Web Interface

The web interface provides three main functions:

1. **Text Chat**: Type messages to chat with the AI assistant
2. **Voice Recording**: Click "Spela in" to record audio, which gets transcribed and optionally sent to chat
3. **Text-to-Speech**: Click "Säg (TTS)" to synthesize and play back Swedish text

### API Endpoints

The FastAPI server exposes several REST endpoints:

- `GET /` - Web interface
- `POST /api/chat` - Send text message, get AI response
- `POST /api/transcribe` - Upload audio file, get transcription
- `POST /api/synthesize` - Convert text to speech, get WAV file
- `GET /api/health` - Health check endpoint
- `GET /install` - Webbaserad installationsguide för n8n-integrationen
- `GET /api/n8n/config` - Hämta nuvarande n8n-inställningar
- `POST /api/n8n/test-base` - Testa anslutning mot n8n-basen (kontrollerar `/healthz`)
- `POST /api/n8n/test-webhook` - Skicka testpayload till webhooken
- `POST /api/n8n/test-api-key` - Verifiera API-nyckel mot `rest/workflows`
- `POST /api/n8n/save` - Spara konfigurationen till `n8n_config.yaml`

### Example API Usage

**Text Chat**:
```bash
curl -X POST "http://localhost:8080/api/chat" \
     -F "message=Hej, vad kan du hjälpa mig med?"
```

**Speech Synthesis**:
```bash
curl -X POST "http://localhost:8080/api/synthesize" \
     -F "text=Hej, detta är ett test" \
     -F "rate=130" \
     --output response.wav
```

## Development

### Project Structure

```
├── webapp.py              # FastAPI web server
├── rag.py                 # RAG implementation (referenced)
├── stt_openai.py          # Speech-to-text module (referenced)
├── n8n_config.py          # Hjälpmodul som sparar/laddar n8n-inställningar
├── index.html             # Web interface template
├── main.js                # Frontend JavaScript
├── templates/setup.html   # Webbaserad installationsguide för n8n
├── requirements-web.txt   # Python dependencies
├── Dockerfile             # Container definition
├── docker-compose.yml     # Docker Compose configuration
├── README.md              # This file
└── README_WEB.md          # Web-specific documentation
```

### Integrering med n8n

För att koppla GENIO-AI till ett n8n-flöde används HTTP-anrop direkt från Raspberry Pi:n där appen körs. Flödet tar emot data via en webhook och kan valfritt säkras med n8n:s inbyggda API-nyckel. Kommunikationen sker på följande sätt:

1. **Webhook** – När en användare skriver ett meddelande i chatten, och assistenten svarar, skickar appen ett JSON-objekt med både användarens fråga och assistentens svar till den konfigurerade webhook-sökvägen (`event="chat"`).
2. **Test av anslutning** – Appen kan automatiskt kontrollera att n8n är uppe genom att fråga efter `<bas-url>/healthz`.
3. **API-nyckel** – Om du anger en API-nyckel läggs den i headern `X-N8N-API-KEY` vid anrop till `rest/workflows`, vilket gör att du kan verifiera att nyckeln fungerar och att flödet är tillgängligt.

För att förenkla uppsättningen finns en installationsguide i webgränssnittet på `http://<din-pi>:8080/install`. Guiden gör fyra saker:

1. Ber användaren mata in bas-URL (exempelvis `http://192.168.1.50:5678`) och testar anslutningen genom att kalla `/healthz`.
2. Ber om webhook-sökvägen (exempelvis `/webhook/genio-ai`) och skickar ett testpayload för att säkerställa att flödet tar emot data.
3. Valfritt: kontrollerar en API-nyckel mot `rest/workflows` för att försäkra sig om att REST-gränssnittet fungerar.
4. Sparar konfigurationen i `n8n_config.yaml` och aktiverar integrationen direkt. Efter sparning kommer alla kommande chatt-svar att notifiera flödet via webhooken.

Om något test misslyckas visar guiden tydliga felmeddelanden så att du kan justera inställningarna eller felsöka n8n-instansen. När allt är grönt visas statusen “Aktiv integration”.

### Adding Documents for RAG

To add documents for the RAG system to reference:

1. Create a `docs/` directory
2. Add your documents (text files, PDFs, etc.)
3. Run the ingestion process:
   ```bash
   python rag.py --ingest docs/
   ```

### Customizing the Assistant

- **System Prompt**: Modify the `SYSTEM_PROMPT` variable in `webapp.py`
- **Language**: Change the `language.speech` setting in `config.yaml`
- **Model**: Update `openai.chat_model` in `config.yaml` for different GPT models
- **TTS Voice**: Modify espeak-ng parameters in the `/api/synthesize` endpoint

## Docker Deployment

### Building for Raspberry Pi

The included Dockerfile is optimized for Raspberry Pi 5 (arm64):

```bash
docker build -t genio-ai:latest .
docker run --rm -p 8080:8080 \
    -e OPENAI_API_KEY=$OPENAI_API_KEY \
    -v $(pwd)/data:/app/data \
    genio-ai:latest
```

### Production Considerations

- **Security**: Use HTTPS and authentication for internet-facing deployments
- **Performance**: Consider using smaller GPT models or caching for cost optimization
- **Storage**: Mount persistent volumes for document storage and model caches
- **Monitoring**: Set up logging and health checks for production use

## Troubleshooting

### Common Issues

1. **OpenAI API Key**: Ensure your API key is properly set and has sufficient credits
2. **Audio Recording**: Check browser permissions for microphone access
3. **TTS Not Working**: Verify espeak-ng is installed (`espeak-ng --version`)
4. **Port Already in Use**: Change the port in docker-compose.yml or kill existing processes
5. **Docker Socket Permission Denied**: If you see `permission denied` errors when
   Docker tries to access `/var/run/docker.sock`, run the command with `sudo` or
   add your user to the Docker group (`sudo usermod -aG docker $USER && newgrp docker`).
   Make sure the Docker daemon itself is running (`sudo systemctl status docker`).

### Logs

View application logs:
```bash
docker-compose logs -f web
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly on Raspberry Pi if possible
5. Submit a pull request

## License

This project is open source. Please check the repository for license information.

## Acknowledgments

- OpenAI for Whisper and GPT models
- FastAPI for the web framework
- espeak-ng for text-to-speech synthesis
- The Raspberry Pi community

---

For web-specific deployment details, see [README_WEB.md](README_WEB.md).