# ziotackus

Bot Telegram privato che monitora i link in una chat di gruppo e moralizza chiunque riposti qualcosa già condiviso in precedenza. Gira su Docker e riconosce intelligentemente varianti equivalenti dello stesso URL per YouTube, Instagram, Facebook e 9gag.

## Prerequisiti

- [Docker](https://docs.docker.com/get-docker/) e Docker Compose installati sul Raspberry Pi
- Un bot Telegram creato tramite [@BotFather](https://t.me/BotFather)
- Il **Chat ID** del gruppo in cui verrà aggiunto il bot

## Configurazione

### 1. Crea il bot su Telegram

1. Apri [@BotFather](https://t.me/BotFather) su Telegram
2. Invia `/newbot` e segui le istruzioni
3. Copia il **token** che ti viene fornito

### 2. Trova il Chat ID del tuo gruppo

Il modo più semplice:
1. Aggiungi temporaneamente [@userinfobot](https://t.me/userinfobot) al gruppo
2. Scrivi qualcosa nel gruppo — il bot risponderà con il Chat ID (un numero negativo tipo `-1001234567890`)
3. Rimuovi @userinfobot dal gruppo

In alternativa, avvia ziotackus senza `ALLOWED_CHAT_ID` configurato: vedrà arrivare il messaggio e lo loggerà con `LOG_LEVEL=DEBUG`.

### 3. Crea il file `.env`

```bash
cp .env.example .env
```

Modifica `.env` con i tuoi valori:

```env
BOT_TOKEN=1234567890:ABCdefGHIjklMNOpqrSTUvwxYZ
ALLOWED_CHAT_ID=-1001234567890
```

## Build e avvio

```bash
# Prima volta (o dopo modifiche al codice)
docker compose up -d --build

# Solo riavvio (senza rebuild)
docker compose up -d

# Visualizza i log in tempo reale
docker compose logs -f

# Ferma il bot
docker compose down
```

Il database SQLite viene persistito nel volume Docker `db_data` — non viene perso al riavvio o al rebuild.

## Seeding della cronologia esistente

La Telegram Bot API non permette ai bot di leggere i messaggi passati. Per importare i link già postati nel gruppo prima dell'installazione del bot, usa lo script di seeding.

### Esportare la chat da Telegram Desktop

1. Apri **Telegram Desktop**
2. Vai nel gruppo → menu `⋮` → **Esporta cronologia chat**
3. Imposta:
   - Formato: **JSON**
   - Seleziona solo **Messaggi di testo** (deseleziona foto, video, ecc. — non servono)
4. Clicca **Esporta** — verrà creata una cartella con un file `result.json`

### Eseguire lo script di seeding

**In locale** (con Python e dipendenze installate):

```bash
.venv\Scripts\activate  # Windows
# oppure: source .venv/bin/activate  (Linux/Mac)

python seed_from_export.py \
  --export /path/to/result.json \
  --chat-id -1001234567890 \
  --db data/ziotackus.db
```

**Dentro Docker** (se il container è già in esecuzione):

```bash
# Copia il file di export nel container
docker cp /path/to/result.json ziotackus:/app/result.json

# Esegui lo script
docker exec ziotackus python seed_from_export.py \
  --export result.json \
  --chat-id -1001234567890 \
  --db data/ziotackus.db
```

Lo script stampa un riepilogo al termine:

```
Seeding completato!
  Link unici importati : 347
  Duplicati trovati    : 23
  Messaggi saltati     : 5
```

> **Nota**: lo script usa le date dell'export Telegram, ma non ha accesso agli username degli utenti (l'export contiene solo il nome visualizzato). Gli username verranno aggiornati automaticamente man mano che quei membri postano nuovi link dopo l'attivazione del bot.

## Comandi disponibili

| Comando | Descrizione |
|---|---|
| `/start` | Presentazione del bot e lista comandi |
| `/stats` | Classifica di tutti i membri per numero di link postati |
| `/hall_of_shame` | Podio dei copincollatori seriali con percentuali |

## Aggiornamenti

```bash
git pull
docker compose up -d --build
```

Il volume con il database non viene toccato durante il rebuild.

## Note per Raspberry Pi 4

- L'immagine `python:3.11-slim` ha una versione ARM64 ufficiale — nessuna compilazione cross-platform necessaria.
- Il bot usa **polling**, non webhook: non è necessario configurare DuckDNS, certificati TLS o port forwarding per il funzionamento del bot stesso.
- DuckDNS e port forwarding restano utili solo se vuoi esporre altri servizi dal Raspberry Pi.
- Il database SQLite è salvato in un volume Docker (`db_data`) — sopravvive a `docker compose down` e rebuild.

## Struttura del progetto

```
bot/
├── app.py          — wiring del bot (handler registration, polling)
├── config.py       — lettura variabili d'ambiente
├── database.py     — tutto il SQL (schema + query)
├── normalizer.py   — estrazione e normalizzazione URL
├── messages.py     — pool messaggi italiani e helper
└── handlers/
    ├── filters.py  — AllowedChatFilter (whitelist chat)
    ├── message.py  — rilevamento duplicati sui messaggi
    ├── commands.py — /stats, /hall_of_shame, /start
    └── member.py   — messaggio di benvenuto al join
seed_from_export.py — import cronologia da export JSON Telegram
```
