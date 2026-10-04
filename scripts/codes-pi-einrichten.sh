#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."
JON_DIR="$(pwd)"
NUTZER="$(id -un)"
PORT="${JON_CODES_PORT:-8791}"
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

codes() {
  (cd "$JON_DIR/backend" && "$PY" -m app.codeserver "$@")
}

[ "$(id -u)" != "0" ] || fehler "Bitte als normaler Benutzer starten, nicht als root."
[ -x "$PY" ] || fehler "Jon ist hier noch nicht installiert. Zuerst ./pi-installieren.sh ausführen."
(cd "$JON_DIR/backend" && "$PY" -c "import app.codeserver") 2>/dev/null || fehler "Diese Jon-Version kennt den Codeserver noch nicht. Zuerst Jon auf dem Pi aktualisieren."

echo "[1/5] Richte den Codeserver ein (Port $PORT, nur lokal erreichbar) ..."
mkdir -p "$DIENSTE"
cat > "$DIENSTE/jon-codes.service" <<DIENST
[Unit]
Description=Jon Codeserver für Admin- und Entwickler-Codes
After=network-online.target

[Service]
WorkingDirectory=$JON_DIR/backend
Environment=JON_CODES_HOST=127.0.0.1
Environment=JON_CODES_PORT=$PORT
ExecStart=$PY -m app.codeserver
Restart=always
RestartSec=5
UMask=0077
NoNewPrivileges=true

[Install]
WantedBy=default.target
DIENST
if [ "$(loginctl show-user "$NUTZER" -p Linger --value 2>/dev/null)" != "yes" ]; then
  sudo loginctl enable-linger "$NUTZER"
fi
systemctl --user daemon-reload
systemctl --user enable jon-codes.service >/dev/null 2>&1
systemctl --user restart jon-codes.service

echo "[2/5] Warte auf den Codeserver ..."
for i in $(seq 1 30); do
  if curl -fsS "http://127.0.0.1:$PORT/codes/status" >/dev/null 2>&1; then
    break
  fi
  sleep 1
  [ "$i" = "30" ] && fehler "Der Codeserver startet nicht. Logs: journalctl --user -u jon-codes -e --no-pager | tail -40"
done

echo "[3/5] Admin-Code ..."
if curl -fsS "http://127.0.0.1:$PORT/codes/status" | grep -q '"admin":true'; then
  echo "Ist schon eingerichtet. Ändern mit: cd $JON_DIR/backend && $PY -m app.codeserver admin"
else
  read -r -s -p "Admin-Code festlegen (mindestens 12 Zeichen, wird nicht angezeigt): " CODE
  echo ""
  printf '%s\n' "$CODE" | codes admin
  unset CODE
fi

echo "[4/5] Gebe den Codeserver über Tailscale Funnel unter /codes frei ..."
if ! command -v tailscale >/dev/null 2>&1; then
  curl -fsSL https://tailscale.com/install.sh | sh
fi
if ! tailscale status >/dev/null 2>&1; then
  echo "Melde den Pi bei Tailscale an. Öffne den Link, der gleich erscheint, im Browser:"
  sudo tailscale up
fi
ts funnel --bg --set-path /codes "http://127.0.0.1:$PORT/codes" >/dev/null

echo "[5/5] Fertig."
NAME="$(tailscale status --json | "$PY" -c 'import json,sys; print(json.load(sys.stdin)["Self"]["DNSName"].rstrip("."))')"
echo ""
echo "Codeserver:              https://$NAME/codes/status"
echo "Öffentlicher Schlüssel:  $(codes oeffentlich)"
echo ""
echo "Jon nutzt https://$NAME/codes, wenn JON_CODES_URL nicht anders gesetzt ist."
echo "Geheime Dateien liegen nur hier: ${JON_CODES_DIR:-$HOME/.local/share/jon-codes} (Rechte 600)."
echo "Stoppen: tailscale funnel --set-path /codes off && systemctl --user disable --now jon-codes"
