\
#!/usr/bin/env bash
set -Eeuo pipefail

# Genio AI setup for Raspberry Pi 5 (Debian/Raspberry Pi OS)
# Flags:
#   --fresh           Remove and recreate .venv from scratch
#   --python <spec>   Choose Python interpreter (e.g. '3.12', 'python3.12', '/usr/bin/python3.12')
#
# The script installs system packages (audio, build tools, ffmpeg),
# creates an isolated venv, avoids PyAV, and installs Python deps.
#
# Note: The app does not require PyAV. If you hit build errors from 'av' on Python 3.13,
# run this script with --fresh or specify --python 3.12

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
    *)
      echo "Unknown argument: $1" >&2
      exit 2
      ;;
  esac
done

find_python() {
  local req="$1"
  if [[ -n "$req" ]]; then
    # If it's a path
    if [[ "$req" == */* ]]; then
      echo "$req"
      return 0
    fi
    # If it's a version like "3.12" or "3.11"
    if [[ "$req" =~ ^[0-9]+\.[0-9]+$ ]]; then
      if command -v "python${req}" >/dev/null 2>&1; then
        command -v "python${req}"
        return 0
      fi
      if command -v "python3.${req#*.}" >/dev/null 2>&1; then
        command -v "python3.${req#*.}"
        return 0
      fi
    fi
    # Otherwise treat as a command name like "python3.12"
    if command -v "$req" >/dev/null 2>&1; then
      command -v "$req"
      return 0
    fi
  fi

  # Default preference order
  if command -v python3.12 >/dev/null 2>&1; then
    command -v python3.12; return 0
  fi
  if command -v python3.11 >/dev/null 2>&1; then
    command -v python3.11; return 0
  fi
  command -v python3
}

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo ">>> Installing system packages (audio, build tools, ffmpeg, BLAS) ..."
sudo apt update
sudo apt install -y \
  python3-pip python3-venv python3-dev \
  pkg-config build-essential \
  portaudio19-dev libportaudio2 libportaudiocpp0 alsa-utils \
  libsndfile1-dev libopenblas-dev \
  ffmpeg \
  libavformat-dev libavcodec-dev libavdevice-dev libavutil-dev \
  libavfilter-dev libswscale-dev libswresample-dev

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

# Avoid PyAV (not required). If present from a previous environment, remove it.
pip uninstall -y av || true

echo ">>> Installing Python dependencies (no cache) ..."
pip install --no-cache-dir -r requirements.txt

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
[!] Detected Python 3.13.
    If you encounter build issues with third-party packages, consider installing Python 3.12:
        sudo apt install -y python3.12 python3.12-venv python3.12-dev
    Then rerun:
        ./setup.sh --fresh --python 3.12
WARN
fi

cat << 'EOM'

============================================================
 Genio AI: setup complete ✅

Place your models/files:
  - Porcupine (.ppn):     resources/porcupine/wakeword.ppn
  - Whisper (CT2):        resources/whisper/<ct2-model-dir>/
  - Piper (svenska ONNX): resources/piper/sv-voice.onnx (+ .json)

Required environment variables:
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
