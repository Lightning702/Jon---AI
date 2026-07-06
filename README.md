# Jon — KI-Desktop-Assistent

Jon ist ein moderner KI-Desktop-Assistent für Windows mit Multi-Provider-Unterstützung,
Streaming, Langzeit-Persistenz, echter Systemsteuerung, Maus-/Tastatur-Automatisierung,
Sprachsteuerung, einem bearbeitbaren Skill-System und einer eigenständigen Handy-App.
Backend in Python/FastAPI, Frontend in Electron + React + TypeScript im
Black/Gold-Glassmorphism-Design. (Claude hat es nur veröffentlicht, weil ich nicht wusste
wie das geht. Er hat auch bisschen geholfen.)

**Website & Download: [https://getjon.netlify.app](https://getjon.netlify.app)**

---

## Inhalt

- [Jon herunterladen](#jon-herunterladen)
- [Funktionen](#funktionen)
- [Was Jon steuern kann (Tools)](#was-jon-steuern-kann-tools)
- [Skills](#skills)
- [Konten & Modelle](#konten--modelle)
- [Nutzung /usage](#nutzung-usage)
- [Handy-App](#handy-app)
- [Setup](#setup)
- [Dokumentation](#dokumentation)
- [Sicherheit](#sicherheit)

---

## Jon herunterladen

Der einfachste Weg zu Jon führt über die offizielle Website:

1. Öffne **[https://getjon.netlify.app](https://getjon.netlify.app)**
2. Klicke auf **Download** — du erhältst die Datei `jon.zip`
3. Entpacke die Zip-Datei an einen Ort deiner Wahl (z. B. `C:\Jon`)
4. Folge danach der [Setup-Anleitung](#setup) weiter unten
5. Nach dem Setup startet ein Doppelklick auf `start-jon.bat` Backend und App zusammen

Alternativ das Repository direkt klonen:

```bash
git clone https://github.com/Lightning702/Jon---AI.git
```

**Voraussetzungen:** Windows 10/11, [Python](https://www.python.org/downloads/) 3.12 oder
neuer und [Node.js](https://nodejs.org/) 20 oder neuer.

**Ohne Installation:** Die Handy-App läuft direkt im Browser unter
[https://getjon.netlify.app/app](https://getjon.netlify.app/app/).

---

## Funktionen

- **Multi-Provider-Chat** mit einheitlicher Schnittstelle: NVIDIA, OpenAI, Anthropic,
  Gemini, Ollama, DeepSeek, GLM, Qwen, Mistral
- **Echtes Token-Streaming** (Server-Sent Events), inklusive separatem Denkprozess
  (`reasoning_content`)
- **Modell- und Providerwechsel** zur Laufzeit; automatische Modell-Erkennung pro Anbieter
- **Großes Antwortlimit** (bis 32.768 Tokens) mit automatischer Anpassung an Modellgrenzen
- **Echtes Tool-/Function-Calling** — Jon steuert den PC wirklich (siehe unten)
- **Freigabe-Modus**: „Zuerst fragen" (Standard) oder „Alles erlauben", dauerhaft gespeichert
- **Aufklappbare Tool-Anzeige**: jede Aktion zeigt auf Klick den genauen Befehl und eine
  kurze Erklärung
- **Maus-/Tastatur-Automatisierung** über PyAutoGUI (Multi-Monitor)
- **Sprachsteuerung** mit Wake-Word „Jon" und Text-to-Speech-Antworten
- **Langzeitgedächtnis**: Jon merkt sich Fakten über alle Unterhaltungen hinweg
- **Skill-System**: bearbeitbare Markdown-Anleitungen (z. B. Web-Design)
- **Konten-Bereich**: Provider offiziell per API-Key verbinden, Modelle wählen
- **Nutzungs-Übersicht** `/usage`: real gemessene Tokens, Anfragen, Antwortzeiten
- **Handy-App (PWA)**: Chat, Apps öffnen, Teilen, Vorlesen, Spracheingabe, Bildanalyse
- **Website & Netlify-Deployment** inklusive Handy-Proxy für NVIDIA

---

## Was Jon steuern kann (Tools)

Jon ruft echte Funktionen auf dem PC auf. Jede Aktion ist im Chat als Chip sichtbar und
auf Klick aufklappbar (Befehl + Erklärung + Ergebnis).

| Bereich | Tools |
|---------|-------|
| Shell | `run_powershell`, `run_cmd` |
| Programme | `start_program`, `kill_program`, `open_url`, `open_in_vscode` |
| Dateien | `list_dir`, `read_file`, `write_file`, `append_file`, `move_path`, `copy_path`, `delete_path`, `make_dir`, `search_files` |
| Archive | `zip_paths`, `unzip` |
| System | `system_info`, `list_processes`, `lock_screen`, `open_explorer` |
| Zwischenablage | `clipboard_get`, `clipboard_set` |
| Bildschirm | `screenshot`, `get_screen_info` |
| Web | `http_get`, `download_file` |
| Maus/Tastatur | `mouse_move`, `mouse_click`, `mouse_scroll`, `keyboard_type`, `keyboard_press`, `keyboard_hotkey` |
| Fenster | `list_windows`, `focus_window`, `wait` |
| Gedächtnis | `remember`, `recall`, `forget` |
| Skills | `list_skills`, `read_skill`, `write_skill` |

Standardmäßig fragt Jon vor jeder Aktion um Erlaubnis. Reine Abfragen (Systeminfo, Fenster
auflisten, Skill lesen, Erinnerung abrufen) laufen ohne Rückfrage. Der Modus ist im
Zahnrad-Menü umstellbar. Alle Tools sind in [docs/API.md](docs/API.md) dokumentiert.

---

## Skills

Skills sind **bearbeitbare Markdown-Anleitungen** im Ordner `skills/`. Jon liest die
passende Anleitung, bevor er eine Aufgabe startet, und folgt ihr. Du kannst sie in der App
(Konten → Skills), in jedem Texteditor oder direkt in der entpackten ZIP bearbeiten.

Mitgeliefert:

- **web-design** — wie Jon moderne, responsive Websites baut
- **pc-automation** — zuverlässige Maus-/Tastatur-Steuerung
- **research** — sauberes Nachschlagen und Zusammenfassen

Mehr dazu in [docs/SKILLS.md](docs/SKILLS.md).

---

## Konten & Modelle

Im Bereich **Konten** (Personen-Symbol oben rechts) verbindest du Anbieter über den
**offiziellen API-Key**. Jon erkennt danach automatisch alle verfügbaren Modelle und du
wählst dein Standardmodell.

> **Transparenz:** Ein Login mit einem ChatGPT-Plus- oder Claude-Pro-*Abo*, der die
> Abo-Tokens nutzt, wird von OpenAI und Anthropic offiziell **nicht** für Drittanbieter
> angeboten. Jon nutzt deshalb ausschließlich den offiziellen API-Zugang. Angaben wie
> Tarif oder Profilbild liefern die offiziellen APIs nicht — Jon zeigt dann ehrlich
> „Über die offizielle API nicht verfügbar" statt Daten zu erfinden. Die Architektur ist
> modular und für spätere offizielle Konto-Verknüpfungen vorbereitet.

---

## Nutzung /usage

Tippe **`/usage`** im Chat (oder öffne Konten → Nutzung). Jon zeigt real gemessene Werte
aus den offiziellen API-Antworten:

- Prompt-Tokens, Completion-Tokens, Gesamt-Tokens
- Anzahl der Anfragen, durchschnittliche Antwortzeit
- verwendetes Modell, Zeitpunkt der letzten Anfrage

Kosten, Rate-Limits und Restkontingent geben die meisten APIs nicht direkt aus — diese
Felder werden nicht erfunden.

---

## Handy-App

Die PWA unter [getjon.netlify.app/app](https://getjon.netlify.app/app/) läuft ohne
Installation und speichert deinen Key nur lokal! Sie kann:

- mit jedem Provider chatten (eigener API-Key)
- **Apps öffnen** (WhatsApp, YouTube, Maps, Spotify, Kamera … per offiziellen Deep-Links)
- über das **Teilen-Menü** teilen (Web Share API)
- Antworten **vorlesen** (Text-to-Speech) und per **Spracheingabe** zuhören
- **Bilder analysieren** (Foto anhängen → Vision-Modell)
- Standort und Uhrzeit abfragen

Android schränkt aus Sicherheitsgründen den Zugriff auf Kontakte, Nachrichten und fremde
Dateien im Browser ein. Jon nutzt dann die bestmögliche offizielle Alternative (z. B. die
App per Deep-Link öffnen) und sagt ehrlich, was nicht geht. Details in
[docs/ANDROID.md](docs/ANDROID.md).

---

## Setup

### 1. Umgebungsvariablen

```bash
cp .env.example .env
```

Trage deine API-Keys in `.env` ein. **Keys gehören niemals in den Quellcode.** Alternativ
verbindest du Anbieter zur Laufzeit im Konten-Bereich.

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

Backend: `http://127.0.0.1:8756` — API-Docs: `http://127.0.0.1:8756/docs`.

### 3. Frontend

```bash
cd frontend
npm install
npm run dev
```

`npm run dev` startet Vite und Electron zusammen. `npm run build` erzeugt einen
Produktions-Build, `npm run package` ein Windows-Paket (electron-builder).

Details und Fehlerbehebung: [docs/DEVELOPMENT.md](docs/DEVELOPMENT.md).

---

## Dokumentation

| Dokument | Inhalt |
|----------|--------|
| [docs/FEATURES.md](docs/FEATURES.md) | Vollständige Funktionsliste |
| [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) | Architekturübersicht |
| [docs/API.md](docs/API.md) | Komplette API- und Tool-Referenz |
| [docs/SKILLS.md](docs/SKILLS.md) | Skill-/Plugin-Dokumentation |
| [docs/ANDROID.md](docs/ANDROID.md) | Handy-App im Detail |
| [docs/DEVELOPMENT.md](docs/DEVELOPMENT.md) | Entwicklerhandbuch |
| [docs/EXAMPLES.md](docs/EXAMPLES.md) | Beispiele & Rezepte |
| [docs/ROADMAP.md](docs/ROADMAP.md) | Roadmap |
| [docs/FAQ.md](docs/FAQ.md) | Häufige Fragen |
| [CHANGELOG.md](CHANGELOG.md) | Änderungsverlauf |

---

## Sicherheit

- API-Keys werden aus Umgebungsvariablen oder dem lokalen Konten-Speicher (`data/`) geladen,
  niemals aus dem Quellcode.
- `.env` und der komplette `data/`-Ordner sind über `.gitignore` ausgeschlossen.
- Die System- und Tool-Aktionen laufen mit den Rechten des angemeldeten Benutzers. Der
  Standardmodus „Zuerst fragen" verlangt vor jeder Aktion eine Freigabe.
- Das Backend ist nur an `127.0.0.1` gebunden. Für ein öffentliches Deployment ist eine
  Authentifizierungsschicht erforderlich.
