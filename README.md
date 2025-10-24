# Genio AI

Genio AI är en svensk, offline-kapabel röstagent för Raspberry Pi 5 som kombinerar lokal taligenkänning, textgenerering via n8n-arbetsflöden, och text-till-tal.

## Funktioner

- **Väckningsfras**: Porcupine (.ppn) med justerbar känslighet
- **Tal-till-text**: Faster Whisper (CTranslate2) lokalt på svenska
- **Text-till-tal**: Piper TTS med svensk röstmodell, lokalt
- **MQTT**: Säker kommunikation (TLS/SSL, port 8883) mot n8n-workflow
- **Offline**: Efter initial setup fungerar allt utan internet
- **Språk**: Förinställt till svenska (sv)

## Arbetsflöde

1. **Lyssna på wakeword** - Väntar på väckningsfrasen
2. **Tal till text** - Konverterar användarens tal till text
3. **MQTT kommunikation** - Skickar text till n8n-flöde via MQTT
4. **n8n-bearbetning** - n8n läser MQTT-kanalen och skickar tillbaka ett svar
5. **Text till tal** - Läser upp svaret från n8n
6. **Upprepa** - Redo för nästa väckningsfras

## Installation

Se [setup.sh](setup.sh) för automatisk installation på Raspberry Pi 5.

```bash
./setup.sh
```

## Konfiguration

1. Kopiera `config.example.yaml` till `config.yaml`
2. Redigera konfigurationsfilen med dina inställningar
3. Sätt miljövariabler för känslig information:
   - `PORCUPINE_ACCESS_KEY` - Din Picovoice-nyckel
   - `MQTT_USERNAME` - HiveMQ Cloud-användarnamn
   - `MQTT_PASSWORD` - HiveMQ Cloud-lösenord

## MQTT-konfiguration

Genio AI använder HiveMQ Cloud för MQTT-kommunikation:
- **Host**: `7dab69000883410aba47967fb078d6d9.s1.eu.hivemq.cloud`
- **Port**: `8883` (TLS/SSL)
- **Protokoll**: MQTT över TLS

## Hälsokontroll

Innan du kör Genio AI, använd hälsokontroll-skriptet för att verifiera att allt är korrekt konfigurerat:

```bash
python3 scripts/health_check.py
```

## Körning

```bash
source .venv/bin/activate
export PORCUPINE_ACCESS_KEY="pvac_*************"
export MQTT_USERNAME="<hivemq-user>"
export MQTT_PASSWORD="<hivemq-pass>"
python3 genio_ai.py
```

## Förbättringar i denna version

- ✅ Förbättrad felhantering i alla komponenter
- ✅ Konfigurationsvalidering vid start
- ✅ Automatisk återanslutning för MQTT med exponentiell backoff
- ✅ Bättre loggning med tidsstämplar och nivåer
- ✅ Graceful shutdown vid SIGINT/SIGTERM
- ✅ Hälsokontroll-skript för systemvalidering
- ✅ Förbättrad säkerhet med input-validering
- ✅ Timeout-hantering för TTS och externa processer
- ✅ .gitignore för bättre versionshantering
- ✅ Detaljerad dokumentation

## Felsökning

### PyAV-problem

På Python 3.13 drar vissa `faster-whisper`-versioner in `av==10.*` via sina metadata. V7-installern undviker detta genom att:
1) Installera `faster-whisper==0.10.1` med `--no-deps`, och
2) Appen skickar **PCM-array** direkt till Faster-Whisper (ingen fil-avkodning), så `av` behövs inte i runtime.

Använd `scripts/diagnose_av.sh` för att diagnostisera PyAV-relaterade problem.

### Modeller

Se [MODELS.md](MODELS.md) för information om hur du laddar ner och konfigurerar modeller.

## Systemkrav

- Raspberry Pi 5
- Debian/Raspberry Pi OS
- Python 3.11 eller 3.12
- Mikrofon och högtalare
- Internet för initial setup och MQTT-kommunikation
