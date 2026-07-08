@echo off
setlocal enabledelayedexpansion
title Jon Installer bauen
cd /d "%~dp0"
set ELECTRON_RUN_AS_NODE=
set NODE_OPTIONS=

where npm >nul 2>nul
if errorlevel 1 (
    echo Node.js wurde nicht gefunden. Bitte Node.js 18+ von https://nodejs.org installieren.
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

echo Baue Jon-Installer. Das kann beim ersten Mal ein paar Minuten dauern...
call npm run package
if errorlevel 1 (
    echo Der Build ist fehlgeschlagen. Bitte Meldungen oben pruefen.
    pause
    exit /b 1
)

echo.
echo Fertig. Der Installer (Jon Setup .exe) liegt in:
echo %~dp0frontend\release
start "" "%~dp0frontend\release"
pause
endlocal
