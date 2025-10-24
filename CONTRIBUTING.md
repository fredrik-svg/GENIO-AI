# Bidragsguide för Genio AI

Tack för ditt intresse för att bidra till Genio AI! Detta dokument ger riktlinjer för hur du kan hjälpa till med projektet.

## Kom igång

1. Forka repositoryt
2. Klona din fork lokalt
3. Kör `./setup.sh` för att installera beroenden
4. Skapa en ny branch för din funktion/fix

## Utvecklingsmiljö

### Förutsättningar

- Raspberry Pi 5 (för fullständig testning)
- Python 3.11 eller 3.12
- Virtuell miljö (skapas automatiskt av setup.sh)

### Testning

Innan du skickar in ändringar:

1. Kör syntaxkontroll:
```bash
python3 -m py_compile genio_ai.py
```

2. Kör hälsokontrollen:
```bash
python3 scripts/health_check.py
```

3. Testa manuellt om möjligt med riktig hårdvara

## Kodstandarder

### Python-kod

- Använd 4 mellanslag för indentering
- Följ PEP 8-riktlinjer där det är lämpligt
- Lägg till docstrings för alla publika funktioner och klasser
- Använd type hints där det är meningsfullt
- Kommentera komplex logik på svenska

### Felhantering

- Fånga specifika undantag, inte bara `Exception`
- Logga fel med lämplig nivå (ERROR, WARNING, INFO, DEBUG)
- Ge användbara felmeddelanden på svenska
- Använd try-except-finally för resursstädning

### Loggning

- Använd logging-modulen, inte print()
- Välj rätt loggnivå:
  - DEBUG: Detaljerad diagnostisk information
  - INFO: Bekräftelse att saker fungerar som förväntat
  - WARNING: Något oväntat hände, men applikationen fungerar
  - ERROR: Ett allvarligare problem
  - CRITICAL: Applikationen kan inte fortsätta

### Säkerhet

- Validera alltid användarinput
- Använd miljövariabler för känslig information
- Skydda mot command injection i subprocess-anrop
- Använd timeout för externa processer
- Logga aldrig känslig information (lösenord, nycklar)

## Git Workflow

1. Skapa en feature branch från main:
```bash
git checkout -b feature/min-nya-funktion
```

2. Gör dina ändringar och commita ofta:
```bash
git add .
git commit -m "Beskrivande commit-meddelande på svenska"
```

3. Pusha till din fork:
```bash
git push origin feature/min-nya-funktion
```

4. Skapa en Pull Request mot main-branchen

### Commit-meddelanden

- Skriv på svenska
- Använd presens ("Lägger till" inte "Lade till")
- Första raden: kortfattad sammanfattning (max 50 tecken)
- Följt av tom rad och detaljerad beskrivning vid behov

Exempel:
```
Lägger till automatisk återanslutning för MQTT

- Implementerar exponentiell backoff
- Lägger till max antal försök
- Förbättrar felmeddelanden
```

## Rapportera buggar

När du rapporterar en bugg, inkludera:

1. **Beskrivning**: Vad som hände och vad du förväntade dig
2. **Steg för att återskapa**: Detaljerade steg
3. **Miljö**:
   - Raspberry Pi-modell
   - OS-version
   - Python-version
   - Relevanta konfigurationsinställningar (utan känslig info)
4. **Loggar**: Relevanta loggrader (ta bort känslig information)
5. **Screenshots**: Om tillämpligt

## Föreslå nya funktioner

För nya funktioner, öppna först en issue för diskussion:

1. Beskriv funktionen och varför den behövs
2. Förklara hur den skulle fungera
3. Diskutera eventuella alternativ du övervägt
4. Vänta på feedback innan du börjar implementera

## Områden som behöver hjälp

- [ ] Enhetstester
- [ ] Integration med fler n8n-arbetsflöden
- [ ] Stöd för fler språk
- [ ] Performance-optimeringar
- [ ] Dokumentationsförbättringar
- [ ] Exempel på n8n-flöden

## Frågor?

Öppna en issue med taggen "question" om du har frågor.

Tack för ditt bidrag! 🎉
