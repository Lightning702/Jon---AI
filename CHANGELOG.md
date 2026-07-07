# Changelog

Alle nennenswerten Änderungen an Jon.

## [1.4.1] — 2026-07-07

### Behoben
- **Backend stürzte beim Neustart immer ab („Port 8756 bereits verwendet"):**
  `start-jon.bat` filterte die Portbelegung nach dem englischen Wort „LISTENING" —
  auf deutschem Windows heißt es „ABHÖREN", der alte Prozess wurde also nie beendet.
  Der Port-Kill läuft jetzt sprachunabhängig über PowerShell, und das Backend räumt
  beim Start zusätzlich selbst einen belegten Port frei (alte Instanz wird beendet,
  neue übernimmt).
- Ordner-Dialog in Jon Code: Fehler werden nicht mehr stillschweigend verschluckt —
  wenn kein Dialog erscheinen kann, öffnet sich das manuelle Pfad-Feld.
- Der „Verbunden"-Punkt prüft das Backend jetzt alle 15 Sekunden statt nur beim
  App-Start.

## [1.4.0] — 2026-07-07

### Neu
- **Echter Windows-Wecker:** `set_alarm` legt eine geplante Windows-Aufgabe an, die zur
  Uhrzeit (`time='07:00'`) oder nach Ablauf (`in_minutes=10`) mit Klingelton und Popup
  klingelt — auch wenn Jon geschlossen ist. Dazu `list_alarms` und `delete_alarm`.
- **`REASONING_EFFORT` in `.env`:** steuert, wie lange gpt-oss-Modelle „nachdenken"
  (`low`/`medium`/`high`). Standard `low` — Antworten kommen dadurch um ein Vielfaches
  schneller (gemessen ~0,7s statt ~4s bis zum ersten Token).

### Geändert
- **Konten & Modelle laden deutlich schneller:** `/api/providers` und `/api/accounts`
  fragen alle Anbieter parallel statt nacheinander ab, Modell-Listen werden 5 Minuten
  gecacht und hängende Anbieter nach 6s (`MODELS_TIMEOUT`) übersprungen. Gemini blockiert
  den Server dabei nicht mehr.
- `.env` enthält jetzt alle unterstützten Anbieter (OpenRouter, Groq, Together, xAI,
  Ollama, LM Studio, …) zum direkten Eintragen.
- System-Prompt kennt Wecker/Timer, `ms-settings:`-Deep-Links und die Regel, bereits
  erledigte Aktionen nie zu wiederholen.

### Behoben
- **Backend startete auf neuen Geräten nicht:** `audioop-lts` fehlte in den
  Requirements (Pflicht ab Python 3.13), und ein Fehler beim Import von
  Sprachpaket/PyAutoGUI riss den ganzen Server mit. Beides ist jetzt abgesichert —
  Sprach- und Maussteuerung melden sich sauber ab, statt den Start zu verhindern.
- **`start-jon.bat` deutlich robuster:** erkennt den Windows-Store-Python-Platzhalter,
  nutzt den `py`-Launcher, prüft alle Abhängigkeiten, installiert notfalls mit `--user`,
  schreibt `data\backend.log` und zeigt bei Startfehlern die letzten Log-Zeilen an.
- **Jon wiederholt keine erledigten Aktionen mehr** (z.B. YouTube nach einem „Danke"
  erneut öffnen): Tool-Antworten ohne Text erscheinen im Verlauf jetzt als
  „[Bereits erledigt: …]" bzw. „Erledigt ✅", und der Prompt verbietet Wiederholungen.

## [1.3.0] — 2026-07-07

### Neu
- **Coding-Agent im Terminal (`jon`):** autonomer KI-Coding-Agent für das VS-Code-Terminal
  mit Workspace-Analyse, präzisen Multi-Datei-Änderungen, Build/Test-Schleife und
  vollständigem Slash-Command-System (`/help /clear /status /usage /model /provider
  /agents /tools /memory /plugins /settings`). `/model` und `/provider` wechseln ohne
  Neustart. Installierbar über `pip install -e .` (Konsolen-Befehl `jon`) oder `jon.bat`.
- **Neue Provider:** OpenRouter, Groq, Together AI, xAI (Grok), LM Studio — plus Ollama als
  vollwertige lokale Gratis-Option mit Erreichbarkeits- und Modell-Erkennung.
- **`edit_file`-Tool:** präzise Textersetzung statt ganze Dateien zu überschreiben.
- **Eigenes System-Prompt:** in der App unter Konten → Prompt (ergänzen oder ersetzen).
- **Eigene Skills anlegen/löschen** direkt in der App; neuer **game-design**-Skill
  (2D-Canvas- und 3D-Three.js-Gerüste).
- **Erinnerungen/Loops:** `set_reminder`-Tool und Konten → Erinnerungen. Jon meldet fällige
  Erinnerungen, sobald die App offen ist, per Chat-Nachricht und Browser-Benachrichtigung.

### Hinweis
- Eine Anmeldung mit ChatGPT-/Claude-**Abo** (statt API-Key) bleibt bewusst außen vor: Die
  Anbieter stellen dafür keine offizielle Schnittstelle bereit. Für „gratis" sind Ollama und
  LM Studio (lokal) sowie Free-Tiers (NVIDIA, Gemini, Groq) vorgesehen.
- SMS-Benachrichtigung an eine Telefonnummer ist nicht enthalten (bräuchte einen
  kostenpflichtigen SMS-Dienst); stattdessen offizielle Browser-Benachrichtigungen.

## [1.2.0] — 2026-07-07

### Neu
- **Erweiterte Tools:** `search_files`, `make_dir`, `append_file`, `copy_path`,
  `zip_paths`, `unzip`, `clipboard_get`, `clipboard_set`, `screenshot`, `http_get`,
  `download_file`, `system_info`, `list_processes`, `lock_screen`.
- **Skill-System:** bearbeitbare Markdown-Anleitungen unter `skills/` mit den Tools
  `list_skills`, `read_skill`, `write_skill`. Mitgeliefert: `web-design`, `pc-automation`,
  `research`. Bearbeitbar in der App, per API und als Datei.
- **Konten-Bereich:** Anbieter per offiziellem API-Key verbinden, automatische
  Modell-Erkennung, Standardmodell wählen. Transparente Anzeige, wenn Tarif/Profil offiziell
  nicht verfügbar sind. Endpunkte unter `/api/accounts`.
- **`/usage`:** real gemessene Nutzung (Prompt-/Completion-/Gesamt-Tokens, Anfragen,
  durchschnittliche Antwortzeit, letztes Modell) pro Anbieter. Endpunkt `/api/usage`.
- **Handy-App:** Tool-Loop mit Apps öffnen, Teilen, Vorlesen, Standort, Uhrzeit,
  Web-Abruf; Spracheingabe (Web Speech API); Bildanalyse über Vision-Modelle.
- **Dokumentation:** kompletter `docs/`-Ordner (Features, Architektur, API, Skills,
  Android, Development, Examples, Roadmap, FAQ) und dieser Changelog.

### Geändert
- Antwortlimit auf bis zu 32.768 Tokens erhöht, mit automatischer Halbierung bei
  Modellgrenzen. Anthropic/Gemini erhalten sinnvolle Modell-Fallbacks.
- Provider lösen ihren API-Key jetzt dynamisch auf (env oder verbundenes Konto).
- System-Prompt kennt die neuen Fähigkeiten und Skills.

### Behoben
- Veraltete kompilierte `*.js`/`*.d.ts` aus `frontend/src` entfernt, die im Vite-Build die
  echten `.tsx`-Quellen überschatteten.

## [1.1.0] — 2026-07-06

### Neu
- Freigabe-Modus „Zuerst fragen" (Standard) / „Alles erlauben", dauerhaft gespeichert.
- Aufklappbare Tool-Chips: Befehl, Zusammenfassung und Ergebnis auf Klick.

## [1.0.0] — 2026-07-06

### Neu
- Erste Veröffentlichung: Multi-Provider-Chat, Streaming, Persistenz, PC-Steuerung,
  Maus-/Tastatur-Automatisierung, Sprachsteuerung, Langzeitgedächtnis, Website und
  Handy-App.
