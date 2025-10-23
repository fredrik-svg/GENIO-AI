#!/usr/bin/env bash
set -Eeuo pipefail
# Download a Faster-Whisper (CTranslate2) model via git-lfs (default: small)
REPO="${1:-guillaumekln/faster-whisper-small}"
OUT_DIR="${2:-resources/whisper/faster-whisper-small}"

sudo apt-get update && sudo apt-get install -y git git-lfs
git lfs install

mkdir -p "$(dirname "$OUT_DIR")"
if [ -d "$OUT_DIR/.git" ]; then
  echo ">>> Repository already exists at $OUT_DIR"
else
  echo ">>> Cloning https://huggingface.co/${REPO} -> $OUT_DIR"
  git clone "https://huggingface.co/${REPO}" "$OUT_DIR"
fi

echo ">>> Done. Point stt.model_dir to: $OUT_DIR"
