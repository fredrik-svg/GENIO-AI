
---

## ❗ Varför får jag `-bash: .../.venv/bin/pip: No such file or directory`?

Det betyder att din `pip`-sökväg pekar på en **icke-existerande** venv (t.ex. efter ominstallation eller `--fresh`), eller att ett alias/kommandocache pekar fel.

**Snabbfix (kör i projektkatalogen):**
```bash
# rensa ev. gammal venv och bygg om
./setup.sh --fresh

# aktivera ny venv
source .venv/bin/activate

# installera Hugging Face CLI (om du vill använda snapshot_download)
python -m pip install -U huggingface_hub
```

**Om felet kvarstår, felsök:**
```bash
# Finns filen?
ls -l .venv/bin/python .venv/bin/pip || echo "saknas"

# Rensa shell-cache och alias för 'pip'
hash -r
unalias pip 2>/dev/null || true
type -a pip

# Använd alltid robust form inne i venv:
python -m pip --version
python -m pip install -U huggingface_hub
```

**Alternativ utan HF-CLI:** använd våra script i `scripts/`  
- `scripts/download_whisper_ct2.sh` (git-lfs)  
- `scripts/voices.sh` (Piper-röst)  
- `scripts/download_porcupine_sv_pv.sh` (svensk Porcupine .pv)

## 🩺 Diagnostik
Om du ser att `pip` saknas eller att `av` försöker byggas:
```bash
./scripts/doctor.sh
# eller återskapa venv:
./scripts/fix_venv.sh --python 3.12   # om 3.12 finns, annars utan flagga
```
