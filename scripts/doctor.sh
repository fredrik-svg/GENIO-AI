\
#!/usr/bin/env bash
set -Eeuo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

echo "== Genio AI doctor =="

if [[ ! -d .venv ]]; then
  echo "[!] Ingen .venv hittades. Kör:  ./setup.sh --fresh"
  exit 2
fi

# Try activate venv
if ! source .venv/bin/activate 2>/dev/null; then
  echo "[!] Misslyckades aktivera .venv. Återskapa: ./setup.sh --fresh"
  exit 2
fi

# Ensure pip exists even on minimal Debian venvs
python -m ensurepip --upgrade || true

# Upgrade basic build tools for Python packages
python -m pip install --upgrade pip setuptools wheel || true
hash -r || true

echo "Python: $(python -V)"
echo "pip:    $(python -m pip -V || echo 'saknas')"
echo

echo "== PIP config =="
python - <<'PY'
import sys, subprocess
try:
    out = subprocess.check_output(["pip", "config", "list", "-v"], text=True)
    print(out)
except Exception as e:
    print("Kunde inte läsa pip config:", e)
PY

echo "== Krävda filer (requirements) i projektet =="
ls -l requirements.txt requirements-optional.txt 2>/dev/null || true
echo

echo "== Sök efter 'av' i kravfiler =="
grep -R --line-number -E '(^|[^a-z])av([^a-z]|$)' requirements*.txt 2>/dev/null || echo "(inga träffar)"

echo
echo "== Installerade paket som matchar 'av' =="
python - <<'PY'
import pkgutil
print("av installerat? ->", bool(pkgutil.find_loader("av")))
PY

# Try remove av if present
python -m pip uninstall -y av || true

# Show reverse dependencies if any would re-install av
python -m pip install -q pipdeptree || true
echo
echo "== Om något paket skulle dra in 'av', syns det här =="
pipdeptree -r -p av || true

cat <<'TIP'

Tips:
- Om ett paket här ovan kräver 'av', avinstallera det:
    pip uninstall -y <paketnamn> av
- Installera sedan endast projektets minimala beroenden:
    pip install --no-cache-dir -r requirements.txt

TIP
