#!/usr/bin/env bash
set -euo pipefail
if [[ ! -f ".venv/bin/activate" ]]; then
  echo "[!] No .venv found. Run: ./setup.sh --fresh"
  exit 2
fi
# shellcheck disable=SC1091
source .venv/bin/activate
python - <<'PY'
import importlib.util as u
print("PyAV installerat? ->", bool(u.find_spec("av")))
PY
pip install -q pipdeptree || true
echo ">>> Dependency chain(s) requiring 'av' (if any):"
pipdeptree -r -p av || true
