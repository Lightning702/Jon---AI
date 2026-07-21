# Entwicklerhandbuch

## Voraussetzungen

- Windows 10/11
- Python 3.12+ (getestet mit 3.14)
- Node.js 20+

## Backend

```bash
cd backend
python -m pip install -r requirements.txt
python -m app.main
```

- Läuft auf `http://127.0.0.1:8756`, Docs unter `/docs`.
- Tests: `python -m pytest tests -q`
- Konfiguration über `.env` (siehe `.env.example`) oder Umgebungsvariablen.

## Frontend

```bash
cd frontend
npm install
npm run dev      # Vite + Electron zusammen
npm run build    # tsc -b && vite build
npm run package  # Windows-Paket (electron-builder)
```

### tsconfig

Das Projekt nutzt Projekt-Referenzen: `tsconfig.json` → `tsconfig.app.json` (App-Code,
`composite: true`) + `tsconfig.node.json` (deckt `vite.config.ts` ab). `src/vite-env.d.ts`
liefert die Vite-Typen.

> Kompilierte `*.js`/`*.d.ts` gehören **nicht** neben die `.tsx`-Quellen in `src/` — sie
> überschatten sonst im Vite-Build die echten Quellen. Sie sind per `.gitignore`
> ausgeschlossen.

## Start-Skripte

- `start-jon.bat` — killt Alt-Prozesse auf Port 8756, startet Backend und App.
- `start.ps1`, `start-server.sh` — Varianten für PowerShell/Bash.

Hinweis: `ELECTRON_RUN_AS_NODE`/`NODE_OPTIONS` müssen vor `electron .` geleert werden;
Vite muss an `127.0.0.1` gebunden sein.

## Neuen Provider hinzufügen

1. OpenAI-kompatibel? Dann in `registry.py` eine `OpenAICompatibleProvider`-Instanz mit
   `base_url`, `key_resolver` und `default_models` anlegen.
2. Andernfalls eine Klasse mit dem `LLMProvider`-Interface (`available`, `list_models`,
   `stream`) schreiben.
3. Key-Mapping in `core/keys.py` und ggf. `account_service.SUPPORTED` ergänzen.

## Neues Tool hinzufügen

1. Schema in `ToolBox.schema()` (`backend/app/services/tools.py`).
2. Ausführung in `ToolBox._execute()`.
3. Klartext in `describe_tool()`.
4. Reine Leseaktion? Dann Namen in `SAFE_TOOLS` aufnehmen.
5. Falls nötig, eine Methode im passenden Service ergänzen.

## Windows-Installer (Jon-Setup.exe)

`build-installer.bat` baut die eigenständige `Jon-Setup.exe` in drei Schritten:

1. PyInstaller bündelt das Backend nach `backend/jon-backend.spec` zu
   `backend/dist/jon-backend/jon-backend.exe` (Entry-Point `backend/run_backend.py`,
   `collect_all` für openWakeWord, Playwright, cv2, edge-tts, sounddevice u. a.).
2. `npm run build` erzeugt das Frontend.
3. `electron-builder --config frontend/installer.config.json` paketiert per NSIS und
   nimmt `jon-backend/` als `extraResources` mit.

Zur Laufzeit erkennt `frontend/electron/main.cjs` die gebündelte `jon-backend.exe` und
startet sie statt Python; beim Beenden wird sie per `taskkill /t /f` sauber gestoppt. Ist
keine Exe vorhanden (Entwickler-Setup), fällt es auf `python -m app.main` zurück. Im
gefrorenen Zustand (`sys.frozen`) legt das Backend sein Datenverzeichnis neben die Exe
(Fallback `%LOCALAPPDATA%\Jon\data`). Playwright-Chromium und openWakeWord-Modelle werden
beim ersten Bedarf zur Laufzeit nachgeladen, nicht ins Bundle gepackt.

Der klassische Entwickler-Build (`npm run package` mit rohem `backend/`-Ordner und
lokalem Python) bleibt über die `build`-Sektion in `package.json` erhalten.

## Raspberry Pi (Always-on-Backend)

`pi-installieren.sh` richtet das Backend auf einem Pi als systemd-Dienst (`jon.service`)
ein: venv unter `backend/.venv`, schlanke Abhängigkeiten aus `backend/requirements-pi.txt`
(ohne pyautogui/pygetwindow/pyperclip/pynput/opencv — alle Nutzungen sind lazy/guarded),
`JON_LAN=true` in der `.env`, Web-App-Build nach `frontend/dist` (falls Node verfügbar;
`ELECTRON_SKIP_BINARY_DOWNLOAD=1` spart den Electron-Download). Daten liegen auf dem Pi
unter `~/.jon/data`. Shell-Skripte brauchen LF-Zeilenenden (`.gitattributes` erzwingt das).

## Deployment der Website

`website/` ist statisch. Am schnellsten direkt in der App: **🧰 Werkzeuge → 🌐 Website
hochladen** (oder `/website` im Chat). Beim ersten Mal einen Netlify Personal Access
Token (app.netlify.com/user/applications) einfügen und die Website auswählen — danach
reicht ein Klick oder ein Drag&Drop des Jon-Ordners auf die Fläche: Jon baut
`website/jon.zip` frisch und schickt nur den Website-Inhalt (~1 MB) über die
Netlify-API. Endpunkte: `/api/netlify/status|token|sites|site|deploy`.

Alternative ohne App: `python scripts/netlify_paket.py` erzeugt `netlify-upload.zip`,
die man bei Netlify auf die Deploy-Fläche zieht (Netlify entpackt sie automatisch).

**Nicht** den ganzen Jon-Ordner auf netlify.com ziehen: mit `backend/dist` und
`node_modules` sind das über 1 GB — der Browser lädt dann alles hoch, braucht viele
Minuten und bricht ab. `website/netlify.toml` enthält den NVIDIA-Proxy und die
PWA-Header.
