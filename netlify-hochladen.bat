@echo off
cd /d "%~dp0"
echo Baue das Netlify-Paket...
python scripts\netlify_paket.py
if errorlevel 1 (
  echo.
  echo Fehler beim Bauen des Netlify-Pakets.
  pause
  exit /b 1
)
echo.
echo Es oeffnen sich jetzt der Explorer und Netlify.
echo Zieh die Datei netlify-upload.zip einfach auf die Deploy-Flaeche deiner Website.
start "" explorer /select,"%~dp0netlify-upload.zip"
start "" "https://app.netlify.com/"
pause
