#!/bin/sh
set -e
QUELLE="${JON_HARNESS_URL:-https://getjon.info/jon-harness.pyz}"
ZIEL="$HOME/.local/share/jon-harness"
BIN="$HOME/.local/bin"
printf '\n\033[38;2;94;156;255m  J O N\033[0m  \033[38;2;232;185;74mH A R N E S S\033[0m · von FelWorks\n\n'
if ! command -v python3 >/dev/null 2>&1; then
  printf '  \033[31mPython 3 fehlt.\033[0m Installiere es zuerst (z. B. sudo apt install python3 oder brew install python).\n'
  exit 1
fi
python3 -c 'import sys; sys.exit(0 if sys.version_info >= (3, 9) else 1)' || { printf '  \033[31mBitte Python 3.9 oder neuer installieren.\033[0m\n'; exit 1; }
mkdir -p "$ZIEL" "$BIN"
printf '  Lade Jon Harness herunter …\n'
if command -v curl >/dev/null 2>&1; then
  curl -fsSL "$QUELLE" -o "$ZIEL/jon-harness.pyz.neu"
else
  wget -qO "$ZIEL/jon-harness.pyz.neu" "$QUELLE"
fi
mv "$ZIEL/jon-harness.pyz.neu" "$ZIEL/jon-harness.pyz"
cat > "$BIN/jon" <<'SKRIPT'
#!/bin/sh
exec python3 "$HOME/.local/share/jon-harness/jon-harness.pyz" "$@"
SKRIPT
chmod +x "$BIN/jon"
cp "$BIN/jon" "$BIN/jon-harness"
case ":$PATH:" in
  *":$BIN:"*) ;;
  *)
    for PROFIL in "$HOME/.profile" "$HOME/.bashrc" "$HOME/.zshrc"; do
      if [ -f "$PROFIL" ] && ! grep -q '.local/bin' "$PROFIL"; then
        printf '\nexport PATH="$HOME/.local/bin:$PATH"\n' >> "$PROFIL"
      fi
    done
    ;;
esac
printf '  \033[32m✓ Installiert.\033[0m\n'
if curl -fs --max-time 2 http://127.0.0.1:8756/api/health >/dev/null 2>&1; then
  printf '  \033[32m● Jon läuft – das Terminal verbindet sich automatisch.\033[0m\n'
else
  printf '  ○ Jon ist hier nicht aktiv – das Terminal läuft eigenständig (FelWorks kostenlos, /api für eigene Schlüssel).\n'
fi
printf '\n  Fertig! Starte mit: \033[38;2;232;185;74mjon\033[0m (eventuell neues Terminal öffnen)\n\n'
