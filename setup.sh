\
#!/usr/bin/env bash
set -Eeuo pipefail

# Genio AI setup (v3) for Raspberry Pi 5 (Debian/Raspberry Pi OS)
# Flags:
#   --fresh           Remove and recreate .venv from scratch
#   --python <spec>   Choose Python interpreter (e.g. '3.12', 'python3.12', '/usr/bin/python3.12')
#
# v3 notes:
# - requirements.txt is minimal and does NOT include 'soundfile' or 'av'.
# - The app does not need PyAV. We explicitly uninstall 'av' just in case.

FRESH=0
PY_REQ=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --fresh) FRESH=1; shift ;;
    --python) PY_REQ="${2:-}"; shift 2 ;;
    -h|--help)
      cat <<'USAGE'
Usage: ./setup.sh [--fresh] [--python <3.12|python3.12|/path/to/python>]

Examples:
  ./setup.sh --fresh
  ./setup.sh --fresh --python 3.12
  ./setup.sh --python /usr/bin/python3.12
USAGE
      exit 0
      ;;
    *) echo "Unknown argument: $1" >&2; exit 2 ;;
  esac
done

find_python() {
  local req="$1"
  if [[ -n "$req" ]]; then
    if [[ "$req" == */* ]]; then echo "$req"; return 0; fi
    if [[ "$req" =~ ^[0-9]+\.[0-9]+$ ]]; then
      command -v "python${req}" >/dev/null 2>&1 && { command -v "python${req}"; return 0; }
      command -v "python3.${req#*.}" >/dev/null 2>&1 && { command -v "python3.${req#*.}"; return 0; }
    fi
    command -v "$req" >/dev/null 2>&1 && { command -v "$req"; return 0; }
  fi
  command -v python3.12 >/dev/null 2>&1 && { command -v python3.12; return 0; }
  command -v python3.11 >/dev/null 2>&1 && { command -v python3.11; return 0; }
  command -v python3
}

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo ">>> Installing system packages (audio, build tools, ffmpeg, BLAS) ..."
sudo apt update
sudo apt install -y \
  python3 python3-venv python3-dev \
  pkg-config build-essential \
  portaudio19-dev libportaudio2 libportaudiocpp0 alsa-utils \
  libsndfile1-dev libopenblas-dev ffmpeg

PYBIN="$(find_python "$PY_REQ")"
echo ">>> Using Python: $($PYBIN --version 2>&1)"

if [[ "$FRESH" == "1" ]]; then
  echo ">>> --fresh specified: removing existing .venv ..."
  rm -rf .venv
fi

if [[ ! -d .venv ]]; then
  echo ">>> Creating virtual environment at .venv ..."
  "$PYBIN" -m venv .venv
fi

echo ">>> Activating venv ..."
# shellcheck disable=SC1091
source .venv/bin/activate

echo ">>> Upgrading pip/setuptools/wheel ..."
pip install --upgrade pip setuptools wheel
pip cache purge || true

# Avoid PyAV entirely (not required). If present, remove it.
pip uninstall -y av || true

echo ">>> Installing Python dependencies (minimal, no av/soundfile) ..."
pip install --no-cache-dir -r requirements.txt

# Create config.yaml on first run
if [[ ! -f config.yaml ]]; then
  cp config.example.yaml config.yaml
  echo ">>> Created config.yaml from config.example.yaml"
fi

# Warn if running on Python 3.13
PYVER="$(python - <<'PY'
import sys
print(".".join(map(str, sys.version_info[:3])))
PY
)"
if [[ "$PYVER" =~ ^3\.13\..* ]]; then
  cat <<'WARN'
[!] You are running Python 3.13.
    That's OK for this project because requirements are minimal and do not
    include PyAV. If any package tries to pull 'av' in, remove it:
        pip uninstall -y av
    or re-run:
        ./setup.sh --fresh
WARN
fi

cat << 'EOM'

============================================================
 Genio AI v3: setup complete ✅

Place your models/files:
  - Porcupine (.ppn):     resources/porcupine/wakeword.ppn
  - Whisper (CT2):        resources/whisper/<ct2-model-dir>/
  - Piper (svenska ONNX): resources/piper/sv-voice.onnx (+ .json)

Required env:
  export PORCUPINE_ACCESS_KEY="pvac_*************"
  export MQTT_USERNAME="<hivemq-user>"
  export MQTT_PASSWORD="<hivemq-pass>"

Run the app:
  source .venv/bin/activate
  python3 genio_ai.py

Advanced:
  - Clean rebuild:     ./setup.sh --fresh
  - Pick Python 3.12:  ./setup.sh --fresh --python 3.12

============================================================
EOM
