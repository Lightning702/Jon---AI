# Jon Coding-Agent

Jon arbeitet als autonomer Coding-Agent an ganzen Projekten — auf zwei Wegen:

- **In der App („Jon Code"):** Button oben rechts in der Desktop-App. Es öffnet sich eine
  editorartige Ansicht mit **Dateibaum links**, **Code-Editor in der Mitte** und **Jon als
  Agent rechts**, der direkt an deinen Dateien arbeitet (lesen, ändern, Tests laufen lassen).
  „📂 Ordner öffnen" wählt den Projektordner, „VS Code ↗" öffnet ihn zusätzlich extern.
  Im Chat wechselst du mit `/model` und `/provider` ohne Neustart.
- **Im Terminal (`jon`):** unten beschrieben — ideal im integrierten Terminal von VS Code.

Jon ist dabei **kein eigener Editor**, sondern arbeitet in deinem aktuellen Workspace.

## Nur der geöffnete Ordner

Der gewählte Projektordner ist Jons einziger Arbeitsbereich:

- Alle Datei-Tools sind auf ihn begrenzt, Pfade außerhalb werden abgelehnt.
- Shell-Befehle starten immer in ihm; ein `cd ..`, `pushd`, `Set-Location C:\…` oder ein
  anderer Sprung nach draußen wird blockiert, bevor der Befehl läuft.
- Im Code-Modus bekommt Jon nur die Projekt-Werkzeuge (Dateien, Suche, Shell, Git, Web) —
  Mail, Musik, Smarthome, Kalender und Co. sind hier gar nicht erst verfügbar.

## Direkt in die richtige Datei

- **Nennst du eine Datei** („schreib mir in index.html ein Login-Formular"), sucht Jon sie
  im Projektordner, bekommt ihren Inhalt mit und ändert genau diese Datei. Gibt es sie
  noch nicht, legt er sie an.
- **Nennst du keine** („mach den Header schöner"), gilt die Datei, die gerade im Editor
  offen ist — ihr Pfad und Inhalt stehen Jon immer zur Verfügung. Ungespeicherte Änderungen
  werden vor dem Senden automatisch gespeichert.
- Jon gibt fertigen Code **nicht** im Chat aus, sondern schreibt ihn in die Datei und
  fasst in ein bis drei Sätzen zusammen, was er geändert hat. Der Editor lädt danach
  automatisch neu (Strg+Z macht rückgängig).
- Für alles Sichtbare (HTML, CSS, React …) gilt Jons Design-Vorgabe: modernes Liquid
  Glass statt grauem Standard-Formular — außer das Projekt hat schon ein eigenes Design,
  dann fügt er sich dort ein.

## Im Terminal

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

2. **Ohne Installation:** im `backend`-Ordner `python -m app.cli` ausführen.

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

Mit `/provider ollama` arbeitet der Coding-Agent lokal. Er nutzt dieselbe Konfiguration
wie die App — Server, Modell, Context Length und Keep Alive stellst du einmal im
Zahnrad-Menü unter **Ollama** ein (siehe [OLLAMA.md](OLLAMA.md)).

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
