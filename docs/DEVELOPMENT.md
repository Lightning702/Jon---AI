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

## Deployment der Website

`website/` ist statisch. Netlify-Deploy per Drag&Drop des Ordners; `netlify.toml` enthält
den NVIDIA-Proxy und PWA-Header. Nach Codeänderungen `website/jon.zip` neu bauen.
