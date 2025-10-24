# Genio AI – Svensk, offline‑kapabel röstagent för Raspberry Pi 5

Genio AI är en lokal röstagent som triggas av **Porcupine** (svensk wakeword), transkriberar tal lokalt med **Faster‑Whisper (CTranslate2)** och läser upp svar med **Piper TTS**. Kommunikation mot ditt **n8n‑workflow** sker över **MQTT (TLS/SSL, 8883)** via **HiveMQ Cloud**.

Efter att modellerna och nycklarna laddats ner fungerar STT/TTS/wakeword **offline**. Endast själva MQTT‑flödet kräver nät.

---

## ✨ Funktioner

- **Wakeword:** Porcupine `.ppn` med justerbar känslighet och **svensk språkmodell `.pv`**.
- **STT:** Faster‑Whisper (CT2), låst till **svenska**.
- **TTS:** Piper (svensk röstmodell, lokal ONNX).
- **MQTT:** TLS (8883) mot HiveMQ Cloud → n8n läser/returnerar svar.
- **Pi 5‑optimerad:** `compute_type: int8` för Whisper ger bra fart på CPU.

---

## 🧩 Förutsättningar

- Raspberry Pi 5 (64‑bit Raspberry Pi OS, “Bookworm” rekommenderas)
- USB‑mikrofon + högtalare / hörlurar
- Nät första gången (hämtning av paket och modeller)
- Ditt HiveMQ Cloud‑konto (host, användare, lösenord) och ett n8n‑flöde

---

## 🚀 Installation (rekommenderat, v5/v6)

```bash
# 1) Packa upp
unzip genio-ai-v6.zip -d ~/
cd ~/genio-ai

# 2) Kör setup i STRICT-läge (rensar/bygger om .venv, --no-deps default)
chmod +x setup.sh
./setup.sh --fresh

# (valfritt) välj specifik Python
./setup.sh --fresh --python 3.12
# (valfritt) normal pip-installation utan strict
./setup.sh --fresh --no-strict
```

> **STRICT-läget** installerar en explicit paketlista med `--no-deps` för att förhindra att något drar in **PyAV (`av`)** – vår app behöver inte `av`.

---

## 📥 Modeller – hämta utan pip/CLI

```bash
# Svensk Porcupine språkmodell (.pv)
./scripts/download_porcupine_sv.sh

# Faster-Whisper (CTranslate2) via git-lfs (t.ex. small)
./scripts/download_whisper_git.sh small
# alternativ: tiny | base | small | medium | large-v3

# Piper – svensk röst (ex. 'sv_SE-lisa-medium')
./scripts/download_piper_sv.sh sv_SE-lisa-medium
```

Lägg din **.ppn** (wakeword) från **Picovoice Console** i `resources/porcupine/wakeword.ppn`.

---

## ⚙️ Konfiguration (config.yaml)

Skapa din konfig från mallen:
```bash
cp config.example.yaml config.yaml
```

Fyll i värden (speciellt MQTT och filvägar). Viktigast:
- `wakeword.keyword_path` → din `.ppn`
- `wakeword.model_path` → `porcupine_params_sv.pv`
- `stt.model_dir` → din CT2‑modellmapp
- `tts.model_path` → din Piper‑röst `.onnx`
- `mqtt.host`/`port`/env‑nycklar

Se **“Fältförklaring”** längre ned.

---

## ▶️ Kör

```bash
source .venv/bin/activate
export PORCUPINE_ACCESS_KEY="pvac_*************"
export MQTT_USERNAME="<hivemq-user>"
export MQTT_PASSWORD="<hivemq-pass>"
python3 genio_ai.py
```

---

## 🔌 n8n & MQTT – kontrakt

**App → n8n** (topic `genioai/request`):
```json
{
  "text": "slå på lampan i köket",
  "lang": "sv",
  "timestamp": "2025-10-24T12:34:56Z",
  "corr_id": "d1c...",
  "reply_topic": "genioai/response/d1c...",
  "source": "genio-ai-rpi5"
}
```

**n8n → App** (topic `genioai/response/<corr_id>`):
```json
{
  "corr_id": "d1c...",
  "reply": "Okej, jag slog på lampan i köket.",
  "timestamp": "2025-10-24T12:34:57Z"
}
```

