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

Für Jon Code zusätzlich `"mode": "coding"`, `"workspace": "C:/Projekt"` und optional
`"active_file": "C:/Projekt/index.html"`. Der Workspace begrenzt alle Tools auf diesen
Ordner; `active_file` gibt Jon Pfad und Inhalt der gerade geöffneten Datei mit.

SSE-Events: `meta`, `content`, `reasoning`, `tool` (mit `args`, `summary`, optional
`approval_id`), `error`, `done`.

## Skills

| Methode | Pfad | Beschreibung |
|---------|------|--------------|
| GET | `/api/skills` | Alle Skills (Name, Titel, Größe) |
| GET | `/api/skills/{name}` | Skill-Inhalt |
| PUT | `/api/skills/{name}` | Skill anlegen/aktualisieren (`{content}`) |
| DELETE | `/api/skills/{name}` | Skill löschen (Datei oder Wissensordner) |

Skills sind entweder eine Datei `skills/<name>.md` oder ein Wissensordner
`skills/<name>/` mit `skill.md` als Einstieg. Bei einem Ordner liefert
`GET /api/skills/{name}` zusätzlich `kind: "wissen"` und die Liste der
Wissensdateien.

## Konten

| Methode | Pfad | Beschreibung |
|---------|------|--------------|
| GET | `/api/accounts` | Anbieter, Verbindungsstatus, Modelle, Standardmodell |
| POST | `/api/accounts/connect` | Verbinden (`{provider, api_key, default_model?}`) |
| POST | `/api/accounts/{provider}/default-model` | Standardmodell setzen (`{model}`) |
| DELETE | `/api/accounts/{provider}` | Trennen |

Felder wie `plan`, `avatar_url` melden „Über die offizielle API nicht verfügbar", wenn die
API sie nicht liefert.

## Ollama

| Methode | Pfad | Beschreibung |
|---------|------|--------------|
| GET | `/api/ollama/config` | Alle Ollama-Einstellungen inkl. berechneter `url` |
| PUT | `/api/ollama/config` | Einstellungen ändern (dauerhaft gespeichert) |
| POST | `/api/ollama/reset` | Auf Standardwerte zurücksetzen |
| GET | `/api/ollama/status` | Serverstatus (optional `?force=true`) |
| POST | `/api/ollama/test` | Verbindung sofort testen, optional mit neuen Werten |
| GET | `/api/ollama/models` | Installierte Modelle (optional `?refresh=true`) |
| GET | `/api/ollama/hosts` | Vorschläge: localhost, LAN-, Tailscale-Adresse |

### `PUT /api/ollama/config`

```json
{
  "enabled": true,
  "url": "http://192.168.1.50:11434",
  "model": "llama3.2",
  "temperature": 0.7,
  "top_p": 0.9,
  "top_k": 40,
  "max_tokens": 2048,
  "context_length": 8192,
  "keep_alive": "30m",
  "seed": -1,
  "system_prompt": "",
  "stream": true,
  "timeout": 120,
  "auto_reconnect": true,
  "auto_load_models": true
}
```

Alle Felder sind optional. Statt `url` gehen auch `scheme`, `host` und `port` einzeln.
Ungültige Werte beantwortet die API mit **400** und einer verständlichen Meldung; die
gespeicherte Konfiguration bleibt dabei unverändert.

### `GET /api/ollama/status`

```json
{
  "state": "online",
  "url": "http://127.0.0.1:11434",
  "version": "0.12.0",
  "response_ms": 12,
  "model": "llama3.2",
  "models": ["llama3.2", "qwen2.5:7b"],
  "model_count": 2,
  "last_success": "2026-08-02T20:41:00",
  "error": ""
}
```

`state` ist `online`, `offline` oder `disabled`. Der Chat selbst läuft ganz normal über
`POST /api/chat` mit `"provider": "ollama"`; Jon spricht dabei die offizielle Ollama-API
(`/api/chat`). Ausführliche Anleitung: [OLLAMA.md](OLLAMA.md).

## Ollama-Serverfreigabe

Eigener Server, den andere Jon-Nutzer mitbenutzen dürfen:

