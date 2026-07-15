@echo off
setlocal enabledelayedexpansion
title Jon Autostart
cd /d "%~dp0"
set ELECTRON_RUN_AS_NODE=
set NODE_OPTIONS=

if not exist ".env" (
    if exist ".env.example" copy ".env.example" ".env" >nul
)
if not exist ".env" exit /b 0

set PY=
py -3 -c "import sys" >nul 2>nul
if not errorlevel 1 set PY=py -3
if not defined PY (
    python -c "import sys" >nul 2>nul
    if not errorlevel 1 set PY=python
)
if not defined PY exit /b 1

where npm >nul 2>nul
if errorlevel 1 exit /b 1

set "LOGDIR=%LOCALAPPDATA%\Jon"
if not exist "%LOGDIR%" mkdir "%LOGDIR%"
set "LOGFILE=%LOGDIR%\backend.log"

powershell -NoProfile -Command "Get-NetTCPConnection -LocalPort 8756 -State Listen -ErrorAction SilentlyContinue | Select-Object -ExpandProperty OwningProcess -Unique | ForEach-Object { Stop-Process -Id $_ -Force -ErrorAction SilentlyContinue }" >nul 2>nul

%PY% -c "import fastapi,uvicorn,sqlalchemy,openai,anthropic,httpx,pydantic_settings,speech_recognition,pyautogui,pygetwindow,pyperclip,pypdf,cv2,edge_tts,cryptography,paho.mqtt.client,yt_dlp,pynput" >nul 2>nul
if errorlevel 1 (
    %PY% -m pip install --disable-pip-version-check -r "%~dp0backend\requirements.txt" >nul 2>nul
    if errorlevel 1 %PY% -m pip install --disable-pip-version-check --user -r "%~dp0backend\requirements.txt" >nul 2>nul
)

del "%LOGFILE%" >nul 2>nul
start "Jon Backend" /min powershell -NoProfile -ExecutionPolicy Bypass -Command "$host.UI.RawUI.WindowTitle = 'Jon Backend'; Set-Location '%~dp0backend'; & %PY% -m app.main 2>&1 | ForEach-Object ToString | Tee-Object -FilePath '%LOGFILE%'"

set BACKEND_OK=
for /l %%i in (1,1,30) do (
    if not defined BACKEND_OK (
        powershell -NoProfile -Command "try{$null=Invoke-WebRequest -UseBasicParsing -TimeoutSec 2 http://127.0.0.1:8756/api/health;exit 0}catch{exit 1}" >nul 2>nul
        if not errorlevel 1 set BACKEND_OK=1
        if not defined BACKEND_OK ping -n 2 127.0.0.1 >nul
    )
)

cd /d "%~dp0frontend"
if not exist "node_modules" call npm install >nul 2>nul

call npm run dev
endlocal
