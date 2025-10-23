#!/usr/bin/env bash
set -Eeuo pipefail

# Genio AI setup for Raspberry Pi 5 (Debian/Raspberry Pi OS)
# - Installs system packages (audio, build tools, ffmpeg)
# - Creates a clean Python venv and installs Python deps
# - Copies config.example.yaml -> config.yaml (if missing)
# - Reminds you how to provide secrets and run the app

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo ">>> Uppdaterar paketindex och installerar systempaket ..."
sudo apt update
sudo apt install -y   python3-pip python3-venv python3-dev   pkg-config build-essential   portaudio19-dev libportaudio2 libportaudiocpp0 alsa-utils   libsndfile1-dev libopenblas-dev   ffmpeg   libavformat-dev libavcodec-dev libavdevice-dev libavutil-dev   libavfilter-dev libswscale-dev libswresample-dev

echo ">>> Skapar virtuell miljö (.venv) ..."
if [ ! -d .venv ]; then
  python3 -m venv .venv
fi
source .venv/bin/activate

echo ">>> Uppgraderar pip/setuptools/wheel ..."
pip install --upgrade pip setuptools wheel

# Säkerställ att PyAV inte dras in i onödan
pip uninstall -y av || true

echo ">>> Installerar Python-beroenden ..."
pip install -r requirements.txt

if [ ! -f config.yaml ]; then
  cp config.example.yaml config.yaml
  echo ">>> Skapade config.yaml från config.example.yaml"
fi

cat << 'EOM'

============================================================
 Genio AI: installation klar ✅

Lägg dina modeller/filer:
  - Porcupine (.ppn):     resources/porcupine/wakeword.ppn
  - Whisper (CT2):        resources/whisper/<din-ct2-modell-katalog>/
  - Piper (svensk onnx):  resources/piper/sv-voice.onnx (+ .json i samma dir)
  - Piper binär:          /usr/local/bin/piper  (eller ange sökväg i config.yaml)

Miljövariabler (krav):
  export PORCUPINE_ACCESS_KEY="pvac_*************"
  export MQTT_USERNAME="<hivemq-user>"
  export MQTT_PASSWORD="<hivemq-pass>"

Starta appen:
  source .venv/bin/activate
  python3 genio_ai.py

MQTT (HiveMQ Cloud/TLS):
  Host: 7dab69000883410aba47967fb078d6d9.s1.eu.hivemq.cloud
  Port: 8883 (TLS)
  Topics:
    - Request: genioai/request
    - Response (wildcard): genioai/response/<corr_id>

Systemd (valfritt):
  Se service/genio-ai.service och uppdatera användare/paths/env.

Felsökning kort:
  - PyAV/FFmpeg build-fel? Kör detta script (installerar -dev-paket) och
    använd ren venv (.venv). Vår app kräver inte PyAV.
  - Mikrofon: sätt 'audio.input_device' i config.yaml. Lista enheter i Python:
      python3 -c "import sounddevice as sd; print(sd.query_devices())"
  - Wakeword: justera 'wakeword.sensitivity' (0.0–1.0).

============================================================
EOM
