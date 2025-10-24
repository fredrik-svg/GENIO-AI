# Modeller: nedladdning och placering

## Porcupine (svenska)
- `scripts/download_porcupine_sv.sh` hämtar `porcupine_params_sv.pv`.
- Lägg din `wakeword.ppn` (skapad i Picovoice Console) i `resources/porcupine/`.
- **OBS:** `model_path` är valfri. Om den svenska modellfilen inte finns eller saknas, använder Porcupine sin inbyggda standardmodell istället.
- Sätt i `config.yaml`:
  ```yaml
  wakeword:
    keyword_path: resources/porcupine/wakeword.ppn
    model_path:   resources/porcupine/porcupine_params_sv.pv  # Valfri
  ```

## Whisper (Faster-Whisper, CTranslate2)
- Utan pip/CLI: `scripts/download_whisper_git.sh small` (kräver git-lfs).
- Med Python (valfritt): installera `huggingface_hub` från `requirements-optional.txt`
  och kör `scripts/download_with_hf.py Systran/faster-whisper-small resources/whisper/whisper-small-ct2`.

## Piper (svenska röster)
- **Piper-binär**: `scripts/install_piper.sh` installerar Piper TTS-binären till `/usr/local/bin/piper`.
- **Röstmodeller**: `scripts/download_piper_sv.sh sv_SE-lisa-medium` laddar ner röst + json till `resources/piper/`.
- Ange sökvägen i `tts.model_path` i `config.yaml`.

## Kataloglayout
```
resources/
├─ porcupine/
│  ├─ wakeword.ppn
│  └─ porcupine_params_sv.pv
├─ whisper/
│  └─ whisper-small-ct2/
└─ piper/
   ├─ sv_SE-lisa-medium.onnx
   └─ sv_SE-lisa-medium.onnx.json
```
