#!/usr/bin/env bash
set -euo pipefail
MODEL="${1:-small}"   # tiny|base|small|medium|large-v2|large-v3
DEST="resources/whisper/whisper-${MODEL}-ct2"

sudo apt-get update
sudo apt-get install -y git git-lfs
git lfs install

REPO="https://huggingface.co/Systran/faster-whisper-${MODEL}"
echo "Cloning ${REPO} -> ${DEST}"
mkdir -p "$(dirname "$DEST")"
git clone "${REPO}" "${DEST}" || {
  echo "Clone failed. Does the model '${MODEL}' exist?"
  exit 1
}
echo "Done."
