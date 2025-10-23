#!/usr/bin/env bash
set -euo pipefail
mkdir -p resources/porcupine
curl -L -o resources/porcupine/porcupine_params_sv.pv   https://raw.githubusercontent.com/Picovoice/porcupine/master/lib/common/porcupine_params_sv.pv
echo "Downloaded: resources/porcupine/porcupine_params_sv.pv"
