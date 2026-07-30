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

## Präsentationen

- `create_pptx` baut eine fertige **PowerPoint-Datei (.pptx)** im 16:9-Format
- Layouts: `title`, `bullets`, `cards`, `stat`, `two_columns`, `image`, `quote`,
  `timeline`, `closing` — inklusive Sprechernotizen
- Elf Farbwelten (`midnight`, `ocean`, `forest`, `sage`, `teal`, `coral`, `terracotta`,
  `berry`, `cherry`, `charcoal`, `gold`), passend zum Thema gewählt
- Der Skill `powerpoint` gibt Aufbau, Layoutwahl und Checkliste vor
- `read_pptx` liest vorhandene Präsentationen samt Notizen zum Zusammenfassen

## Jon Code

- Der geöffnete Projektordner ist der einzige Arbeitsbereich: Datei-Tools sind darauf
  begrenzt, Shell-Befehle starten darin, und ein `cd` nach draußen wird blockiert
- Im Code-Modus stehen nur Projekt-Werkzeuge bereit (Dateien, Suche, Shell, Git, Web)
- „Schreib mir in index.html …" → Jon findet die Datei, kennt ihren Inhalt und ändert
  genau sie; ohne Dateinamen gilt die im Editor geöffnete Datei
- Fertiger Code landet in der Datei statt im Chat; ungespeicherte Änderungen werden vor
  dem Senden gespeichert, der Editor lädt danach neu
- Design-Vorgabe für alles Sichtbare: modernes Liquid Glass (Tokens, Blur, Hell/Dunkel,
  Fokus-Zustände, reduzierte Bewegung) statt grauem Standard

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
- Der Online-Koop hat eigene Ports (8760 Browser, 8759 ECHO/AETHERIA, UDP 8761 für die
  Lobby-Suche), die im Netzwerk offen sind — ohne dass Chat, Dateien oder PC-Steuerung
  (8756) das Gerät verlassen
- Im Heimnetz genügt der Freundschaftscode: Kennt das Jon des Gastes den Code nicht,
  sucht es den Gastgeber per Broadcast und leitet den Spieler direkt dorthin weiter
  (`redirect`); fehlende Firewall-Regeln legt ein Knopf in der Lobby an
- Jon beenden schließt auch das Backend — über `POST /api/system/shutdown` auch dann,
  wenn es aus `start-jon.bat` oder dem Autostart kam und die App es nicht selbst
  gestartet hat; ein Parent-Watchdog (`JON_PARENT_PID`) fährt es selbst dann herunter,
  wenn die App abstürzt

## Auto-Update & Installer

- `/update` und Update-Knopf erkennen, wie Jon installiert ist:
  - **Installer-Version**: lädt `Jon-Setup.exe` aus dem GitHub-Release mit
    Fortschrittsanzeige nach `DATA_DIR/updates/`, prüft Größe und Dateityp, fragt einmal
    nach, schließt Jon und installiert. Danach startet Jon von selbst wieder; Chats,
    Konten und Einstellungen bleiben unberührt.
  - **Quellcode-Version**: Backup von `data/`, `git pull`, bedingtes `pip`/`npm`,
    Neustart (auf dem Pi `systemctl restart jon`)
- Angeboten wird immer nur eine Version, für die es auch ein fertiges
  Installationsprogramm gibt — nie ein Update, das dieselbe Version noch einmal einspielt
- `python scripts/build_installer.py`: PyInstaller-Bundle (`jon-backend.exe`) + NSIS → `Jon-Setup.exe` + portable `Jon-Windows.zip`,
  ohne Python/Node/Terminal beim Endnutzer

## Sprachen

- Umschalter Deutsch/English im Zahnrad-Menü steuert Oberfläche (i18n) und Jons
  Antwortsprache; englische `README.en.md`

## Mini Jon lebendig

- Tanzt zur Musik (Spotify/Amazon), färbt sich in Song-Farbe, wird bei Stopp normal
- Trink- & Steh-Erinnerungen alle 90 Minuten (abschaltbar)
- Pomodoro-Coach: Timer-Badge, fröhlich in Pausen, Bewegungstipps
- Vorlese-Modus: markierten Text mit Strg+Alt+V vorlesen lassen

## Spiele

- **Werkzeuge → Spiele** (`/spiele`) — Übersicht mit Vorschaubild, Beschreibung, Steuerung,
  Version und Status (bereit, läuft, wird gebaut, Fehler); gestartet wird erst per Klick
- **ECHO** (`/echo`) — First-Person-Psychological-Horror, 4 Etagen, 464 Räume, adaptive
  Regie, fünf Enden; startet als eigenes Fenster, Jon bleibt offen
- **AETHERIA** (`/aetheria`) — Fantasy-Open-World-RPG mit sechs Dörfern, Aufträgen,
  Stufenaufstieg, Tag/Nacht und Weltkarte
- **Blockwelt** (`/spiel`) — Voxel-Sandbox im Browser-Tab, Jon baut auf Zuruf (Taste T)
- **Eigene Spiele nachrüsten** — Ordner mit `jon-spiele.json` neben Jon (oder in `games/`)
  legen: Titel, Beschreibung, Icon, Vorschaubild, Exe, Startparameter und optionales
  Bau-Skript; Jon findet ihn beim nächsten Öffnen der Liste ohne Code-Änderung
- **Fehlerfall** — fehlt die Spieldatei oder bricht der Start ab, erscheint eine Meldung
  in der Karte (inkl. Hinweis auf `echo.log`), Jon läuft unbeeindruckt weiter

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

## Privater Browser

- Öffnet als eingebettetes Fenster in der App (Werkzeuge → 🕶️, `/privat`, Strg+Alt+P);
  „↗ Eigenes Fenster" öffnet ihn in der Desktop-App zusätzlich als eigenes Fenster
- Tabs, Adress-/Suchleiste (DuckDuckGo), Strg+T/W/L/R, Strg+Tab
- Reine In-Memory-Session: kein Verlauf, keine Cookies, kein Cache auf der Platte
- Beim Schließen und per „Spuren löschen" wird alles sofort gewischt
- Berechtigungsanfragen automatisch abgelehnt, Popups öffnen als Tab
- Keine Anmeldung, kein Konto — komplett lokal und privat
- **Auch auf dem Raspberry Pi / in der Web-App**: unter Werkzeuge im selben eingebetteten
  Fenster (sobald die Web-App gebaut ist, was `pi-update.sh` jetzt automatisch erledigt)
  und jederzeit direkt unter `http://<IP>:8756/privat` — diese Seite braucht keinen Build.
  Seiten laufen über den Jon-Proxy (`/api/private/proxy`, umgeht Frame-Sperren, speichert
  nichts, blockt interne Adressen gegen SSRF)
- **Mini Jon** öffnet ihn auf Zuruf („öffne den privaten Browser")

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
