# Genio AI (Raspberry Pi 5, svenska)

En offline-kapabel röstagent för Raspberry Pi 5 som använder:

- **Porcupine** (.ppn) för väckningsfras (justerbar känslighet)
- **Faster-Whisper (CTranslate2)** för lokal STT (svenska)
- **Piper TTS** för lokal TTS (svensk röst)
- **MQTT över TLS/SSL (8883)** mot **HiveMQ Cloud** där ett **n8n**-workflow svarar

Efter första nedladdningen av modeller och uppsättning av nycklar fungerar allt **offline** (förutom själva MQTT-flödet som kräver nät).

## Katalog

```
genio-ai/
├─ genio_ai.py
├─ config.example.yaml
├─ requirements.txt
├─ service/genio-ai.service
└─ resources/
   ├─ porcupine/   # lägg din .ppn här
   ├─ whisper/     # lägg CT2-modellen här
   └─ piper/       # lägg Piper ONNX-modellen här
```

## Installation (kort)

```bash
sudo apt update
sudo apt install -y python3-pip python3-dev portaudio19-dev libportaudio2 libportaudiocpp0 alsa-utils ffmpeg libopenblas-dev

cd ~/genio-ai
pip3 install -r requirements.txt
cp config.example.yaml config.yaml

# Miljövariabler
export PORCUPINE_ACCESS_KEY="pvac_*************"
export MQTT_USERNAME="your-hivemq-user"
export MQTT_PASSWORD="your-strong-password"

# Kör
python3 genio_ai.py
```

## n8n

Lyssna på `genioai/request`, läs `text`, svara till `reply_topic` med JSON:
```json
{ "corr_id": "<samma-som-request>", "reply": "Svarstext", "timestamp": "..." }
```

## Licens

MIT (exempelprojekt). Lägg gärna till vald licens i ditt repo.
