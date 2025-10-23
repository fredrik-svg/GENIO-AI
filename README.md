# Genio AI (Raspberry Pi 5, svenska)

En offline-kapabel röstagent för Raspberry Pi 5 som använder:

- **Porcupine** (.ppn) för väckningsfras (justerbar känslighet)
- **Faster-Whisper (CTranslate2)** för lokal STT (svenska)
- **Piper TTS** för lokal TTS (svensk röst)
- **MQTT över TLS/SSL (8883)** mot **HiveMQ Cloud** där ett **n8n**-workflow svarar

Efter första nedladdningen av modeller och uppsättning av nycklar fungerar allt **offline** (förutom själva MQTT-flödet som förstås kräver nät).

---

## 🚀 Snabbstart (rekommenderat med `setup.sh`)

```bash
# På din Raspberry Pi 5
sudo apt update && sudo apt install -y unzip
unzip genio-ai.zip -d ~/
cd ~/genio-ai
chmod +x setup.sh
./setup.sh
```

Lägg sedan modeller på plats:
```
resources/porcupine/wakeword.ppn             # Porcupine .ppn (svenska)
resources/whisper/<ct2-modellkatalog>/       # Whisper CT2 (t.ex. small/base, int8)
resources/piper/sv-voice.onnx (+ .json)      # Piper svensk röst
```

Sätt miljövariabler och starta:
```bash
source .venv/bin/activate
export PORCUPINE_ACCESS_KEY="pvac_*************"
export MQTT_USERNAME="<hivemq-user>"
export MQTT_PASSWORD="<hivemq-pass>"
python3 genio_ai.py
```

---

## 🧰 Manuell installation (om du inte vill köra `setup.sh`)

Systempaket (audio, bygg, ffmpeg, BLAS):
```bash
sudo apt update
sudo apt install -y python3-pip python3-venv python3-dev   pkg-config build-essential   portaudio19-dev libportaudio2 libportaudiocpp0 alsa-utils   libsndfile1-dev libopenblas-dev   ffmpeg   libavformat-dev libavcodec-dev libavdevice-dev libavutil-dev   libavfilter-dev libswscale-dev libswresample-dev
```

Python-venv och beroenden:
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip setuptools wheel
pip uninstall -y av || true
pip install -r requirements.txt
cp config.example.yaml config.yaml
```

---

## 🔐 MQTT (HiveMQ Cloud) & n8n

- Host: `7dab69000883410aba47967fb078d6d9.s1.eu.hivemq.cloud`
- Port: `8883` (TLS, system-CA räcker normalt)
- Appen **publicerar** på `genioai/request` med fälten:
  ```json
  { "text": "...", "lang": "sv", "corr_id": "...", "reply_topic": "genioai/response/<corr_id>", "timestamp": "..." }
  ```
- n8n **måste svara** till exakt `reply_topic` och **behålla** samma `corr_id`:
  ```json
  { "corr_id": "...", "reply": "svarstext", "timestamp": "..." }
  ```

---

## 🎙️ Ljud & wakeword

- Välj mikrofon genom att sätta `audio.input_device` i `config.yaml`. Lista enheter:
  ```bash
  python3 -c "import sounddevice as sd; print(sd.query_devices())"
  ```
- Justera känslighet för väckningsfras: `wakeword.sensitivity` (0.0–1.0).

---

## 🛠️ Felsökning

### PyAV/FFmpeg “Getting requirements to build wheel …”
Vår app behöver inte PyAV. Använd ren venv och kör `setup.sh` (som installerar nödvändiga -dev-paket ifall du vill ha PyAV ändå). I en ren venv ska `pip install -r requirements.txt` **inte** hämta paketet `av`.

### Ljudproblem (ALSA)
- Öka mikrofonnivå: `alsamixer`
- Kontrollera att rätt input-enhet används och att den inte är mutad.

### Prestanda
- Börja med Whisper **small** (CT2, `int8`).
- Piper är CPU-lätt, men kör gärna på 16 kHz/mono.

---

## 🧩 Katalog

```
genio-ai/
├─ genio_ai.py
├─ setup.sh
├─ README.md
├─ config.example.yaml
├─ requirements.txt
├─ service/genio-ai.service
└─ resources/
   ├─ porcupine/   # lägg din .ppn här
   ├─ whisper/     # lägg CT2-modellen här
   └─ piper/       # lägg Piper ONNX-modellen här
```

---

## ⚙️ Systemd (valfritt)

Redigera `service/genio-ai.service` (användare/paths/env) och kör:
```bash
sudo systemctl daemon-reload
sudo systemctl enable --now genio-ai.service
```

---

## Licens

MIT (exempelprojekt). Anpassa efter behov.