| Methode | Pfad | Beschreibung |
|---------|------|--------------|
| GET | `/api/ollama/share` | Freigabe-Einstellungen und verbundene Benutzer |
| PUT | `/api/ollama/share` | `enabled`, `name`, `description`, `visibility` |
| POST | `/api/ollama/share/code` | Neuen Freigabecode erzeugen (alter wird ungültig) |
| POST | `/api/ollama/share/invites` | Einmal-Einladung erstellen (`{label}`) |
| DELETE | `/api/ollama/share/invites/{code}` | Einladung löschen |
| GET | `/api/ollama/share/users` | Verbundene Benutzer mit Status, Modell, Aktivität |
| DELETE | `/api/ollama/share/users/{id}` | Einen Benutzer entfernen (wirkt sofort) |
| POST | `/api/ollama/share/revoke` | Allen Benutzern den Zugriff entziehen |

`visibility` ist `private`, `invited` oder `public`.

Fremde Server, die man selbst nutzt:

| Methode | Pfad | Beschreibung |
|---------|------|--------------|
| GET | `/api/ollama/remote` | Verbundene fremde Server (ohne Token) |
| POST | `/api/ollama/remote` | Verbinden (`{code}`, auch `CODE@host:port` oder `jon://ollama/...`) |
| GET | `/api/ollama/remote/{code}` | Status: online/offline, Antwortzeit, Modelle |
| POST | `/api/ollama/remote/{code}/refresh` | Modell-Liste neu holen |
| DELETE | `/api/ollama/remote/{code}` | Verbindung trennen |

Die Modelle eines verbundenen Servers erscheinen unter dem Anbieter `ollama` als
`share:<CODE>/<modell>` und lassen sich genauso im Chat verwenden.

### Gastgeber-Endpunkte (Port 8758)

Diese laufen im LAN-erreichbaren Chat-Server, **nicht** in der Steuer-API:

| Methode | Pfad | Auth | Beschreibung |
|---------|------|------|--------------|
| GET | `/share/info` | — | Name und Beschreibung, nur wenn freigegeben |
| POST | `/share/join` | Freigabecode | Liefert ein persönliches Zugriffstoken |
| GET | `/share/api/version` | Bearer | Ollama-Version des Gastgebers |
| GET | `/share/api/tags` | Bearer | Installierte Modelle |
| POST | `/share/api/chat` | Bearer | Chat-Stream (NDJSON), reicht an den lokalen Ollama weiter |

Ohne gültiges Token antworten alle `/share/api/*`-Endpunkte mit **401**. Ein Widerruf
beendet auch laufende Streams. `POST /share/api/chat` übernimmt vom Gast nur `model`,
`messages`, `stream`, `tools` und die Sampling-Optionen; `num_ctx` und `num_predict` werden
auf die Werte des Gastgebers gedeckelt, `keep_alive` kommt immer von ihm.

## Jon Maps

| Methode | Pfad | Beschreibung |
|---------|------|--------------|
| GET | `/api/maps/config` | Anbieter, Themes, Ebenen, Fähigkeiten, Kategorien, grober Startort |
| GET | `/api/maps/styles/{theme}` | Fertiger MapLibre-Style (`dark` oder `light`) im Jon-Design, inklusive 3D-Gebäuden, Gelände und Overlays |
| GET | `/api/maps/search?q=&lat=&lon=&limit=` | Orte, Adressen und Kategorien suchen |
| GET | `/api/maps/nearby?category=&lat=&lon=&radius=&limit=` | Orte einer Kategorie in der Umgebung |
| GET | `/api/maps/reverse?lat=&lon=` | Ort zu einem Punkt |
| POST | `/api/maps/route` | Route berechnen: `{points:[{lat,lon}…], mode, alternatives}`, `mode` ist `fuss`, `auto`, `fahrrad` oder `oepnv` |
| GET | `/api/maps/street?lat=&lon=&radius=&limit=` | Straßenfotos an einem Punkt; ohne Fotos kommt `modus: "render"` |
| GET | `/api/maps/street/sequence/{id}` | Alle Bilder einer Aufnahmefahrt |
| POST | `/api/maps/action` | Was das Tool `maps` nutzt: `{action, args}` mit `action` = `suche`, `umgebung`, `route` oder `erkunden`; liefert Treffer, Routen, Text und ein fertiges `karte`-Objekt |

