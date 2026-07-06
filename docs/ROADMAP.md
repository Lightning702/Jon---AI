# Roadmap

Stand: Juli 2026. Reihenfolge ohne feste Termine.

## Erledigt

- [x] Multi-Provider-Chat mit Streaming
- [x] Echtes Tool-/Function-Calling (PC-Steuerung)
- [x] Maus-/Tastatur-Automatisierung
- [x] Sprachsteuerung + Text-to-Speech
- [x] Langzeitgedächtnis
- [x] Freigabe-Modus (Zuerst fragen / Alles erlauben)
- [x] Aufklappbare Tool-Anzeige mit Befehl und Erklärung
- [x] Erweiterte Tools (Dateien, Archive, System, Web, Zwischenablage, Screenshot)
- [x] Bearbeitbares Skill-System inkl. Web-Design
- [x] Konten-Bereich (offizieller API-Key) mit Modell-Erkennung
- [x] Nutzungs-Übersicht `/usage`
- [x] Handy-App mit Apps öffnen, Teilen, Vorlesen, Sprache, Bildanalyse

## Als Nächstes

- [ ] RAG / Dokumenten-Wissensbasis (PDF, Web, Notizen)
- [ ] MCP-Anbindung (externe Tool-Server)
- [ ] LangGraph-basierte Mehrschritt-Agenten
- [ ] Lokales Whisper (STT) und Piper (TTS) ohne Internet
- [ ] PDF- und Bildanalyse im Desktop-Client
- [ ] Native Android-App mit offiziell erlaubten Intents
- [ ] Installer/Auto-Updater, Code-Signing
- [ ] CI/CD, Docker, breitere Testabdeckung

## Vorbereitet, aber abhängig von offiziellen APIs

- [ ] Konto-Verknüpfung per offiziellem OAuth (sobald Anbieter das für Drittanbieter
      anbieten). Die Architektur ist modular dafür vorbereitet; aktuell nutzt Jon
      ausschließlich den offiziellen API-Key.
- [ ] Kosten-/Rate-Limit-Anzeige in `/usage`, sobald die APIs diese Werte liefern.
