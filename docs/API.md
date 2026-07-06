# API- & Tool-Referenz

Basis-URL: `http://127.0.0.1:8756`. Interaktive Docs: `/docs`.

## Chat & Konversationen

| Methode | Pfad | Beschreibung |
|---------|------|--------------|
| GET | `/api/health` | Status, Standardprovider/-modell, verfügbare Provider |
| GET | `/api/providers` | Provider inkl. konfigurierter Keys und Modelle |
| GET | `/api/providers/{name}/models` | Modelle eines Providers |
| POST | `/api/chat` | Streaming-Chat (SSE) |
| POST | `/api/chat/approve` | Tool-Freigabe (`{id, approved}`) |
| GET | `/api/conversations` | Alle Unterhaltungen |
| GET | `/api/conversations/{id}` | Unterhaltung mit Nachrichten |
| DELETE | `/api/conversations/{id}` | Unterhaltung löschen |

### `POST /api/chat`

```json
{
  "messages": [{ "role": "user", "content": "Hallo" }],
  "provider": "nvidia",
  "model": "openai/gpt-oss-120b",
  "tool_mode": "ask",
  "persist": true
}
```

SSE-Events: `meta`, `content`, `reasoning`, `tool` (mit `args`, `summary`, optional
`approval_id`), `error`, `done`.

## Skills

| Methode | Pfad | Beschreibung |
|---------|------|--------------|
| GET | `/api/skills` | Alle Skills (Name, Titel, Größe) |
| GET | `/api/skills/{name}` | Skill-Inhalt |
| PUT | `/api/skills/{name}` | Skill anlegen/aktualisieren (`{content}`) |
| DELETE | `/api/skills/{name}` | Skill löschen |

## Konten

| Methode | Pfad | Beschreibung |
|---------|------|--------------|
| GET | `/api/accounts` | Anbieter, Verbindungsstatus, Modelle, Standardmodell |
| POST | `/api/accounts/connect` | Verbinden (`{provider, api_key, default_model?}`) |
| POST | `/api/accounts/{provider}/default-model` | Standardmodell setzen (`{model}`) |
| DELETE | `/api/accounts/{provider}` | Trennen |

Felder wie `plan`, `avatar_url` melden „Über die offizielle API nicht verfügbar", wenn die
API sie nicht liefert.

## Nutzung

| Methode | Pfad | Beschreibung |
|---------|------|--------------|
| GET | `/api/usage` | Nutzung pro Anbieter |
| DELETE | `/api/usage` | Nutzung zurücksetzen (optional `?provider=`) |

## Direkte System-Endpoints

`/api/system/powershell`, `/cmd`, `/open-url`, `/start-program`, `/kill-program`,
`/explorer`, `/files/{list,read,write,move,delete}`, `/vscode`, `/transcribe`.

## Tools (Function Calling)

Jon ruft diese Tools im Chat auf. In Klammern die Pflichtargumente.

### Shell & Programme
- `run_powershell(command)` — PowerShell ausführen
- `run_cmd(command)` — CMD ausführen
- `start_program(path)` — Programm/EXE starten
- `kill_program(name)` — Programm beenden
- `open_url(url)` — URL im Browser
- `open_in_vscode(path)` — Pfad in VS Code

### Dateien & Archive
- `list_dir(path)`, `read_file(path)`, `write_file(path, content)`
- `append_file(path, content)`, `make_dir(path)`
- `move_path(source, destination)`, `copy_path(source, destination)`, `delete_path(path)`
- `search_files(root, pattern)` — rekursiv per Glob
- `zip_paths(sources, destination)`, `unzip(source, destination)`

### System & Bildschirm
- `system_info()`, `list_processes()`, `lock_screen()`, `open_explorer(path)`
- `clipboard_get()`, `clipboard_set(text)`
- `screenshot(path?)` — Datei oder Data-URL
- `get_screen_info()`

### Web
- `http_get(url)` — Text abrufen
- `download_file(url, destination)`

### Maus & Tastatur
- `mouse_move(x, y)`, `mouse_click(...)`, `mouse_scroll(amount)`
- `keyboard_type(text)`, `keyboard_press(key)`, `keyboard_hotkey(keys)`
- `list_windows()`, `focus_window(title)`, `wait(seconds)`

### Gedächtnis & Skills
- `remember(content)`, `recall(query?)`, `forget(query)`
- `list_skills()`, `read_skill(name)`, `write_skill(name, content)`

**Freigabe:** Ohne Rückfrage laufen nur `get_screen_info`, `list_windows`, `wait`,
`recall`, `system_info`, `list_processes`, `list_skills`, `read_skill`. Alle anderen
fragen im Modus „Zuerst fragen" um Erlaubnis.
