\
#!/usr/bin/env bash
set -Eeuo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
echo "Återskapar .venv ..."
rm -rf .venv
./setup.sh --fresh "${@}"
