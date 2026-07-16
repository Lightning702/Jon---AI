#!/usr/bin/env bash
set -e

cd "$(dirname "$0")"
JON_DIR="$(pwd)"
SERVICE_USER="$(id -un)"

if [ "$(id -u)" = "0" ]; then
  echo "Bitte nicht als root starten, sondern als normaler Benutzer (sudo holt sich das Skript selbst)."
  exit 1
fi

echo "[1/6] Pruefe Python..."
if ! command -v python3 >/dev/null 2>&1 || ! python3 -m venv --help >/dev/null 2>&1; then
  sudo apt-get update
  sudo apt-get install -y python3 python3-venv python3-pip
fi
python3 - <<'PYEOF'
import sys
if sys.version_info < (3, 11):
    raise SystemExit("Python 3.11 oder neuer wird benoetigt, gefunden: " + sys.version.split()[0])
PYEOF

echo "[2/6] Installiere Backend-Abhaengigkeiten (das dauert beim ersten Mal ein paar Minuten)..."
if [ ! -d backend/.venv ]; then
  python3 -m venv backend/.venv
fi
backend/.venv/bin/pip install --upgrade pip >/dev/null
backend/.venv/bin/pip install -r backend/requirements-pi.txt

echo "[3/6] Richte .env ein..."
if [ ! -f .env ]; then
  cp .env.example .env
  echo "Neue .env aus .env.example erstellt - deine API-Keys musst du dort noch eintragen."
fi
if grep -q '^JON_LAN=' .env; then
  sed -i 's/^JON_LAN=.*/JON_LAN=true/' .env
else
  printf '\nJON_LAN=true\n' >> .env
fi

echo "[4/6] Baue die Web-App fuer Handy und Uhr..."
if [ -d frontend/dist ]; then
  echo "frontend/dist ist schon da - Bau uebersprungen."
else
  if ! command -v npm >/dev/null 2>&1; then
    sudo apt-get update
    sudo apt-get install -y nodejs npm || true
  fi
  if command -v npm >/dev/null 2>&1; then
    (cd frontend && export ELECTRON_SKIP_BINARY_DOWNLOAD=1 && npm install --no-audit --no-fund && npm run build)
  else
    echo "Node.js ist nicht verfuegbar - die Handy-Oberflaeche unter /app fehlt vorerst."
    echo "Entweder Node.js installieren und dieses Skript nochmal starten, oder am PC"
    echo "'npm run build' ausfuehren und den Ordner frontend/dist auf den Pi kopieren."
  fi
fi

echo "[5/6] Richte den Autostart-Dienst ein..."
sudo tee /etc/systemd/system/jon.service >/dev/null <<EOF
[Unit]
Description=Jon KI-Assistent Backend
After=network-online.target
Wants=network-online.target

[Service]
User=$SERVICE_USER
WorkingDirectory=$JON_DIR/backend
ExecStart=$JON_DIR/backend/.venv/bin/python -m app.main
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF
sudo systemctl daemon-reload
sudo systemctl enable jon.service >/dev/null 2>&1
sudo systemctl restart jon.service

echo "[6/6] Warte, bis Jon antwortet..."
IP="$(hostname -I 2>/dev/null | awk '{print $1}')"
for i in $(seq 1 60); do
  if backend/.venv/bin/python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8756/api/health', timeout=2)" >/dev/null 2>&1; then
    echo ""
    echo "Fertig! Jon laeuft und startet ab jetzt bei jedem Hochfahren des Pi von selbst."
    echo ""
    echo "  Handy/Uhr im WLAN:   http://$IP:8756/app"
    echo "  Schnelltest:         http://$IP:8756/api/health"
    echo ""
    echo "  API-Keys eintragen:  nano $JON_DIR/.env   (danach: sudo systemctl restart jon)"
    echo "  Status ansehen:      systemctl status jon"
    echo "  Logs verfolgen:      journalctl -u jon -f"
    echo "  Jon stoppen:         sudo systemctl stop jon"
    echo "  Autostart aus:       sudo systemctl disable jon"
    exit 0
  fi
  sleep 1
done
echo "Jon antwortet noch nicht. Schau in die Logs: journalctl -u jon -e"
exit 1
