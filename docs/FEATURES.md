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

- Wake-Word „Jon" (auch john/jonny/johnny), armed-Modus
- Sprache-zu-Text über Google-Erkennung (Backend)
- Text-to-Speech-Antworten (Web Speech API), bevorzugt deutsche männliche Stimme
- Sprach-Kontext im RAM (letzte 12 Turns), ohne Chat-Verlauf zu verändern

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
