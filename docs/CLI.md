# Jon CLI — Coding-Agent für VS Code

Jon läuft auch als autonomer Coding-Agent direkt im **Terminal** (z. B. im integrierten
Terminal von VS Code) — ähnlich wie moderne KI-Coding-Agenten. Jon ist dabei **kein eigener
Editor**, sondern arbeitet direkt in deinem aktuellen Workspace.

## Starten

Im Projektordner (der Ordner, an dem Jon arbeiten soll):

```bash
jon
```

Zwei Wege, damit `jon` verfügbar ist:

1. **Als Befehl installieren** (empfohlen):
   ```bash
   cd backend
   pip install -e .
   ```
   Danach ist `jon` systemweit im Terminal verfügbar.

2. **Ohne Installation:** die mitgelieferte `jon.bat` (Windows) aufrufen, oder im
   `backend`-Ordner `python -m app.cli`.

## Was Jon im Terminal kann

- Den gesamten Workspace analysieren (Projektstruktur, Projekttyp erkennen)
- Dateien lesen, erstellen, **präzise** ändern (`edit_file` statt Überschreiben),
  verschieben, kopieren, löschen
- Projekte durchsuchen, Abhängigkeiten und APIs verstehen
- Terminalbefehle, Builds und Tests ausführen, Fehler lesen und beheben
- Git verwenden
- Mehrere Dateien in einem Durchlauf bearbeiten
- Selbstständig planen und iterieren, bis die Aufgabe erledigt ist

Jon behält Chatverlauf, Projektstruktur und Gedächtnis über die Sitzung hinweg im Kontext.

## Slash-Befehle

| Befehl | Wirkung |
|--------|---------|
| `/help` | Hilfe |
| `/clear` | Verlauf löschen |
| `/status` | Provider, Modell, Workspace, Nachrichten |
| `/usage` | Nutzung (Tokens, Anfragen, Antwortzeit) |
| `/model [n]` | Modelle des Providers anzeigen / wechseln |
| `/provider [name]` | Provider anzeigen / wechseln |
| `/agents` | Agenten-Modus erklären |
| `/tools` | verfügbare Tools |
| `/memory` | Langzeitgedächtnis |
| `/plugins` | Skills |
| `/settings` | Einstellungen |
| `/exit` | beenden |

`/model` und `/provider` wechseln **ohne Neustart**. Unterstützte Provider:
OpenAI, Anthropic, Gemini, OpenRouter, NVIDIA NIM, Ollama, LM Studio, Groq, Together AI,
DeepSeek, Mistral, xAI (und weitere OpenAI-kompatible).

## Beispiel

```
› Finde alle Type-Fehler im Projekt und behebe sie, dann lass die Tests laufen.
```

Jon durchsucht den Code, ändert die betroffenen Stellen gezielt, startet die Tests, liest
die Ausgabe und iteriert, bis alles grün ist.

## Hinweis zur Sicherheit

Der Coding-Agent führt Tool-Aktionen im Workspace direkt aus (damit er flüssig arbeiten
kann) und zeigt jede Aktion im Terminal an. Nutze ihn in Projektordnern, in denen Jon
arbeiten darf. Für die Desktop-App gilt weiterhin der Freigabe-Modus „Zuerst fragen".
