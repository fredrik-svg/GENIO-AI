# Genio AI

### Varför försökte pip installera `av`?
På Python 3.13 drar vissa `faster-whisper`‑versioner in `av==10.*` via sina metadata. V7‑installern undviker detta genom att:
1) Installera `faster-whisper==0.10.1` med `--no-deps`, och
2) Appen skickar **PCM‑array** direkt till Faster‑Whisper (ingen fil‑avkodning), så `av` behövs inte i runtime.