Die Anbieter sind über die `.env` austauschbar (`MAPS_GEOCODER`, `MAPS_PLACES`,
`MAPS_ROUTER`, `MAPS_TRANSIT`, `MAPS_STREET` und die zugehörigen Basis-URLs). Alle
Voreinstellungen sind kostenlos und brauchen keinen Schlüssel.

## Jon Deep Learning

| Methode | Pfad | Beschreibung |
|---------|------|--------------|
| GET | `/api/research/tasks` | Verlauf (`aufgaben`) und laufende Recherchen (`aktiv`) |
| POST | `/api/research/start` | Recherche starten: `{topic, minutes, depth, provider?, model?}`, `depth` ist `schnell`, `normal` oder `tief` |
| GET | `/api/research/tasks/{id}` | Vollständiger Stand: Unterthemen, Quellen, Protokoll, Dateien, Restzeit |
| GET | `/api/research/tasks/{id}/stream` | Server-Sent Events mit dem Live-Fortschritt |
| POST | `/api/research/tasks/{id}/control` | `{action}` = `pause`, `resume`, `stop` oder `resume_task` (nach Neustart weiterführen) |
| GET | `/api/research/tasks/{id}/files` | Wissensdateien der Recherche |
| GET | `/api/research/tasks/{id}/files/{name}` | Inhalt einer Wissensdatei |
| DELETE | `/api/research/tasks/{id}` | Recherche samt Fortschritt löschen |

Der Fortschritt liegt als JSON unter `<Datenordner>/research/`, das Wissen als Markdown
unter `skills/<thema>/`. Eine unterbrochene Recherche wird beim Start des Backends auf
`unterbrochen` gesetzt und lässt sich mit `resume_task` fortsetzen.

## Nutzung

| Methode | Pfad | Beschreibung |
|---------|------|--------------|
| GET | `/api/usage` | Nutzung pro Anbieter |
| DELETE | `/api/usage` | Nutzung zurücksetzen (optional `?provider=`) |

## Direkte System-Endpoints

`/api/system/powershell`, `/cmd`, `/open-url`, `/start-program`, `/kill-program`,
`/explorer`, `/files/{list,read,write,move,delete}`, `/vscode`, `/transcribe`.

## Papierkorb & Aktionsprotokoll

- `GET /api/trash` — Papierkorb-Einträge (gelöscht/überschrieben/verschoben).
- `POST /api/trash/restore` `{ id }` — Eintrag wiederherstellen.
- `POST /api/trash/undo` — letzte Dateiaktion rückgängig machen.
- `GET /api/actions?source=&day=&limit=` — Aktionsprotokoll, gefiltert nach Quelle
  (`app`, `mini-jon`, `telegram`, `automation`, `watcher`) und Tag (`heute`, `gestern`,
  Datum).

## Sprachsteuerung (openWakeWord)

- `GET /api/voice/wake` — Status (`available`, `listening`, `counter`, `error`).
- `POST /api/voice/wake/start` — Wake-Word-Erkennung starten (offline).
- `POST /api/voice/wake/stop` — stoppen und Mikrofon freigeben.

## Kalender

- `GET /api/calendar?start=&days=` — zusammengeführte Einträge (Jon, Automationen,
  Erinnerungen, ICS).
- `POST /api/calendar` `{ title, date, time?, duration_minutes?, note?, kind? }` — anlegen;
  liefert `konflikte`, wenn sich Termine überschneiden.
- `PUT /api/calendar/{id}` — ändern (nur gesetzte Felder); `done` hakt Tasks ab.
- `DELETE /api/calendar/{id}` — löschen.
- `GET /api/calendar/due` — jetzt fällige Termine (für Benachrichtigungen).

## Spiele

