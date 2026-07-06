# Changelog

Alle nennenswerten Änderungen an Jon.

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
