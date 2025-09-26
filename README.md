# GENIO-AI - Raspberry Pi Röstassistent

En intelligent röstassistent med webbgränssnitt optimerad för Raspberry Pi 5, byggd med FastAPI, OpenAI och RAG (Retrieval-Augmented Generation).

## Raspberry Pi 5 Installation

Den här sektionen innehåller komplett instruktioner för att installera och köra GENIO-AI röstassistenten på en Raspberry Pi 5 (64-bit).

### 1. Översikt

Dessa instruktioner visar hur du kör GENIO-AI röstassistenten på Raspberry Pi 5 (64-bit). Appen tillhandahåller:
- Webbaserat gränssnitt för textchat på svenska  
- Ljudinspelning och transkription via OpenAI Whisper
- Text-till-tal (TTS) med espeak-ng
- RAG-baserad konversation med OpenAI

### 2. Förutsättningar

**Rekommenderat operativsystem:**
- Raspberry Pi OS 64-bit (Bookworm eller senare)
- Ubuntu Server 22.04/24.04 64-bit för ARM64

**Hårdvarukrav:**
- Minst 4GB RAM (8GB rekommenderas)
- Minst 32GB microSD-kort (Class 10 eller snabbare)
- Internetanslutning

**Nödvändiga paket:**
- **Docker-metod (rekommenderad):** Docker CE + Docker Compose plugin
- **Native-metod:** Python 3.11+, Git
- OpenAI API-nyckel

### 3. Installation med Docker (Föredragen metod)

#### Steg 1: Uppdatera systemet
```bash
sudo apt update && sudo apt upgrade -y
```

#### Steg 2: Installera Docker
```bash
# Installera nödvändiga paket
sudo apt install -y ca-certificates curl gnupg lsb-release

# Lägg till Dockers officiella GPG-nyckel
sudo mkdir -p /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/debian/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg

# Lägg till Docker-repositoriet
echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/debian \
  $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

# Installera Docker CE
sudo apt update
sudo apt install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin

# Lägg till din användare i docker-gruppen
sudo usermod -aG docker $USER

# Starta och aktivera Docker
sudo systemctl enable docker
sudo systemctl start docker

# Logga ut och in igen för att gruppmedlemskapet ska träda i kraft
```

#### Steg 3: Klona repositoriet
```bash
git clone https://github.com/fredrik-svg/GENIO-AI.git
cd GENIO-AI
```

#### Steg 4: Konfigurera miljövariabler
```bash
# Kopiera example-filen och redigera den
cp .env.example .env
nano .env

# Eller skapa direkt med echo
echo "OPENAI_API_KEY=sk-ditt-api-key-här" > .env

# Eller exportera miljövariabeln
export OPENAI_API_KEY="sk-ditt-api-key-här"
```

#### Steg 5: Bygg och starta med Docker Compose
```bash
# Bygga och köra i bakgrunden (rekommenderat på Pi 5)
docker compose up -d --build

# Eller med äldre docker-compose syntax
# docker-compose up -d --build

# För att bygga specifikt för arm64 (om du bygger på annan arkitektur):
# docker buildx build --platform linux/arm64 -t genio-ai .
```

#### Steg 6: Verifiera att containern körs
```bash
# Kontrollera att containern körs
docker ps

# Kolla loggar
docker compose logs -f web
```

### 4. Installation utan Docker (Native Python)

#### Steg 1: Installera Python och systempaket
```bash
# Uppdatera systemet
sudo apt update && sudo apt upgrade -y

# Installera Python och nödvändiga paket
sudo apt install -y python3.11 python3.11-pip python3.11-venv git \
    build-essential ffmpeg espeak-ng libasound2-dev portaudio19-dev \
    libsndfile1 ca-certificates wget
```

#### Steg 2: Klona och konfigurera projektet
```bash
# Klona repositoriet
git clone https://github.com/fredrik-svg/GENIO-AI.git
cd GENIO-AI

# Skapa virtuell miljö
python3.11 -m venv venv
source venv/bin/activate

# Installera Python-beroenden
pip install --upgrade pip setuptools wheel
pip install -r requirements-web.txt
```

#### Steg 3: Konfigurera miljövariabler
```bash
# Exportera OpenAI API-nyckel
export OPENAI_API_KEY="sk-ditt-api-key-här"

# För permanent konfiguration, lägg till i ~/.bashrc:
echo 'export OPENAI_API_KEY="sk-ditt-api-key-här"' >> ~/.bashrc
```

#### Steg 4: Starta applikationen
```bash
# Aktivera virtuell miljö om inte redan aktiv
source venv/bin/activate

# Starta FastAPI-servern
python webapp.py

# Eller med uvicorn direkt
uvicorn webapp:app --host 0.0.0.0 --port 8080
```

### 5. Systemd Service (för automatisk start vid boot)

#### För Docker-version:
```bash
# Skapa service-fil
sudo nano /etc/systemd/system/genio-ai.service
```

