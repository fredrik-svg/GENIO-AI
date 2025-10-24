\
#!/usr/bin/env bash
set -Eeuo pipefail

# Genio AI setup (v7) for Raspberry Pi 5 (Debian/Raspberry Pi OS)
# Flags:
#   --fresh             Remove and recreate .venv from scratch
#   --python <spec>     Choose Python interpreter (e.g. '3.12', 'python3.12', '/usr/bin/python3.12')
#   --no-strict         Install with normal dependency resolution (disables --no-deps strict mode)
#
# Default: STRICT mode is ON (uses --no-deps and installs explicit package list).
# If STRICT mode fails, we fall back to a two-step install that AVOIDS 'av':
#   1) pip install -r requirements-nonav.txt
#   2) pip install --no-deps faster-whisper==0.10.1
#
# This prevents 'pip' from trying to pull 'av==10.*' from faster-whisper metadata.

FRESH=0
PY_REQ=""
STRICT=1

while [[ $# -gt 0 ]]; do
  case "$1" in
    --fresh) FRESH=1; shift ;;
    --python) PY_REQ="${2:-}"; shift 2 ;;
    --no-strict) STRICT=0; shift ;;
    -h|--help)
      cat <<'USAGE'
Usage: ./setup.sh [--fresh] [--python <3.12|python3.12|/path/to/python>] [--no-strict]
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

echo ">>> Installing system packages (audio, build tools, ffmpeg, BLAS, git-lfs, libffi-dev, espeak-ng) ..."
sudo apt update
sudo apt install -y \
  python3 python3-venv python3-dev \
  pkg-config build-essential \
  libffi-dev \
  portaudio19-dev libportaudio2 libportaudiocpp0 alsa-utils \
  libsndfile1-dev libopenblas-dev ffmpeg \
  espeak-ng \
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

# Ensure pip exists in the venv
python -m ensurepip --upgrade || true

echo ">>> Upgrading pip/setuptools/wheel ..."
python -m pip install --upgrade pip setuptools wheel
pip cache purge || true
hash -r || true

# Avoid PyAV entirely (not required). If present, remove it.
pip uninstall -y av || true

if [[ "$STRICT" == "1" ]]; then
  echo ">>> STRICT mode: installing explicit packages with --no-deps ..."
  set +e
  # Quote '<1' so the shell doesn't interpret '<' as redirection.
  pip install --no-cache-dir --no-deps \
    "numpy==1.*" \
    "paho-mqtt==2.*" \
    "PyYAML==6.*" \
    "pvporcupine==3.*" \
    "webrtcvad==2.*" \
    "ctranslate2==4.*" \
    "faster-whisper==0.10.1" \
    "tokenizers>=0.13,<1" \
    "sounddevice==0.4.*" \
    "cffi>=1.15,<2" \
    "pycparser>=2.21,<3"
  STRICT_RC=$?
  set -e
  if [[ $STRICT_RC -ne 0 ]]; then
    echo "[!] STRICT install failed. Falling back to av-safe two-step install ..."
    pip install --no-cache-dir -r requirements-nonav.txt
    pip install --no-cache-dir --no-deps "faster-whisper==0.10.1"
  fi
else
  echo ">>> Non-strict mode: installing from requirements-nonav.txt then faster-whisper --no-deps ..."
  pip install --no-cache-dir -r requirements-nonav.txt
  pip install --no-cache-dir --no-deps "faster-whisper==0.10.1"
fi

if [[ ! -f config.yaml ]]; then
  cp config.example.yaml config.yaml
  echo ">>> Created config.yaml from config.example.yaml"
fi

cat << 'EOM'

============================================================
 Genio AI v7: setup complete ✅

Why did 'av' appear earlier?
  - Recent faster-whisper metadata can pull 'av==10.*' on Python 3.13.
  - This installer prevents that by installing faster-whisper with --no-deps
    and feeding raw audio arrays to avoid any runtime need for PyAV.

Model download helpers (no pip needed):
  - Porcupine (sv .pv):    ./scripts/download_porcupine_sv.sh
  - Whisper (CT2 via LFS): ./scripts/download_whisper_git.sh small
  - Piper binary:          ./scripts/install_piper.sh
  - Piper (sv röst):       ./scripts/download_piper_sv.sh sv_SE-lisa-medium

Diagnose if something tries to install 'av':
  ./scripts/diagnose_av.sh

Run the app:
  source .venv/bin/activate
  export PORCUPINE_ACCESS_KEY="pvac_*************"
  export MQTT_USERNAME="<hivemq-user>"
  export MQTT_PASSWORD="<hivemq-pass>"
  python3 genio_ai.py

============================================================
EOM
