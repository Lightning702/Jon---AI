#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."
JON_DIR="$(pwd)"
NUTZER="$(id -un)"
PORT="${JON_DEMO_PORT:-8790}"
PY="$JON_DIR/backend/.venv/bin/python"
DIENSTE="$HOME/.config/systemd/user"

fehler() {
  echo ""
  echo "FEHLER: $1"
  exit 1
}

ts() {
  if tailscale "$@" 2>/dev/null; then
    return 0
  fi
  sudo tailscale "$@"
}

[ "$(id -u)" != "0" ] || fehler "Bitte als normaler Benutzer starten, nicht als root."
[ -x "$PY" ] || fehler "Jon ist hier noch nicht installiert. Zuerst ./pi-installieren.sh ausführen."
(cd "$JON_DIR/backend" && "$PY" -c "import app.demo") 2>/dev/null || fehler "Diese Jon-Version kennt die Demo noch nicht. Zuerst Jon auf dem Pi aktualisieren (git pull oder Pi-Update in der App)."

echo "[1/4] Richte den Demo-Dienst ein (Port $PORT, nur lokal erreichbar) ..."
if systemctl list-unit-files jon-demo.service >/dev/null 2>&1 && systemctl is-enabled jon-demo.service >/dev/null 2>&1; then
  sudo systemctl disable --now jon-demo.service >/dev/null 2>&1 || true
fi
mkdir -p "$DIENSTE"
cat > "$DIENSTE/jon-demo.service" <<DIENST
[Unit]
Description=Jon Website-Demo
After=network-online.target

[Service]
WorkingDirectory=$JON_DIR/backend
Environment=JON_DEMO_HOST=127.0.0.1
Environment=JON_DEMO_PORT=$PORT
ExecStart=$PY -m app.demo
Restart=always
RestartSec=5
NoNewPrivileges=true

[Install]
WantedBy=default.target
DIENST
if [ "$(loginctl show-user "$NUTZER" -p Linger --value 2>/dev/null)" != "yes" ]; then
  sudo loginctl enable-linger "$NUTZER"
fi
systemctl --user daemon-reload
systemctl --user enable jon-demo.service >/dev/null 2>&1
systemctl --user restart jon-demo.service

echo "[2/4] Warte, bis die Demo antwortet ..."
for i in $(seq 1 40); do
  if curl -fsS "http://127.0.0.1:$PORT/demo/status" >/dev/null 2>&1; then
    break
  fi
  sleep 1
  [ "$i" = "40" ] && fehler "Die Demo startet nicht. Logs: journalctl --user -u jon-demo -e --no-pager | tail -40"
done

echo "[3/4] Mache die Demo über Tailscale Funnel unter /demo im Internet erreichbar ..."
if ! command -v tailscale >/dev/null 2>&1; then
  curl -fsSL https://tailscale.com/install.sh | sh
fi
if ! tailscale status >/dev/null 2>&1; then
  echo "Melde den Pi bei Tailscale an. Öffne den Link, der gleich erscheint, im Browser:"
  sudo tailscale up
fi
ts funnel --bg --set-path /demo "http://127.0.0.1:$PORT/demo" >/dev/null

echo "[4/4] Fertig."
NAME="$(tailscale status --json | "$PY" -c 'import json,sys; print(json.load(sys.stdin)["Self"]["DNSName"].rstrip("."))')"
echo ""
echo "Die Demo ist erreichbar unter:  https://$NAME/demo/status"
echo "Andere Pfade deines Funnels bleiben unverändert."
echo ""
echo "Letzter Schritt in Netlify (Site getjon → Site configuration → Environment variables):"
echo "  JON_DEMO_URL = https://$NAME"
echo "Danach einmal neu veröffentlichen. Die Seite getjon.info/testen/ verbindet sich dann mit diesem Pi."
echo ""
echo "Stoppen: tailscale funnel --set-path /demo off && systemctl --user disable --now jon-demo"
