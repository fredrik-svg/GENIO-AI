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
   docker-compose up --build
   ```

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
├── index.html             # Web interface template
├── main.js                # Frontend JavaScript
├── requirements-web.txt   # Python dependencies
├── Dockerfile             # Container definition
├── docker-compose.yml     # Docker Compose configuration
├── README.md              # This file
└── README_WEB.md          # Web-specific documentation
```

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