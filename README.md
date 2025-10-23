
## 📥 Modeller – snabbkommandon (utan pip)
```bash
./scripts/download_porcupine_sv.sh
./scripts/download_whisper_git.sh small
./scripts/download_piper_sv.sh sv_SE-lisa-medium
```

## 🧰 Hugging Face CLI / pip-fel
Får du `-bash: .../.venv/bin/pip: No such file or directory`?
```bash
# 1) Aktivera venv
source .venv/bin/activate

# 2) Bootstrappa pip inuti venv
python -m ensurepip --upgrade

# 3) Uppgradera verktyg
python -m pip install --upgrade pip setuptools wheel

# 4) Om det fortfarande strular: bygg om venv
./setup.sh --fresh
```
