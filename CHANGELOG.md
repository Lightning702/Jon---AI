# Changelog

Alle nennenswerten Änderungen an Jon.

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
