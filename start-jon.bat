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

set "LOGDIR=%LOCALAPPDATA%\Jon"
if not exist "%LOGDIR%" mkdir "%LOGDIR%"
set "LOGFILE=%LOGDIR%\backend.log"
del "%~dp0data\backend.log" >nul 2>nul

set "JONLAN="
findstr /I /C:"JON_LAN=true" ".env" >nul 2>nul
if not errorlevel 1 set "JONLAN=1"

set "WLANIP="
for /f "usebackq delims=" %%a in (`powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\start-vorbereiten.ps1" -JonLan "%JONLAN%"`) do set "WLANIP=%%a"

%PY% -c "import importlib.util as u,sys; mods=['fastapi','uvicorn','sqlalchemy','openai','anthropic','httpx','pydantic_settings','speech_recognition','pyautogui','pygetwindow','pyperclip','pypdf','cv2','edge_tts','cryptography','paho.mqtt.client','yt_dlp','pynput','tzdata','numpy']; sys.exit(0 if all(u.find_spec(m) for m in mods) else 1)" >nul 2>nul
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

%PY% -c "import importlib.util as u,sys; sys.exit(0 if u.find_spec('faster_whisper') else 1)" >nul 2>nul
if errorlevel 1 (
    echo Richte die Spracherkennung fuer Telefonanrufe ein...
    %PY% -m pip install --disable-pip-version-check faster-whisper >nul 2>nul
    if errorlevel 1 %PY% -m pip install --disable-pip-version-check --user faster-whisper >nul 2>nul
)

where ffmpeg >nul 2>nul
if errorlevel 1 echo Hinweis: ffmpeg wurde nicht gefunden - ohne ffmpeg kann Jon am Telefon nicht sprechen.

echo Starte Jon-Backend...
del "%LOGFILE%" >nul 2>nul
start "Jon Backend" /min powershell -NoProfile -ExecutionPolicy Bypass -Command "$host.UI.RawUI.WindowTitle = 'Jon Backend'; Set-Location '%~dp0backend'; $log = '%LOGFILE%'; try { Set-Content -Path $log -Value '' -ErrorAction Stop } catch { $log = Join-Path $env:TEMP 'jon-backend.log' }; & %PY% -m app.main 2>&1 | ForEach-Object ToString | Tee-Object -FilePath $log -ErrorAction SilentlyContinue"

echo Warte auf Backend...
set BACKEND_OK=
powershell -NoProfile -Command "for($i=0;$i -lt 200;$i++){ try{ $null=Invoke-WebRequest -UseBasicParsing -TimeoutSec 2 http://127.0.0.1:8756/api/health; exit 0 }catch{ Start-Sleep -Milliseconds 250 } }; exit 1" >nul 2>nul
if not errorlevel 1 set BACKEND_OK=1
if defined BACKEND_OK (
    echo Backend laeuft auf http://127.0.0.1:8756
    set "JONTOKEN="
    for /f "usebackq delims=" %%a in (`powershell -NoProfile -Command "try{$h=Invoke-RestMethod -TimeoutSec 5 http://127.0.0.1:8756/api/health; if($h.token_file -and (Test-Path $h.token_file)){(Get-Content $h.token_file -Raw).Trim()}}catch{''}"`) do set "JONTOKEN=%%a"
    set "SPIELE="
    for /f "usebackq delims=" %%a in (`powershell -NoProfile -Command "try{$r=Invoke-RestMethod -TimeoutSec 5 -Headers @{'X-Jon-Token'='!JONTOKEN!'} http://127.0.0.1:8756/api/games; (($r.spiele | ForEach-Object { $_.titel + ' [' + $_.status + ']' }) -join ', ')}catch{''}"`) do set "SPIELE=%%a"
    if defined SPIELE (
        echo Spiele-Dienst laeuft: !SPIELE!
        echo Spiele starten erst ueber Werkzeuge ^> Spiele ^> Starten.
    )
    if defined WLANIP (
        echo.
        echo Fuer Handy/Uhr im selben WLAN eintragen:  http://%WLANIP%:8756
        echo Test im Handy-Browser:  http://%WLANIP%:8756/api/health
        echo.
    )
) else (
    echo.
    echo Das Backend ist nicht gestartet. Letzte Zeilen aus dem Log:
    echo ------------------------------------------------------------------
    powershell -NoProfile -Command "if(Test-Path '%LOGFILE%'){Get-Content '%LOGFILE%' -Tail 25}else{Write-Host 'Keine Log-Datei gefunden.'}"
    echo ------------------------------------------------------------------
    echo Vollstaendiges Log: %LOGFILE%
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

echo.
echo Jon startet - dieses Fenster bitte offen lassen.
echo Schliesst du es, wird Jon mitsamt Backend beendet.
echo Backend-Log: %LOGFILE%
echo.
echo Starte Jon-App...
call npm run dev
set "APPCODE=%ERRORLEVEL%"

echo Jon wurde beendet - stoppe das Backend...
powershell -NoProfile -Command "try{Invoke-WebRequest -UseBasicParsing -TimeoutSec 3 -Method Post http://127.0.0.1:8756/api/system/shutdown | Out-Null}catch{}" >nul 2>nul
powershell -NoProfile -Command "Start-Sleep -Milliseconds 800; Get-NetTCPConnection -LocalPort 8756 -State Listen -ErrorAction SilentlyContinue | Select-Object -ExpandProperty OwningProcess -Unique | ForEach-Object { $p = Get-Process -Id $_ -ErrorAction SilentlyContinue; if ($p -and $p.ProcessName -match '^(python|pythonw|py|jon-backend)$') { Stop-Process -Id $_ -Force -ErrorAction SilentlyContinue } }" >nul 2>nul
powershell -NoProfile -Command "Get-CimInstance Win32_Process -ErrorAction SilentlyContinue | Where-Object { $_.Name -match '^(python|pythonw|py|jon-backend)\.exe$' -and $_.CommandLine -match 'app\.main|run_backend' } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }" >nul 2>nul

if not "%APPCODE%"=="0" (
    echo.
    echo Die Jon-App hat sich unerwartet beendet ^(Code %APPCODE%^).
    echo Das Backend wurde mitgestoppt, du kannst einfach neu starten.
    echo Meldungen der App stehen oben, das Backend-Log unter: %LOGFILE%
    pause
)

endlocal
