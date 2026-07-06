#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT"
unset ELECTRON_RUN_AS_NODE
unset NODE_OPTIONS

if [ ! -f ".env" ]; then
    cp ".env.example" ".env"
    echo ".env erstellt. Bitte NVIDIA_API_KEY in .env eintragen und das Script erneut starten."
    exit 0
fi

PYTHON="python3"
command -v python3 >/dev/null 2>&1 || PYTHON="python"

if ! command -v "$PYTHON" >/dev/null 2>&1; then
    echo "Python wurde nicht gefunden. Bitte Python 3.11+ installieren."
    exit 1
fi

if command -v lsof >/dev/null 2>&1; then
    PIDS="$(lsof -ti tcp:8756 2>/dev/null || true)"
    if [ -n "$PIDS" ]; then
        kill -9 $PIDS 2>/dev/null || true
        sleep 1
    fi
fi

"$PYTHON" -c "import fastapi, uvicorn, sqlalchemy, openai, anthropic, httpx" >/dev/null 2>&1 || "$PYTHON" -m pip install -r "$ROOT/backend/requirements.txt"

cd "$ROOT/backend"
"$PYTHON" -m app.main &
BACKEND_PID=$!
trap 'kill "$BACKEND_PID" 2>/dev/null || true' EXIT INT TERM

OK=0
for _ in $(seq 1 40); do
    if curl -fs http://127.0.0.1:8756/api/health >/dev/null 2>&1; then
        OK=1
        break
    fi
    sleep 0.7
done

if [ "$OK" = "1" ]; then
    echo "Backend laeuft auf http://127.0.0.1:8756"
else
    echo "Backend nicht erreichbar."
    exit 1
fi

if command -v npm >/dev/null 2>&1; then
    cd "$ROOT/frontend"
    [ -d node_modules ] || npm install
    npm run dev
else
    echo "Node.js nicht gefunden - nur Backend laeuft. Zum Beenden Strg+C druecken."
    wait "$BACKEND_PID"
fi
