@echo off
setlocal
title Jon KI-Desktop
cd /d "%~dp0"
set ELECTRON_RUN_AS_NODE=
set NODE_OPTIONS=

if not exist ".env" (
    copy ".env.example" ".env" >nul
    echo .env wurde erstellt. Bitte NVIDIA_API_KEY in .env eintragen und die Datei erneut starten.
    pause
    exit /b 0
)

where python >nul 2>nul
if errorlevel 1 (
    echo Python wurde nicht gefunden. Bitte Python 3.11+ von https://www.python.org installieren.
    pause
    exit /b 1
)

where npm >nul 2>nul
if errorlevel 1 (
    echo Node.js wurde nicht gefunden. Bitte Node.js 18+ von https://nodejs.org installieren.
    pause
    exit /b 1
)

for /f "tokens=5" %%p in ('netstat -ano ^| findstr ":8756 " ^| findstr "LISTENING"') do taskkill /f /pid %%p >nul 2>nul

python -c "import fastapi,uvicorn,sqlalchemy,openai,anthropic,httpx" >nul 2>nul
if errorlevel 1 (
    echo Installiere Backend-Abhaengigkeiten...
    python -m pip install -r "%~dp0backend\requirements.txt"
)

echo Starte Jon-Backend...
start "Jon Backend" /min cmd /c "cd /d "%~dp0backend" && python -m app.main"

echo Warte auf Backend...
powershell -NoProfile -Command "$ok=$false;for($i=0;$i -lt 40;$i++){try{$null=Invoke-WebRequest -UseBasicParsing -TimeoutSec 2 http://127.0.0.1:8756/api/health;$ok=$true;break}catch{Start-Sleep -Milliseconds 700}};if($ok){Write-Host 'Backend laeuft auf http://127.0.0.1:8756'}else{Write-Host 'Backend nicht erreichbar - Fenster Jon Backend pruefen'}"

cd /d "%~dp0frontend"
if not exist "node_modules" (
    echo Installiere Frontend-Abhaengigkeiten...
    call npm install
)

echo Starte Jon-App...
call npm run dev

endlocal