> I n8n: MQTT Trigger på `genioai/request` → bearbeta `{{$json.text}}` → publicera svar till `{{$json.reply_topic}}` **med samma `corr_id`**.

---

## 🧾 Fältförklaring (config.yaml)

```yaml
audio:
  input_device: null         # ALSA-index eller null för default (se "Ljudtips")
  sample_rate: 16000         # 16 kHz, matchar Porcupine/Whisper
  vad_aggressiveness: 2      # 0-3 (högre = klipper tystnad tidigare)
  max_utterance_sec: 12      # hård gräns inspelningslängd
  silence_end_ms: 800        # avsluta efter så här mycket tystnad

wakeword:
  access_key_env: "PORCUPINE_ACCESS_KEY"     # miljövariabel med din Picovoice AccessKey
  keyword_path: "resources/porcupine/wakeword.ppn"
  model_path:   "resources/porcupine/porcupine_params_sv.pv"  # svensk .pv krävs för svenska
  sensitivity: 0.55

stt:
  model_dir: "resources/whisper/whisper-small-ct2"  # CT2‑modellmapp
  compute_type: "int8"                              # int8|int8_float16|float16|float32
  language: "sv"
  beam_size: 5

tts:
  piper_bin: "/usr/local/bin/piper"                 # eller ange egen sökväg
  model_path: "resources/piper/sv_SE-lisa-medium.onnx"
  keep_wav: false

mqtt:
  host: "7dab69000883410aba47967fb078d6d9.s1.eu.hivemq.cloud"
  port: 8883
  username_env: "MQTT_USERNAME"
  password_env: "MQTT_PASSWORD"
  client_id: "genio-ai-rpi5"
  ca_certs: null             # null = systemets CA
  tls_insecure: false
  qos: 1
  request_topic: "genioai/request"
  base_response_topic: "genioai/response"
  timeout_sec: 15
  keepalive: 60
  clean_session: true
```

---

## 🗂️ Kataloglayout
```
genio-ai/
├─ genio_ai.py
├─ setup.sh
├─ README.md
├─ MODELS.md
├─ config.example.yaml
├─ requirements.txt
├─ scripts/
│  ├─ download_porcupine_sv.sh
│  ├─ download_whisper_git.sh
│  ├─ download_piper_sv.sh
│  └─ diagnose_av.sh
└─ resources/
   ├─ porcupine/
   ├─ whisper/
   └─ piper/
```

---

## 🔧 Ljudtips

- Lista enheter och hitta rätt `input_device`:
  ```bash
  python3 - <<'PY'
  import sounddevice as sd; print(sd.query_devices())
  PY
  ```
- Justera nivåer i `alsamixer`. Kontrollera att mic inte är mutad.

---

## 🧪 Felsökning

### 1) `-bash: .../.venv/bin/pip: No such file or directory`
Orsaker: venv skapades utan `python3-venv`, pip bootstrappades inte, eller venv pekar på en borttagen interpreter.  
**Lösning:**
```bash
source .venv/bin/activate 2>/dev/null || true
python -m ensurepip --upgrade
python -m pip install --upgrade pip setuptools wheel
hash -r
# eller enklast: ./setup.sh --fresh
```

### 2) PyAV (`av`) försöker bygga på Python 3.13
Vår app behöver **inte** PyAV. STRICT‑läget i `setup.sh` installerar med `--no-deps`.  
Om du ändå ser PyAV: kör diagnostik och avinstallera boven.
```bash
./scripts/diagnose_av.sh
pip uninstall -y av <paket-som-kräver-av>
./setup.sh --fresh
```

### 3) Wakeword triggar inte / triggar för ofta
- Höj/sänk `wakeword.sensitivity` (0.0–1.0).
- Byt mikrofon eller minska bakgrundsbrus.

### 4) Whisper är långsam
- Använd CT2‑modell **small** och `compute_type: int8`.
- Sänk `beam_size` till 1–3 för snabbare, något mindre exakt.

### 5) Piper låter hackigt
- Testa annan svensk röst (t.ex. `sv_SE-nst-medium`).
- Kontrollera att uppspelning via `aplay` fungerar och att CPU inte är 100 %.

---

## 🔐 Säkerhet
Spara aldrig hemligheter i repo. Använd **miljövariabler** eller en `EnvironmentFile` för systemd‑tjänsten.

---

## 📦 Licens
MIT – exempelprojekt. Anpassa efter behov.
