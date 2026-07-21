#!/usr/bin/env bash

cd "$(dirname "$0")"
JON_DIR="$(pwd)"
SERVICE_USER="$(id -un)"

if [ "$(id -u)" = "0" ]; then
  echo "Bitte nicht als root starten, sondern als normaler Benutzer (sudo holt sich das Skript selbst)."
  exit 1
fi

fail() {
  echo ""
  echo "FEHLER: $1"
  exit 1
}

echo "[1/6] Pruefe Python..."
if ! command -v python3 >/dev/null 2>&1 || ! python3 -m venv --help >/dev/null 2>&1; then
  sudo apt-get update
  sudo apt-get install -y python3 python3-venv python3-pip || fail "Python konnte nicht installiert werden."
fi
python3 - <<'PYEOF' || fail "Python 3.11 oder neuer wird benoetigt."
import sys
raise SystemExit(0 if sys.version_info >= (3, 11) else 1)
PYEOF

echo "[2/6] Installiere Backend-Abhaengigkeiten (das dauert beim ersten Mal ein paar Minuten)..."
if [ ! -d backend/.venv ]; then
  python3 -m venv backend/.venv || fail "Konnte die virtuelle Umgebung nicht anlegen."
fi
backend/.venv/bin/pip install --upgrade pip >/dev/null 2>&1
backend/.venv/bin/pip install -r backend/requirements-pi.txt || fail "Backend-Abhaengigkeiten konnten nicht installiert werden. Pruefe die Internetverbindung."

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

echo "[4/6] Richte den Autostart-Dienst ein..."
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

echo "[5/6] Warte, bis Jon antwortet..."
OK=0
for i in $(seq 1 60); do
  if backend/.venv/bin/python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8756/api/health', timeout=2)" >/dev/null 2>&1; then
    OK=1
    break
  fi
  sleep 1
done
if [ "$OK" != "1" ]; then
  echo ""
  echo "Das Backend antwortet noch nicht. Schau in die Logs:"
  echo "  journalctl -u jon -e --no-pager | tail -40"
  exit 1
fi

echo "[6/6] Baue die Web-App fuer Handy und Uhr (optional)..."
if [ -d frontend/dist ]; then
  echo "frontend/dist ist schon da - Bau uebersprungen."
elif command -v npm >/dev/null 2>&1; then
  if (cd frontend && export ELECTRON_SKIP_BINARY_DOWNLOAD=1 && npm install --no-audit --no-fund && npm run build); then
    echo "Web-App gebaut."
  else
    echo "Hinweis: Der Web-App-Bau ist fehlgeschlagen (oft zu wenig RAM auf dem Pi)."
    echo "Das Backend laeuft trotzdem. Baue die Web-App am PC mit 'npm run build' und"
    echo "kopiere den Ordner frontend/dist auf den Pi, dann klappt auch die /app-Oberflaeche."
  fi
else
  echo "Node.js/npm ist nicht installiert - die Handy-Oberflaeche unter /app fehlt vorerst."
  echo "Das Backend laeuft trotzdem. Fuer /app: Node installieren und Skript erneut starten,"
  echo "oder frontend/dist am PC bauen und auf den Pi kopieren."
fi

IP="$(hostname -I 2>/dev/null | awk '{print $1}')"
echo ""
echo "Fertig! Jon laeuft und startet ab jetzt bei jedem Hochfahren des Pi von selbst."
echo ""
echo "  Handy/Uhr im WLAN:   http://$IP:8756/app"
echo "  Privater Browser:    http://$IP:8756/privat   (kein Verlauf, keine Cookies)"
echo "  Schnelltest:         http://$IP:8756/api/health"
echo ""
echo "  API-Keys eintragen:  nano $JON_DIR/.env   (danach: sudo systemctl restart jon)"
echo "  Status ansehen:      systemctl status jon"
echo "  Logs verfolgen:      journalctl -u jon -f"
echo "  Jon stoppen:         sudo systemctl stop jon"
echo "  Autostart aus:       sudo systemctl disable jon"
exit 0
