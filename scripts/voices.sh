#!/usr/bin/env bash
set -Eeuo pipefail
# Download a Swedish Piper voice (default: sv_SE/lisa/medium) into resources/piper/
VOICE_PATH="${1:-sv/sv_SE/lisa/medium}"
OUT_DIR="resources/piper"
mkdir -p "$OUT_DIR"
BASE_URL="https://huggingface.co/rhasspy/piper-voices/resolve/main"

ONNX="$(basename "$VOICE_PATH")"
ONNX_FILE="${VOICE_PATH##*/}.onnx"
JSON_FILE="${VOICE_PATH##*/}.onnx.json"

echo ">>> Downloading Piper voice: $VOICE_PATH"
curl -L -o "${OUT_DIR}/${ONNX_FILE}" "${BASE_URL}/${VOICE_PATH}/${ONNX_FILE}"
curl -L -o "${OUT_DIR}/${JSON_FILE}" "${BASE_URL}/${VOICE_PATH}/${JSON_FILE}"

echo ">>> Saved:"
echo " - ${OUT_DIR}/${ONNX_FILE}"
echo " - ${OUT_DIR}/${JSON_FILE}"
echo
echo "Update your config.yaml -> tts.model_path: ${OUT_DIR}/${ONNX_FILE}"
