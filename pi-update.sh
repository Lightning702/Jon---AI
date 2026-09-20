#!/usr/bin/env bash

cd "$(dirname "$0")"
JON_DIR="$(pwd)"

echo "[1/4] Hole die neueste Version..."
rm -rf frontend/dist frontend/dist.bak
git stash push -u -m "pi-update-autostash" >/dev/null 2>&1
if ! git pull --rebase; then
  echo "git pull ist fehlgeschlagen. Stelle lokale Aenderungen wieder her..."
  git rebase --abort >/dev/null 2>&1
  git stash pop >/dev/null 2>&1
  echo "Bitte pruefe: git status"
  exit 1
fi
git stash pop >/dev/null 2>&1

echo "[2/4] Aktualisiere Backend-Abhaengigkeiten..."
if [ -d backend/.venv ]; then
  backend/.venv/bin/pip install -q -r backend/requirements-pi.txt || echo "Warnung: pip-Update unvollstaendig."
else
  echo "Keine venv gefunden - fuehre stattdessen pi-installieren.sh aus."
  exit 1
fi

if [ ! -f webapp/index.html ]; then
  echo "Warnung: Der Ordner webapp fehlt - die Oberflaeche unter /app bleibt leer."
fi

echo "[3/4] Starte den Dienst neu..."
sudo systemctl restart jon.service

echo "[4/4] Warte, bis Jon antwortet..."
for i in $(seq 1 40); do
  if backend/.venv/bin/python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8756/api/health', timeout=2)" >/dev/null 2>&1; then
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
    echo ""
    echo "Fertig! Jon laeuft in der neuesten Version."
    if [ -n "$TOKEN" ]; then
      echo "  Handy/Uhr im WLAN:  http://$IP:8756/app/?token=$TOKEN"
      echo "  Privater Browser:   http://$IP:8756/privat?token=$TOKEN"
    else
      echo "  Handy/Uhr im WLAN:  http://$IP:8756/app"
      echo "  Privater Browser:   http://$IP:8756/privat"
    fi
    exit 0
  fi
  sleep 1
done
echo ""
echo "Jon antwortet noch nicht. Schau in die Logs:"
echo "  journalctl -u jon -e --no-pager | tail -40"
exit 1
