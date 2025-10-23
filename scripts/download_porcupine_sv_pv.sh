#!/usr/bin/env bash
set -Eeuo pipefail
# Download Swedish Porcupine language model (.pv) into resources/porcupine/
OUT_DIR="resources/porcupine"
mkdir -p "$OUT_DIR"
URL="https://raw.githubusercontent.com/Picovoice/porcupine/master/lib/common/porcupine_params_sv.pv"
curl -L -o "${OUT_DIR}/porcupine_params_sv.pv" "$URL"
echo ">>> Saved: ${OUT_DIR}/porcupine_params_sv.pv"
echo "Add to config.yaml -> wakeword.model_path: ${OUT_DIR}/porcupine_params_sv.pv"
