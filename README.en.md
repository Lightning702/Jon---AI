# Jon — AI Desktop Assistant

🇩🇪 **Deutsche Version: [README.md](README.md)**

Jon is a modern AI desktop assistant for Windows with multi-provider support,
streaming, long-term persistence, real system control, mouse/keyboard automation,
voice control, an editable skill system and a standalone phone app. Backend in
Python/FastAPI, frontend in Electron + React + TypeScript in a black/gold glassmorphism
design.

**Website & download: [https://getjon.netlify.app](https://getjon.netlify.app)**

---

## Download Jon

The easiest way to get Jon is the official website:

1. Open **[https://getjon.netlify.app](https://getjon.netlify.app)**
2. Click **Download** — you get the file `jon.zip`
3. Unzip it wherever you like (e.g. `C:\Jon`)
4. Follow the [setup guide](#setup) below
5. After setup, a double-click on `start-jon.bat` starts backend and app together

Or clone the repository directly:

```bash
git clone https://github.com/Lightning702/Jon---AI.git
```

**Requirements:** Windows 10/11, [Python](https://www.python.org/downloads/) 3.12+ and
[Node.js](https://nodejs.org/) 20+.

**No installation:** The phone app runs directly in the browser at
[https://getjon.netlify.app/app](https://getjon.netlify.app/app/).

---

## Features

- **🙂 Mini Jon** — Jon's little son lives as a cute glowing circle on your desktop:
  always on top, movable, there from Windows startup. He greets you with updates, listens
  continuously (say "Jon" once, then just keep talking), speaks with lip-sync, and can do
  everything the big Jon can. Face, colours, eyes and size are fully customizable.
- **🗣️ Voice control** — Offline wake-word detection ("Jon") via openWakeWord in the
  backend, with automatic fallback to in-window recognition. Barge-in: talk while Jon is
  speaking and he stops instantly. Sensitivity is adjustable in the gear menu.
- **🧰 Real system control** — PowerShell/CMD, launch/kill programs, read/write/move/delete
  files, mouse and keyboard automation, screenshots, window management.
- **🗑️ Trash & action log** — Deletes, overwrites and moves are backed up to `data/trash`
  first (kept 30 days). `/undo` restores the last file action, `/trash` lists everything.
  Every tool call is logged with source (app, Mini Jon, Telegram, automation, watcher);
  `/log` shows the recent actions with filters.
- **🌐 Browser automation** — Jon drives a visible Chromium window (Playwright):
  `browser_goto/click/fill/read/screenshot/back/close`. He reads a page before clicking and
  never logs in or buys anything without explicit confirmation.
- **📅 Calendar** — A local calendar (month/week view) in the black/gold design. Jon adds,
  moves and searches appointments by voice ("Add dentist Friday 3pm"), warns about
  conflicts, and shows automations, reminders and your connected ICS calendar side by side.
  `/calendar` shows the next 7 days.
- **🔒 LAN pairing** — With `JON_LAN=1`, every new device must pair with a 6-digit code
  shown on the PC before it gets a permanent token. Paired devices are managed in the gear
  menu.
- **🔄 Auto-update** — `/update` pulls the latest version, backs up `data/` first, reinstalls
  only what changed, and restarts (on the Raspberry Pi via `systemctl restart jon`).
- **🌍 English & German** — Switch the whole UI and Jon's replies between German and English
  in the gear menu.
- Plus: knowledge base, automations, reminders, friends chat, Telegram bot (with photo
  analysis and direct mouse/keyboard control), evening show, password vault, flashcards,
  and more.

---

## Setup

### 1. Environment variables

```bash
cp .env.example .env
```

Put your API keys in `.env`. **Keys never belong in source code.** Alternatively connect
providers at runtime in the accounts area.

```
NVIDIA_API_KEY=nvapi-...
DEFAULT_PROVIDER=nvidia
DEFAULT_JON_MODEL=openai/gpt-oss-120b
DEFAULT_EMIL_MODEL=openai/gpt-oss-20b
```

### 2. Backend

```bash
cd backend
python -m pip install -r requirements.txt
python -m app.main
```

Backend: `http://127.0.0.1:8756` — API docs: `http://127.0.0.1:8756/docs`.

### 3. Frontend

```bash
cd frontend
npm install
npm run dev
```

`npm run dev` starts Vite and Electron together. `npm run build` creates a production
build, `npm run package` a Windows installer (electron-builder).

Details and troubleshooting: [docs/DEVELOPMENT.md](docs/DEVELOPMENT.md).

### Always on: Jon on a Raspberry Pi

To reach Jon around the clock from phone and smartwatch — even when the PC is off — the
backend can run on a Raspberry Pi (Pi 4 or newer):

1. `git clone https://github.com/Lightning702/Jon---AI.git jon`
2. `cd jon && bash pi-installieren.sh`
3. Enter API keys: `nano .env`, then `sudo systemctl restart jon`

The script installs everything, builds the web app and sets up a systemd service that
starts automatically on boot. Reach Jon at `http://<Pi-IP>:8756/app`.

---

## Security

- API keys live only in your local `.env` or the local account store, never in the code.
- All system control respects the approval mode ("ask first" / "allow all").
- With `JON_LAN=1`, LAN access requires device pairing.
- The trash keeps deleted files for 30 days so mistakes are recoverable.
