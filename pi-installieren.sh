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

echo "[1/5] Pruefe Python..."
if ! command -v python3 >/dev/null 2>&1 || ! python3 -m venv --help >/dev/null 2>&1; then
  sudo apt-get update
  sudo apt-get install -y python3 python3-venv python3-pip || fail "Python konnte nicht installiert werden."
fi
python3 - <<'PYEOF' || fail "Python 3.11 oder neuer wird benoetigt."
import sys
raise SystemExit(0 if sys.version_info >= (3, 11) else 1)
PYEOF

echo "[2/5] Installiere Backend-Abhaengigkeiten (das dauert beim ersten Mal ein paar Minuten)..."
if [ ! -d backend/.venv ]; then
  python3 -m venv backend/.venv || fail "Konnte die virtuelle Umgebung nicht anlegen."
fi
backend/.venv/bin/pip install --upgrade pip >/dev/null 2>&1
backend/.venv/bin/pip install -r backend/requirements-pi.txt || fail "Backend-Abhaengigkeiten konnten nicht installiert werden. Pruefe die Internetverbindung."

echo "[3/5] Richte .env ein..."
if [ ! -f .env ]; then
  cp .env.example .env
  echo "Neue .env aus .env.example erstellt - deine API-Keys musst du dort noch eintragen."
fi
if grep -q '^JON_LAN=' .env; then
  sed -i 's/^JON_LAN=.*/JON_LAN=true/' .env
else
  printf '\nJON_LAN=true\n' >> .env
fi

echo "[4/5] Richte den Autostart-Dienst ein..."
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

echo "[5/5] Warte, bis Jon antwortet..."
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

IP="$(hostname -I 2>/dev/null | awk '{print $1}')"
TOKEN="$(backend/.venv/bin/python - <<'PY'
import json, urllib.request
try:
    datei = json.load(urllib.request.urlopen("http://127.0.0.1:8756/api/health", timeout=5))["token_file"]
    print(open(datei, encoding="utf-8").read().strip())
except Exception:
    print("")
PY
)"
if [ -n "$TOKEN" ]; then
  ZUGANG="http://$IP:8756/app/?token=$TOKEN"
else
  ZUGANG="http://$IP:8756/app"
fi
echo ""
echo "Fertig! Jon laeuft und startet ab jetzt bei jedem Hochfahren des Pi von selbst."
echo ""
echo "  Handy/Uhr im WLAN:   $ZUGANG"
echo "                       (die Adresse enthaelt deinen Geraete-Schluessel -"
echo "                        einmal am Handy oeffnen, danach merkt es sich der Browser)"
echo "  Privater Browser:    http://$IP:8756/privat?token=$TOKEN"
echo "  Schnelltest:         http://$IP:8756/api/health"
echo ""
echo "  API-Keys eintragen:  nano $JON_DIR/.env   (danach: sudo systemctl restart jon)"
echo "  Status ansehen:      systemctl status jon"
echo "  Logs verfolgen:      journalctl -u jon -f"
echo "  Jon stoppen:         sudo systemctl stop jon"
echo "  Autostart aus:       sudo systemctl disable jon"
exit 0
