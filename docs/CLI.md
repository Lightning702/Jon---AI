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

Tipp `jon` — in **jedem** Terminal, und du hast Jon komplett: Windows CMD, PowerShell,
macOS Terminal (zsh/bash), Linux und das integrierte Terminal von VS Code, IntelliJ & Co.

```bash
jon
```

Beim Start begruesst dich Jon mit Logo, Menue und dem Prompt `jon>`. Schreib einfach, was
du willst — der volle Funktionsumfang der App steht bereit: Chat, Code, Dateien, System,
Browser, Projekte, Tools, Gedaechtnis und der Agenten-Modus.

### Einrichten

**Aus dem Download (Setup oder portables Paket) ist nichts zu tun:** Seit 4.53.2 legt Jon
den Befehl beim ersten Start selbst an und traegt den Ordner in den PATH ein. Ein neues
Terminal oeffnen, `jon` tippen — fertig. Die gebuendelte `jon-backend.exe` versteht dafuer
`cli`, `terminal` und `jon` als erstes Wort; zieht die App um oder kommt ein Update, zeigt
der Befehl von selbst auf die neue Fassung. Abschalten: `JON_KEIN_TERMINAL_BEFEHL=1`,
entfernen unter **Zahnrad → Diagnose**.

Von Hand geht es weiterhin ueber **Zahnrad → Jon im Terminal → Einrichten** (Windows:
Nutzer-PATH, macOS/Linux: `~/.local/bin` und die Shell-Profile).

Im Quellcode-Betrieb:

- **Als Befehl installieren:** `cd backend && pip install -e .`
- **Ohne Installation:** im `backend`-Ordner `python -m app.cli` ausfuehren.

### In VS Code

Im integrierten Terminal erkennt Jon den Editor automatisch — VS Code, Cursor,
Windsurf und JetBrains — und startet im **Code-Modus**: Er laedt den Ordner,
analysiert die Struktur und meldet sich mit `Du (code)>`. Auch ohne Editor reicht ein
Projektordner: eine `.git`, eine `package.json`, ein `src/` oder schon eine einzelne
Code-Datei wie `index.html`. Mit `chat` wechselst du in den normalen Chat, mit `code`
zurueck.

```
PS C:\Projekte\Jon-AI> jon
Jon Code-Modus aktiviert!
VS Code erkannt — ich arbeite in C:\Projekte\Jon-AI
Ich analysiere dein Projekt ...
 ✓ Repository geladen (Zweig main)
 ✓ Code-Struktur analysiert (128 Dateien, 14 Verzeichnisse) · Node/JS, Python
 ✓ Bereit fuer deine Aufgabe
Sag einfach, was ich bauen oder aendern soll — ich schreibe direkt in die Dateien.
Du (code)>
```

Im Code-Modus ist der geoeffnete Ordner Jons einziger Arbeitsbereich: Datei-Tools und
Shell-Befehle bleiben darin, und Jon bekommt genau die Projekt-Werkzeuge. Sagst du
„bau mir eine Website“, schreibt er die Dateien und meldet in zwei Saetzen, was er
angelegt hat.

### Direkt fragen

Eine einzelne Frage geht auch ohne Sitzung:

```bash
jon "erklaere mir dieses Projekt"
jon code "behebe alle Type-Fehler"
```

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

## Befehle

Du kannst sie mit oder ohne `/` schreiben. Ohne `/` gilt ein Wort nur als Befehl,
wenn es **allein** steht — „Code mir mit HTML eine Website“ ist also ein Auftrag an
Jon und kein `code`-Befehl. Mit `/` geht beides auf einmal: `/code bau mir ein Menue`
schaltet in den Code-Modus und erledigt den Auftrag gleich mit.

| Befehl | Wirkung |
|--------|---------|
| `hilfe` | Beispiele, Befehle und alles, was Jon im Terminal kann |
| `chat` | in den normalen Chat wechseln |
| `code` | Code-Modus fuer das aktuelle Projekt |
| `projekte` | Projektstruktur anzeigen |
| `tools` | verfuegbare Tools |
| `memory` | Langzeitgedaechtnis |
| `einstellungen` | Anbieter, Modell, Modus, Ordner |
| `modell [n]` | Modelle des Anbieters anzeigen / waehlen — die Wahl bleibt gemerkt |
| `anbieter [name]` | Anbieter anzeigen / waehlen — die Wahl bleibt gemerkt |
| `agent` | Agenten-Modus erklaeren |
| `neu` | Verlauf loeschen |
| `ende` | beenden |

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
