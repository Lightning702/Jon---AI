#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."
JON_DIR="$(pwd)"
NUTZER="$(id -un)"
PORT="${JON_DEMO_PORT:-8790}"

fehler() {
  echo ""
  echo "FEHLER: $1"
  exit 1
}

[ "$(id -u)" != "0" ] || fehler "Bitte als normaler Benutzer starten, nicht als root."
[ -x "$JON_DIR/backend/.venv/bin/python" ] || fehler "Jon ist hier noch nicht installiert. Zuerst ./pi-installieren.sh ausführen."
"$JON_DIR/backend/.venv/bin/python" -c "import app.demo" 2>/dev/null || fehler "Diese Jon-Version kennt die Demo noch nicht. Zuerst Jon auf dem Pi aktualisieren (git pull oder Pi-Update in der App)."

echo "[1/4] Richte den Demo-Dienst ein (Port $PORT, nur lokal erreichbar) ..."
sudo tee /etc/systemd/system/jon-demo.service >/dev/null <<DIENST
[Unit]
Description=Jon Website-Demo
After=network-online.target jon.service
Wants=network-online.target

[Service]
User=$NUTZER
WorkingDirectory=$JON_DIR/backend
Environment=JON_DEMO_HOST=127.0.0.1
Environment=JON_DEMO_PORT=$PORT
ExecStart=$JON_DIR/backend/.venv/bin/python -m app.demo
Restart=always
RestartSec=5
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=full

[Install]
WantedBy=multi-user.target
DIENST
sudo systemctl daemon-reload
sudo systemctl enable jon-demo.service >/dev/null 2>&1
sudo systemctl restart jon-demo.service

echo "[2/4] Warte, bis die Demo antwortet ..."
for i in $(seq 1 40); do
  if curl -fsS "http://127.0.0.1:$PORT/demo/status" >/dev/null 2>&1; then
    break
  fi
  sleep 1
  [ "$i" = "40" ] && fehler "Die Demo startet nicht. Logs: journalctl -u jon-demo -e --no-pager | tail -40"
done

echo "[3/4] Mache die Demo über Tailscale Funnel im Internet erreichbar ..."
if ! command -v tailscale >/dev/null 2>&1; then
  curl -fsSL https://tailscale.com/install.sh | sh
fi
if ! tailscale status >/dev/null 2>&1; then
  echo "Melde den Pi bei Tailscale an. Öffne den Link, der gleich erscheint, im Browser:"
  sudo tailscale up
fi
sudo tailscale funnel --bg "$PORT"

echo "[4/4] Fertig."
NAME="$(tailscale status --json | "$JON_DIR/backend/.venv/bin/python" -c 'import json,sys; print(json.load(sys.stdin)["Self"]["DNSName"].rstrip("."))')"
echo ""
echo "Die Demo ist erreichbar unter:  https://$NAME"
echo ""
echo "Letzter Schritt in Netlify (Site getjon → Site configuration → Environment variables):"
echo "  JON_DEMO_URL = https://$NAME"
echo "Danach einmal neu veröffentlichen. Die Seite getjon.info/testen/ verbindet sich dann mit diesem Pi."
echo ""
echo "Prüfen:  curl https://$NAME/demo/status"
echo "Stoppen: sudo tailscale funnel reset && sudo systemctl disable --now jon-demo"
