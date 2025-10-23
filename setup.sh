\
#!/usr/bin/env bash
set -Eeuo pipefail

# Genio AI setup (v4) for Raspberry Pi 5 (Debian/Raspberry Pi OS)
# Flags:
#   --fresh           Remove and recreate .venv from scratch
#   --python <spec>   Choose Python interpreter (e.g. '3.12', 'python3.12', '/usr/bin/python3.12')

FRESH=0
PY_REQ=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --fresh) FRESH=1; shift ;;
    --python) PY_REQ="${2:-}"; shift 2 ;;
    -h|--help)
      cat <<'USAGE'
Usage: ./setup.sh [--fresh] [--python <3.12|python3.12|/path/to/python>]
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

echo ">>> Installing system packages (audio, build tools, ffmpeg, BLAS, git-lfs) ..."
sudo apt update
sudo apt install -y \
  python3 python3-venv python3-dev \
  pkg-config build-essential \
  portaudio19-dev libportaudio2 libportaudiocpp0 alsa-utils \
  libsndfile1-dev libopenblas-dev ffmpeg \
  git git-lfs

git lfs install

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
source .venv/bin/activate || { echo "[!] Could not activate venv. Is python3-venv installed?"; exit 1; }

# Ensure pip exists in the venv (Debian sometimes omits it if venv was created without python3-venv)
python -m ensurepip --upgrade || true

echo ">>> Upgrading pip/setuptools/wheel ..."
python -m pip install --upgrade pip setuptools wheel
pip cache purge || true

# Avoid PyAV entirely (not required). If present, remove it.
pip uninstall -y av || true

echo ">>> Installing Python dependencies (minimal, no av/soundfile) ..."
pip install --no-cache-dir -r requirements.txt

if [[ ! -f config.yaml ]]; then
  cp config.example.yaml config.yaml
  echo ">>> Created config.yaml from config.example.yaml"
fi

cat << 'EOM'

============================================================
 Genio AI v4: setup complete ✅

Model download helpers (no pip needed):
  - Porcupine (sv .pv):   ./scripts/download_porcupine_sv.sh
  - Whisper (CT2 via LFS): ./scripts/download_whisper_git.sh small   # tiny|base|small|medium|large-v3
  - Piper (sv röst):       ./scripts/download_piper_sv.sh sv_SE-lisa-medium

If you later want to use Hugging Face Python downloader:
  - Optional deps:  pip install -r requirements-optional.txt
  - Then:           ./scripts/download_with_hf.py Systran/faster-whisper-small resources/whisper/whisper-small-ct2

If you ever see: "-bash: .../.venv/bin/pip: No such file or directory"
  1) Ensure venv exists and is activated:   source .venv/bin/activate
  2) Bootstrap pip inside venv:             python -m ensurepip --upgrade
  3) Or rebuild venv cleanly:               ./setup.sh --fresh
  4) Clear any old shell hash:              hash -r

Run the app:
  source .venv/bin/activate
  export PORCUPINE_ACCESS_KEY="pvac_*************"
  export MQTT_USERNAME="<hivemq-user>"
  export MQTT_PASSWORD="<hivemq-pass>"
  python3 genio_ai.py

============================================================
EOM