- `GET /api/games?frisch=` — alle gefundenen Spiele mit `status` (`bereit`, `laeuft`,
  `baut`, `nicht_gebaut`, `fehler`, `fehlt`, `nicht_verfuegbar`), `hinweis`, `version`,
  `herausgeber`, `gebaut_am`, `typ` (`nativ` oder `web`) und `vorschau`. `frisch=true`
  liest die Manifeste neu ein.
- `POST /api/games/{id}/start` — startet das Spiel als eigenen Prozess (`typ: "nativ"`)
  bzw. liefert den Pfad zum Öffnen im Browser-Tab (`typ: "web"`). Fehler kommen als 400
  mit verständlichem Text.
- `POST /api/games/{id}/stop` — beendet ein laufendes Spiel.
- `POST /api/games/{id}/build` — kompiliert das Spiel im Hintergrund (Bau-Skript aus dem
  Manifest, nur Windows); der Fortschritt steht danach im `status`.
- `GET /api/games/{id}/vorschau` — Vorschaubild.

Neue Spiele braucht man nicht einzuprogrammieren: Ordner mit `jon-spiele.json` neben Jon
oder in `games/` legen (`spiele: [{ id, titel, genre, icon, kurz, beschreibung,
steuerung, exe, args, vorschau, version }]`).

## Mini Jon

- `GET /api/mini-jon/status` — Status (`{ status: "wach" | "schlaeft", since }`).
- `POST /api/mini-jon/status` `{ status }` — Status setzen; „schläft" wird auch von den
  Telegram-Kommandos `/schlafen` und `/aufwachen` des Mini-Jon-Bots geschaltet. Schläft
  Emil, zeigen Desktop-Figur und Telegram-Bot eine Schlaf-Animation mit geschlossenen
  Augen statt Antworten.

## Telegram-Gruppen

Jon (`telegram_bot_token`) und Mini Jon (`mini_jon_bot_token`, eigener Bot) können
gemeinsam in Telegram-Gruppen sein: Beide lesen alle Nachrichten mit (bei @BotFather
`/setprivacy` → Disable) und speichern sie in einem gemeinsamen Gruppen-Verlauf
(`data/telegram_groups.json`), antworten aber nur, wenn sie mit ihrem `@Benutzernamen`
erwähnt werden. Weitere Bots lassen sich als Unterklasse von `GroupBot`
(`app/services/telegram_group_service.py`) ergänzen und harmonieren über denselben
Verlauf. In Gruppen sind PC-Tools bewusst deaktiviert.

## Auto-Update

- `GET /api/update` — prüft, ob eine neuere Version vorliegt.
- `POST /api/update` — führt das Update aus und streamt den Fortschritt als `text/plain`
  (Backup von `data/`, `git pull`, bedingt `pip`/`npm`, Neustart bzw. `systemctl restart
  jon` auf dem Pi).

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

### Browser-Agent (Playwright)
- `browser_task(auftrag, dry_run?, max_schritte?)` — kompletter Auftrag: planen, oeffnen,
  lesen, klicken, ausfuellen, berichten. Erste Wahl fuer alles Mehrstufige.
- `browser_goto(url)`, `browser_search(query)`, `browser_read()`
- `browser_click(element)`, `browser_fill(element, text, enter?)`, `browser_press(taste,
  element?)`, `browser_scroll(richtung?, menge?)`, `browser_select(element, option)`
- `browser_back()`, `browser_forward()`, `browser_reload()`, `browser_wait(element?,
  timeout?)`
- `browser_tab_new(url?)`, `browser_tab_switch(tab)`, `browser_tab_close(tab?)`
- `browser_screenshot(ganz?)`, `browser_status()`, `browser_close()`
- `browser_confirm(token, abbrechen?)` — gibt eine vom RiskActionGuard gestoppte Aktion
  frei, nur nach ausdruecklicher Zustimmung des Nutzers.
- `element` ist eine ID aus `browser_read` (z.B. `e17`) oder sichtbarer Text.
- REST: `GET /api/browser/status`, `POST /api/browser/confirm`, `POST /api/browser/stop`.

