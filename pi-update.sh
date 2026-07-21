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

echo "[2/5] Aktualisiere Backend-Abhaengigkeiten..."
if [ -d backend/.venv ]; then
  backend/.venv/bin/pip install -q -r backend/requirements-pi.txt || echo "Warnung: pip-Update unvollstaendig."
else
  echo "Keine venv gefunden - fuehre stattdessen pi-installieren.sh aus."
  exit 1
fi

echo "[3/5] Baue die Web-App neu (damit neue Funktionen unter /app erscheinen)..."
if command -v npm >/dev/null 2>&1; then
  rm -rf frontend/dist.bak
  if [ -d frontend/dist ]; then
    cp -r frontend/dist frontend/dist.bak
  fi
  if (cd frontend && export ELECTRON_SKIP_BINARY_DOWNLOAD=1 && npm install --no-audit --no-fund && npm run build); then
    rm -rf frontend/dist.bak
    echo "Web-App aktualisiert."
  else
    echo "Hinweis: Der Web-App-Bau ist fehlgeschlagen (oft zu wenig RAM auf dem Pi)."
    if [ -d frontend/dist.bak ]; then
      rm -rf frontend/dist
      mv frontend/dist.bak frontend/dist
      echo "Die vorige Web-App wurde wiederhergestellt (evtl. ohne die neuesten Aenderungen)."
    fi
    echo "Der private Browser laeuft trotzdem direkt unter http://<IP>:8756/privat"
  fi
else
  echo "npm ist nicht installiert - /app wird nicht neu gebaut."
  echo "Der private Browser ist dennoch direkt erreichbar unter http://<IP>:8756/privat"
fi

echo "[4/5] Starte den Dienst neu..."
sudo systemctl restart jon.service

echo "[5/5] Warte, bis Jon antwortet..."
for i in $(seq 1 40); do
  if backend/.venv/bin/python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8756/api/health', timeout=2)" >/dev/null 2>&1; then
    IP="$(hostname -I 2>/dev/null | awk '{print $1}')"
    echo ""
    echo "Fertig! Jon laeuft in der neuesten Version."
    echo "  Handy/Uhr im WLAN:  http://$IP:8756/app"
    echo "  Privater Browser:   http://$IP:8756/privat"
    exit 0
  fi
  sleep 1
done
echo ""
echo "Jon antwortet noch nicht. Schau in die Logs:"
echo "  journalctl -u jon -e --no-pager | tail -40"
exit 1
