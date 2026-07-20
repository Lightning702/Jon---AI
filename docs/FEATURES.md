# Funktionen

Vollständige Übersicht über den aktuellen Stand von Jon.

## Chat & Modelle

- Multi-Provider: NVIDIA, OpenAI, Anthropic, Gemini, Ollama, DeepSeek, GLM, Qwen, Mistral
- Einheitliche Provider-Abstraktion (`LLMProvider`); OpenAI-kompatible Dienste teilen sich
  einen Adapter, Anthropic und Gemini haben eigene
- Token-Streaming über Server-Sent Events
- Separater Denkprozess (`reasoning_content`) ein-/ausklappbar
- Automatische Modell-Erkennung pro Anbieter (kein Code-Update für neue Modelle nötig)
- Provider- und Modellwechsel zur Laufzeit
- Antwortlimit bis 32.768 Tokens mit automatischer Halbierung bei Modellgrenzen
- Robuste Wiederholung bei transienten 5xx-Fehlern (Backoff)

## Werkzeuge (Function Calling)

- 40+ Tools von Shell über Dateien, Archive, System, Zwischenablage, Screenshot, Web bis
  Maus/Tastatur (siehe [API.md](API.md))
- Agent-Loop mit bis zu 30 Tool-Runden pro Antwort
- Freigabe-Modus „Zuerst fragen" (Standard) / „Alles erlauben", dauerhaft gespeichert
- Aufklappbare Tool-Chips: Befehl, Zusammenfassung, Ergebnis
- Reine Leseaktionen laufen ohne Rückfrage

## Automatisierung

- Maus bewegen/klicken/scrollen, Tastatur tippen/drücken/Kombinationen
- Multi-Monitor-Unterstützung, Koordinaten als Pixel oder Bruchteile 0–1
- Fenster auflisten und fokussieren, Wartezeiten
- Failsafe: Maus in die obere linke Ecke bricht ab

## Sprache

- Wake-Word „Jon" wahlweise offline über openWakeWord im Backend (unter 1 s), mit
  automatischem Fallback auf die Fenster-Erkennung; Empfindlichkeit niedrig/mittel/hoch
- Barge-in: Sprechen während Jon redet stoppt die Ausgabe sofort (Jon und Mini Jon),
  mit Echo-Schutz
- Mikrofon nur offen, wenn wirklich zugehört wird
- Sprache-zu-Text über Google-Erkennung (Backend)
- Text-to-Speech-Antworten (Web Speech API), bevorzugt deutsche männliche Stimme
- Sprach-Kontext im RAM (letzte 12 Turns), ohne Chat-Verlauf zu verändern

## Browser-Automatisierung

- Sichtbares Chromium-Fenster (Playwright), persistente Session pro Chat
- `browser_goto/read/click/fill/screenshot/back/close`
- `browser_read` liefert Text plus interaktive Elemente mit stabilen Selektoren
- Klick/Ausfüllen per Selektor oder sichtbarem Text, 15 s Timeout, klare Fehler
- Chromium wird beim ersten Aufruf automatisch installiert
- Skill `browser-automation.md`: nie Logins/Käufe ohne Bestätigung

## Kalender

- Eigener lokaler Kalender (`data/calendar.json`) mit Monats-/Wochenansicht im
  Black/Gold-Design
- `calendar_add/list/update/delete/search` — Eintragen per Zuruf, Konflikt-Ansage
- Automationen, Erinnerungen und der ICS-Kalender (Google/Outlook, read-only) farblich
  integriert; erledigte Tasks durchgestrichen
- Termine mit Uhrzeit melden sich im Chat und als Browser-Benachrichtigung
- Fließt in Tagesbriefing und Wochenrückblick ein; `/kalender` zeigt 7 Tage

## Vertrauen & Sicherheit

- Papierkorb: Löschen/Überschreiben/Verschieben sichert das Original 30 Tage in
  `data/trash`; `/undo` und `/papierkorb` zum Wiederherstellen
- Aktionsprotokoll aller Tool-Aufrufe mit Quelle; `/log` mit Filter; Abwesenheits-Bericht
  im Briefing
- Mit `JON_LAN=1` ist Jon für Handy und Smartwatch im eigenen WLAN erreichbar

