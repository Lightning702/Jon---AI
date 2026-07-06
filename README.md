# Jon — KI-Desktop-Assistent

Jon ist ein moderner KI-Desktop-Assistent für Windows mit Multi-Provider-Unterstützung,
Streaming, Langzeit-Persistenz und Systemsteuerung. Backend in Python/FastAPI, Frontend in
Electron + React + TypeScript im Black/Gold-Glassmorphism-Design.

**Website & Download: [https://getjon.netlify.app](https://getjon.netlify.app)**

## Jon herunterladen

Der einfachste Weg zu Jon führt über die offizielle Website:

1. Öffne **[https://getjon.netlify.app](https://getjon.netlify.app)**
2. Klicke auf **Download** — du erhältst die Datei `jon.zip`
3. Entpacke die Zip-Datei an einen Ort deiner Wahl (z. B. `C:\Jon`)
4. Folge danach der [Setup-Anleitung](#setup) weiter unten
5. Nach dem Setup startet ein Doppelklick auf `start-jon.bat` Backend und App zusammen

Alternativ kannst du das Repository direkt klonen:

```bash
git clone https://github.com/Lightning702/Jon---AI.git
```

**Voraussetzungen:** Windows 10/11, [Python](https://www.python.org/downloads/) 3.12 oder
neuer und [Node.js](https://nodejs.org/) 20 oder neuer.

**Ohne Installation:** Die Handy-App läuft direkt im Browser unter
[https://getjon.netlify.app/app](https://getjon.netlify.app/app/) — API-Key eintragen und loslegen,
auf dem Smartphone über „Zum Startbildschirm hinzufügen" installierbar.

## Funktionen (aktueller Stand)

- Multi-Provider-Chat mit einheitlicher Schnittstelle: NVIDIA, OpenAI, Anthropic, Gemini,
  Ollama, DeepSeek, GLM, Qwen, Mistral
- Echtes Token-Streaming (Server-Sent Events), inkl. separatem Denkprozess (`reasoning_content`)
- Modell- und Providerwechsel zur Laufzeit
- Konfigurations- und API-Key-Verwaltung ausschließlich über Umgebungsvariablen / `.env`
- SQLite-Langzeitgedächtnis für Unterhaltungen (SQLAlchemy)
- Systemsteuerung: PowerShell, CMD, Programme starten/schließen, Explorer, Dateien
  lesen/schreiben/verschieben/löschen, URLs öffnen, VS Code öffnen
- Electron-Desktop-Shell mit rahmenlosem Fenster und Premium-UI

## Architektur

```
Jon/
├── backend/                  FastAPI-Backend (Clean Architecture)
│   └── app/
│       ├── core/             Konfiguration + Key-Manager
│       ├── providers/        Einheitliche LLM-Provider-Abstraktion
│       ├── db/               SQLAlchemy-Modelle + Session
│       ├── services/         Chat- und System-Services
│       ├── api/              FastAPI-Routen
│       └── main.py           App-Factory + Uvicorn-Entrypoint
├── frontend/                 Electron + Vite + React + TypeScript
│   ├── electron/             Main- und Preload-Prozess
│   └── src/                  React-UI (Components, Lib)
├── .env.example              Vorlage für Umgebungsvariablen
└── data/                     SQLite-Datenbank (jon.db)
```

Die Provider implementieren alle `LLMProvider` (`app/providers/base.py`). OpenAI-kompatible
Dienste (NVIDIA, OpenAI, DeepSeek, GLM, Qwen, Mistral, Ollama) laufen über
`OpenAICompatibleProvider`; Anthropic und Gemini haben eigene Adapter. Die `ProviderRegistry`
baut alle Provider aus der Konfiguration und aktiviert nur solche mit vorhandenem Key.

## Setup

### 1. Umgebungsvariablen

```bash
cp .env.example .env
```

Trage deine API-Keys in `.env` ein. **Keys gehören niemals in den Quellcode.**
Beispiel:

```
NVIDIA_API_KEY=nvapi-...
DEFAULT_PROVIDER=nvidia
DEFAULT_MODEL=openai/gpt-oss-120b
```

### 2. Backend

```bash
cd backend
python -m pip install -r requirements.txt
python -m app.main
```

Das Backend läuft auf `http://127.0.0.1:8756`. API-Docs: `http://127.0.0.1:8756/docs`.

### 3. Frontend

```bash
cd frontend
npm install
npm run dev
```

`npm run dev` startet Vite und Electron zusammen. Alternativ `npm run build` für einen
Produktions-Build und `npm run package` für ein Windows-Installationspaket (electron-builder).

## API-Überblick

| Methode | Pfad | Beschreibung |
|---------|------|--------------|
| GET  | `/api/health` | Status + verfügbare Provider |
| GET  | `/api/providers` | Provider inkl. konfigurierter Keys und Modelle |
| GET  | `/api/providers/{name}/models` | Modelle eines Providers |
| POST | `/api/chat` | Streaming-Chat (SSE) |
| GET  | `/api/conversations` | Alle Unterhaltungen |
| GET  | `/api/conversations/{id}` | Unterhaltung mit Nachrichten |
| DELETE | `/api/conversations/{id}` | Unterhaltung löschen |
| POST | `/api/system/powershell` | PowerShell-Befehl ausführen |
| POST | `/api/system/cmd` | CMD-Befehl ausführen |
| POST | `/api/system/open-url` | URL im Browser öffnen |
| POST | `/api/system/start-program` | Programm starten |
| POST | `/api/system/kill-program` | Programm beenden |
| POST | `/api/system/explorer` | Explorer öffnen |
| POST | `/api/system/files/*` | list / read / write / move / delete |
| POST | `/api/system/vscode` | Pfad in VS Code öffnen |

## Sicherheit

- API-Keys werden ausschließlich aus Umgebungsvariablen geladen.
- `.env` und der komplette `data/`-Ordner sind über `.gitignore` ausgeschlossen.
- Die System-Routen führen Befehle mit den Rechten des angemeldeten Benutzers aus und sind
  nur an `127.0.0.1` gebunden. Für ein öffentliches Deployment ist eine Authentifizierungs-
  schicht erforderlich.