Innehåll för service-filen:
```ini
[Unit]
Description=GENIO-AI Voice Assistant
Requires=docker.service
After=docker.service

[Service]
Type=oneshot
RemainAfterExit=yes
WorkingDirectory=/home/pi/GENIO-AI
ExecStart=/usr/bin/docker compose up -d
ExecStop=/usr/bin/docker compose down
TimeoutStartSec=0
User=pi

[Install]
WantedBy=multi-user.target
```

#### För native Python-version:
```ini
[Unit]
Description=GENIO-AI Voice Assistant
After=network.target

[Service]
Type=simple
User=pi
WorkingDirectory=/home/pi/GENIO-AI
Environment=OPENAI_API_KEY=sk-ditt-api-key-här
ExecStart=/home/pi/GENIO-AI/venv/bin/python webapp.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

#### Aktivera och starta tjänsten:
```bash
# Ladda om systemd-konfiguration
sudo systemctl daemon-reload

# Aktivera tjänsten för automatisk start
sudo systemctl enable genio-ai.service

# Starta tjänsten
sudo systemctl start genio-ai.service

# Kontrollera status
sudo systemctl status genio-ai.service
```

### 6. Vanliga problem och felsökning

#### Arkitekturproblem (x86 vs arm64):
```bash
# På Raspberry Pi 5 ska bygget fungera automatiskt, men om du bygger från annan arkitektur:

# Tvinga arm64-plattform vid bygge
docker buildx build --platform linux/arm64 -t genio-ai .

# Eller bygg direkt på Pi:n (rekommenderat)
docker compose up -d --build
```

#### Byggtid och prestanda:
```bash
# Första bygget på Pi 5 kan ta 10-30 minuter beroende på internetanslutning
# Använd --no-cache för att bygga om från scratch
docker compose build --no-cache

# Kontrollera byggloggarna
docker compose logs --tail=100
```

#### Docker-behörighetsproblem:
```bash
# Lägg till användare i docker-gruppen igen
sudo usermod -aG docker $USER
# Logga ut och in igen

# Eller kör temporärt med sudo
sudo docker compose up -d
```

#### Portkonflikter:
```bash
# Kontrollera vilka portar som används
sudo netstat -tlnp | grep :8080

# Ändra port i docker-compose.yml om nödvändigt
# ports:
#   - "8081:8080"  # Extern port 8081 istället för 8080
```

#### Saknade miljövariabler:
```bash
# Kontrollera att OpenAI API-nyckeln är satt
echo $OPENAI_API_KEY

# Kontrollera Docker-miljövariabler
docker compose config
```

#### Loggar för felsökning:
```bash
# Docker-loggar
docker compose logs -f web

# Systemd-loggar
sudo journalctl -u genio-ai.service -f

# Native Python-loggar
tail -f ~/.local/share/genio-ai/logs/app.log
```

### 7. Kontrollera att appen är igång

#### Kontrollera tjänstens hälsa:
```bash
# Testa hälsokontroll
curl http://localhost:8080/api/health

# Eller från annan dator på nätverket
curl http://RASPBERRY-PI-IP:8080/api/health
```

#### Öppna webbgränssnittet:
- Lokalt: http://localhost:8080
- Från andra enheter: http://RASPBERRY-PI-IP:8080
- Ersätt `RASPBERRY-PI-IP` med din Pi:s IP-adress

#### Hitta Pi:s IP-adress:
```bash
# Visa nätverksinformation
hostname -I

# Eller mer detaljerat
ip addr show
```

### 8. Användning

1. **Textchat:** Skriv meddelanden på svenska i webbgränssnittet
2. **Röstinspelning:** Klicka "Spela in" för att spela in tal som transkriberas
3. **Text-till-tal:** Klicka "Säg (TTS)" för att höra svaret uppläst

### 9. Konfiguration

#### Skapa config.yaml (valfritt)
Appen kan använda en `config.yaml`-fil för inställningar:

```yaml
openai:
  api_key_env: "OPENAI_API_KEY"
  chat_model: "gpt-4o-mini"

language:
  speech: "sv"

rag:
  top_k: 5

tts:
  rate: 130
```

Om ingen config.yaml finns använder appen standardinställningar.

### 10. TODO - Ofullständig installation

**Observera:** Detta repository verkar sakna några nödvändiga filer för full funktionalitet:

- `rag.py` - RAG (Retrieval-Augmented Generation) modul
- `stt_openai.py` - Speech-to-text modul för OpenAI Whisper

**För utvecklare:** Dessa filer behöver skapas eller läggas till i repositoriet för att appen ska fungera fullt ut. Webapp.py importerar dessa moduler.

### 11. Licens och kontakt

Detta projekt är en del av [GENIO-AI repositoriet](https://github.com/fredrik-svg/GENIO-AI).

**Rapportera problem:**
- Öppna en issue på GitHub: https://github.com/fredrik-svg/GENIO-AI/issues
- Inkludera loggar och systeminformation vid buggrapporter

**Bidrag:**
- Pull requests välkomnas
- Följ projektets kodningsstandard
- Testa dina ändringar på Raspberry Pi 5 före inlämning

---

*Instruktioner skapade för Raspberry Pi 5 (64-bit) med Raspberry Pi OS eller Ubuntu Server.*