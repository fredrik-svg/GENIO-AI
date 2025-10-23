## 🚀 Snabbstart (med flaggor)

```bash
# På din Raspberry Pi 5
sudo apt update && sudo apt install -y unzip
unzip genio-ai.zip -d ~/
cd ~/genio-ai
chmod +x setup.sh

# Rekommenderat: skapa helt ren miljö
./setup.sh --fresh

# Alternativt välj Python (om 3.12 finns installerad)
./setup.sh --fresh --python 3.12
```

# Genio AI (Raspberry Pi 5, svenska)

En offline-kapabel röstagent för Raspberry Pi 5 som använder:

- **Porcupine** (.ppn) för väckningsfras (justerbar känslighet)
- **Faster-Whisper (CTranslate2)** för lokal STT (svenska)
- **Piper TTS** för lokal TTS (svensk röst)
- **MQTT över TLS/SSL (8883)** mot **HiveMQ Cloud** där ett **n8n**-workflow svarar

Efter första nedladdningen av modeller och uppsättning av nycklar fungerar allt **offline** (förutom själva MQTT-flödet som kräver nät).

---

## Snabbstart (script)

```bash
chmod +x setup.sh
./setup.sh --install-systemd
# eller utan systemd:
# ./setup.sh
```

**Flaggor**
- `--venv .venv` – var venv skapas (default `.venv`)
- `--with-pyav` – installerar FFmpeg *dev*‑bibliotek om du vill kunna bygga PyAV (ej nödvändigt för denna app)
- `--install-systemd` – installerar och startar en systemd‑tjänst (`genio-ai.service`)
- `--skip-apt` – hoppar över apt‑installationssteg

---

## Manuell installation

```bash
sudo apt update
sudo apt install -y python3-venv python3-dev build-essential pkg-config git curl   portaudio19-dev libportaudio2 libportaudiocpp0 alsa-utils   libsndfile1 libsndfile1-dev libopenblas-dev ffmpeg

# (endast om du vill kunna bygga PyAV)
sudo apt install -y libavformat-dev libavcodec-dev libavdevice-dev libavutil-dev   libavfilter-dev libswscale-dev libswresample-dev

python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip setuptools wheel
pip install -r requirements.txt
cp config.example.yaml config.yaml
```

---

## Konfiguration

Miljövariabler:
```bash
export PORCUPINE_ACCESS_KEY="pvac_*************"
export MQTT_USERNAME="your-hivemq-user"
export MQTT_PASSWORD="your-strong-password"
```

`config.yaml` – viktiga fält:
- `wakeword.keyword_path` → din `.ppn`
- `stt.model_dir` → lokal CT2‑modell *eller* en modellstorlek (`small`, `base` etc.) för auto‑nedladdning
- `tts.model_path` → din Piper‑röst (`.onnx`)

> Installera **piper** binären separat om den saknas. Sätt `tts.piper_bin` om den inte ligger i PATH.

---

## Körning

```bash
source .venv/bin/activate
python genio_ai.py
```

Systemd (om installerat):
- Hemligheter i `/etc/default/genio-ai`
- Hantera tjänsten: `sudo systemctl restart|status genio-ai.service`

---

## n8n

Lyssna på `genioai/request`, läs `text`, svara till `reply_topic` med JSON:
```json
{ "corr_id": "<samma-som-request>", "reply": "Svarstext", "timestamp": "..." }
```
Broker: `7dab69000883410aba47967fb078d6d9.s1.eu.hivemq.cloud`, port `8883`, TLS.

---

## Felsökning

**PyAV/FFmpeg (“Getting requirements to build wheel …”)**  
Appen kräver inte PyAV. Kör i ren venv och installera endast våra beroenden.  
Vill du ha PyAV? Kör `./setup.sh --with-pyav` för att installera FFmpeg‑dev‑bibliotek.

**Mikrofon hittas inte**  
```bash
python -c "import sounddevice as sd; print(sd.query_devices())"
```
Sätt `audio.input_device` i `config.yaml`.

**Inget svar från n8n**  
Öka `mqtt.timeout_sec` och se att n8n publicerar till `reply_topic` med samma `corr_id`.

---

## Struktur

```
genio-ai/
├─ genio_ai.py
├─ setup.sh
├─ config.example.yaml
├─ requirements.txt
├─ service/genio-ai.service
└─ resources/
   ├─ porcupine/   # .ppn
   ├─ whisper/     # CT2-modell, eller använd 'small' m.m.
   └─ piper/       # Piper ONNX-modell (.onnx + .json)
```

## Licens

MIT (exempelprojekt).

> **Obs om Python 3.13:** Vissa tredjeparts‑paket saknar färdiga hjul och kan försöka bygga från källkod.
> Kör `./setup.sh --fresh` (undviker PyAV) eller använd `--python 3.12` om du har Python 3.12 installerad.