### Denken, Gedächtnis und Ziele
- `was_war(zeitraum?, thema?)`, `verlauf_heute()` — Jons Ereignisgedaechtnis
- `ziel(aktion, titel?, frist?, naechster_schritt?, id?, zustand?, fortschritt?)`
- `weltmodell(aktion, name?, art?, beschreibung?, ziel?, beziehung?)`
- `notizblock(aktion, inhalt?, bereich?)` — Arbeitsgedaechtnis
- `selbstbild(aufgabe?)` — Faehigkeiten, Erfolgsquoten, Grenzen
- `erfahrung(bereich?, aktion?, text?, art?)` — was wo klappt
- `weltzustand()` — Browser, Bildschirm, Handy, Auftraege, Ziele, Netz, Budget
- `gedaechtnis_pflegen(tag?)` — Tag nacharbeiten und konsolidieren
- `initiative(aktion, id?)` — vorausdenken, entscheiden, ausfuehren
- `team(aufgabe, agenten?)` — mehrere Teilagenten parallel
- `lernen(aktion, id?, titel?)` — Muster, Skills, Trainingsdaten
- `rueckgaengig(id?, nur_zeigen?)`, `netz_status(neu?)`
- REST: `GET /api/denken/zustand|ziele|verlauf|initiative|selbstbild|weltmodell|
  auftraege|budget|benchmark`, `POST /api/denken/ziele`, `PATCH /api/denken/ziele/{id}`,
  `POST /api/denken/initiative/lauf`, `POST /api/denken/konsolidieren`

- `browser_wahl(browser?, speicher?)` — welcher Browser fuer Webseiten und Websuche
  (`jon`, `system`, `chrome`, `edge`, `firefox`, `brave`, `opera`, `vivaldi`) und ob
  Jons Browser alles nur im Arbeitsspeicher haelt (`ram`) oder auf der Festplatte
  ablegt (`festplatte`)

### Kalender
- `calendar_add(title, date, time?, duration_minutes?, note?, kind?)`
- `calendar_list(start?, days?)`, `calendar_search(query)`
- `calendar_update(id, ...)`, `calendar_delete(id)`

### Dokumente & Präsentationen
- `read_pdf(path, max_pages?)`
- `create_pptx(title, slides, path?, theme?, subtitle?)` — baut eine fertige `.pptx`.
  `slides` ist eine Liste aus `{layout, title, subtitle, text, bullets, items, image,
  notes}`; `layout` ist `title`, `bullets`, `cards`, `stat`, `two_columns`, `image`,
  `quote`, `timeline` oder `closing`; `theme` eines von `midnight`, `ocean`, `forest`,
  `sage`, `teal`, `coral`, `terracotta`, `berry`, `cherry`, `charcoal`, `gold`
- `read_pptx(path, max_slides?)` — Text und Sprechernotizen je Folie

### Karten & Navigation
- `maps(action, query?, category?, around?, from?, to?, via?, mode?, radius?)` —
  `action` ist `suche` (Orte und Adressen), `umgebung` (Kategorie in der Nähe),
  `route` (Dauer, Entfernung, Alternativen) oder `erkunden` (Straßenebene).
  Das Ergebnis enthält ein `karte`-Objekt; im Chat erscheint daraus eine interaktive Karte.

### Eigenständiges Lernen
- `deep_learning(action, topic?, minutes?, depth?, id?)` — `action` ist `start`,
  `status`, `pause`, `weiter` oder `stop`. `start` legt eine Recherche an, die im
  Hintergrund läuft und im Chat als Live-Panel erscheint.

### Gedächtnis & Skills
- `remember(content)`, `recall(query?)`, `forget(query)`
- `list_skills()`, `read_skill(name)`, `write_skill(name, content)`
- `read_skill_file(name, file)` — eine einzelne Wissensdatei aus einem Wissensordner

**Freigabe:** Ohne Rückfrage laufen nur reine Abfragen wie `get_screen_info`,
`list_windows`, `wait`, `recall`, `system_info`, `list_processes`, `list_skills`,
`read_skill`, `read_skill_file`, `read_pptx`, `browser_read`, `browser_screenshot`,
`calendar_list`, `calendar_search`, `maps`, `deep_learning`.
Alle anderen fragen im Modus „Zuerst fragen" um Erlaubnis.