## Auto-Update & Installer

- `/update` und Update-Knopf: Backup von `data/`, `git pull`, bedingtes `pip`/`npm`,
  Neustart (auf dem Pi `systemctl restart jon`)
- `build-installer.bat`: PyInstaller-Bundle (`jon-backend.exe`) + NSIS → `Jon-Setup.exe`,
  ohne Python/Node/Terminal beim Endnutzer

## Sprachen

- Umschalter Deutsch/English im Zahnrad-Menü steuert Oberfläche (i18n) und Jons
  Antwortsprache; englische `README.en.md`

## Mini Jon lebendig

- Tanzt zur Musik (Spotify/Amazon), färbt sich in Song-Farbe, wird bei Stopp normal
- Trink- & Steh-Erinnerungen alle 90 Minuten (abschaltbar)
- Pomodoro-Coach: Timer-Badge, fröhlich in Pausen, Bewegungstipps
- Vorlese-Modus: markierten Text mit Strg+Alt+V vorlesen lassen

## Produktivität & Alltag

- **Fokus-Statistik** (`/fokus`) — lokale App-Zeiten als Balkendiagramm, im Wochenrückblick
- **Automatische Datei-Ablage** — Downloads regelbasiert einsortieren, mit Papierkorb
- **Zwischenablage-Aktionen** — URL/Mail/Telefon/IBAN/Adresse/Code erkannt, passende Aktion
- **Meeting-Mitschrift** (`/meeting`) — System-Ton + Mikrofon (Fifine bevorzugt), live
  transkribiert, Zusammenfassung mit To-dos in den Kalender

## Telegram

- Fotos per Vision-Modell analysieren, Maus/Tastatur direkt steuern
- Lange Sprachnachrichten zusammenfassen + Termine in den Kalender
- Standort-Erinnerungen: benannte Orte + Geofencing über Live-Standort
- Guten-Morgen-Nachricht mit Terminen, Erinnerungen einen Tag vorher
- **Gruppen-Chats**: Jon und Mini Jon lesen in Gruppen still mit (Kontext),
  antworten aber nur bei Erwähnung mit ihrem `@Benutzernamen`; beliebig viele
  Bots harmonieren in derselben Gruppe über einen gemeinsamen Verlauf
  (bei @BotFather `/setprivacy` → Disable, damit die Bots alles mitlesen)
- **Mini Jon als eigener Bot** (eigenes Token): antwortet als Emil; mit
  `/schlafen` schläft er ein und zeigt statt Antworten eine Schlaf-Animation
  mit geschlossenen Augen, `/aufwachen` weckt ihn — der Schlaf-Status gilt
  auch für die Desktop-Figur

## Gedächtnis

- Persistentes Langzeitgedächtnis (SQLite)
- `remember` / `recall` / `forget`
- Automatisches Merken von Merkenswertem
- Fakten fließen in jeden System-Prompt ein

## Skills

- Bearbeitbare Markdown-Anleitungen im Ordner `skills/`
- In der App bearbeitbar (Konten → Skills), per API und als Datei
- Jon liest die passende Anleitung vor der Ausführung

## Konten & Nutzung

- Konten-Bereich: Provider per offiziellem API-Key verbinden
- Automatische Modell-Liste, Standardmodell wählbar
- Transparente Anzeige, wenn Infos offiziell nicht verfügbar sind
- `/usage`: real gemessene Tokens, Anfragen, Antwortzeiten pro Anbieter

## Handy-App (PWA)

- Chat mit eigenem API-Key (nur lokal gespeichert)
- Tool-Loop: Apps öffnen, Teilen, Vorlesen, Standort, Uhrzeit, Web-Abruf
- Spracheingabe (Web Speech API) und Vorlesen
- Bildanalyse über Vision-fähige Modelle
- Installierbar über „Zum Startbildschirm hinzufügen"

## Persistenz & Betrieb

- SQLite über SQLAlchemy, Tabellen werden automatisch angelegt
- Start-Skripte (`start-jon.bat`, `start.ps1`, `start-server.sh`)
- Netlify-Deployment inklusive NVIDIA-Proxy für die Handy-App
