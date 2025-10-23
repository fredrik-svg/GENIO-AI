#!/usr/bin/env bash
set -euo pipefail
VOICE="${1:-sv_SE-lisa-medium}"  # alternatives: sv_SE-nst-medium, etc.
mkdir -p resources/piper

case "$VOICE" in
  sv_SE-lisa-medium)
    ONNX_URL="https://huggingface.co/rhasspy/piper-voices/resolve/main/sv/sv_SE/lisa/medium/sv_SE-lisa-medium.onnx"
    JSON_URL="https://huggingface.co/rhasspy/piper-voices/resolve/main/sv/sv_SE/lisa/medium/sv_SE-lisa-medium.onnx.json"
    ;;
  sv_SE-nst-medium)
    ONNX_URL="https://huggingface.co/rhasspy/piper-voices/resolve/main/sv/sv_SE/nst/medium/sv_SE-nst-medium.onnx"
    JSON_URL="https://huggingface.co/rhasspy/piper-voices/resolve/main/sv/sv_SE/nst/medium/sv_SE-nst-medium.onnx.json"
    ;;
  *)
    echo "Unknown voice: $VOICE"
    exit 2
    ;;
esac

curl -L -o "resources/piper/${VOICE}.onnx" "$ONNX_URL"
curl -L -o "resources/piper/${VOICE}.onnx.json" "$JSON_URL"
echo "Downloaded to resources/piper/${VOICE}.onnx(+.json)"
