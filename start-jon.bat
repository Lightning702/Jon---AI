@echo off
setlocal enabledelayedexpansion
title Jon KI-Desktop
cd /d "%~dp0"
set ELECTRON_RUN_AS_NODE=
set NODE_OPTIONS=

if not exist ".env" (
    copy ".env.example" ".env" >nul
    echo .env wurde erstellt. Bitte NVIDIA_API_KEY oder einen anderen Key in .env eintragen und die Datei erneut starten.
    start notepad ".env"
    pause
    exit /b 0
)

set PY=
py -3 -c "import sys" >nul 2>nul
if not errorlevel 1 set PY=py -3
if not defined PY (
    python -c "import sys" >nul 2>nul
    if not errorlevel 1 set PY=python
)
if not defined PY (
    echo Python wurde nicht gefunden oder ist nur der Windows-Store-Platzhalter.
    echo Bitte Python 3.11+ von https://www.python.org installieren und dabei "Add to PATH" anhaken.
    pause
    exit /b 1
)

%PY% -c "import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)" >nul 2>nul
if errorlevel 1 (
    echo Deine Python-Version ist zu alt. Bitte Python 3.11+ installieren.
    pause
    exit /b 1
)

where npm >nul 2>nul
if errorlevel 1 (
    echo Node.js wurde nicht gefunden. Bitte Node.js 18+ von https://nodejs.org installieren.
    pause
    exit /b 1
)

if not exist "data" mkdir "data"

for /f "tokens=5" %%p in ('netstat -ano ^| findstr ":8756 " ^| findstr "LISTENING"') do taskkill /f /pid %%p >nul 2>nul

%PY% -c "import fastapi,uvicorn,sqlalchemy,openai,anthropic,httpx,pydantic_settings,speech_recognition,pyautogui,pygetwindow,pyperclip" >nul 2>nul
if errorlevel 1 (
    echo Installiere Backend-Abhaengigkeiten...
    %PY% -m pip install --disable-pip-version-check -r "%~dp0backend\requirements.txt"
    if errorlevel 1 (
        echo Erster Versuch fehlgeschlagen, versuche Installation nur fuer deinen Benutzer...
        %PY% -m pip install --disable-pip-version-check --user -r "%~dp0backend\requirements.txt"
        if errorlevel 1 (
            echo Die Installation der Backend-Abhaengigkeiten ist fehlgeschlagen. Bitte Meldungen oben pruefen.
            pause
            exit /b 1
        )
    )
)

echo Starte Jon-Backend...
del "%~dp0data\backend.log" >nul 2>nul
start "Jon Backend" /min cmd /c "cd /d "%~dp0backend" && %PY% -m app.main >> "%~dp0data\backend.log" 2>&1"

echo Warte auf Backend...
set BACKEND_OK=
for /l %%i in (1,1,40) do (
    if not defined BACKEND_OK (
        powershell -NoProfile -Command "try{$null=Invoke-WebRequest -UseBasicParsing -TimeoutSec 2 http://127.0.0.1:8756/api/health;exit 0}catch{exit 1}" >nul 2>nul
        if not errorlevel 1 set BACKEND_OK=1
        if not defined BACKEND_OK ping -n 2 127.0.0.1 >nul
    )
)
if defined BACKEND_OK (
    echo Backend laeuft auf http://127.0.0.1:8756
) else (
    echo.
    echo Das Backend ist nicht gestartet. Letzte Zeilen aus data\backend.log:
    echo ------------------------------------------------------------------
    powershell -NoProfile -Command "if(Test-Path '%~dp0data\backend.log'){Get-Content '%~dp0data\backend.log' -Tail 25}else{Write-Host 'Keine Log-Datei gefunden.'}"
    echo ------------------------------------------------------------------
    echo Tipp: Fehlende Pakete mit  %PY% -m pip install -r backend\requirements.txt  nachinstallieren.
    pause
    exit /b 1
)

cd /d "%~dp0frontend"
if not exist "node_modules" (
    echo Installiere Frontend-Abhaengigkeiten...
    call npm install
    if errorlevel 1 (
        echo npm install ist fehlgeschlagen. Bitte Meldungen oben pruefen.
        pause
        exit /b 1
    )
)

echo Starte Jon-App...
call npm run dev

endlocal
