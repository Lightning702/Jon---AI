#!/usr/bin/env bash

cd "$(dirname "$0")"
JON_DIR="$(pwd)"

echo "[1/4] Hole die neueste Version..."
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

echo "[3/4] Starte den Dienst neu..."
sudo systemctl restart jon.service

echo "[4/4] Warte, bis Jon antwortet..."
for i in $(seq 1 40); do
  if backend/.venv/bin/python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8756/api/health', timeout=2)" >/dev/null 2>&1; then
    IP="$(hostname -I 2>/dev/null | awk '{print $1}')"
    echo ""
    echo "Fertig! Jon laeuft in der neuesten Version."
    echo "  Handy/Uhr im WLAN:  http://$IP:8756/app"
    exit 0
  fi
  sleep 1
done
echo ""
echo "Jon antwortet noch nicht. Schau in die Logs:"
echo "  journalctl -u jon -e --no-pager | tail -40"
exit 1
