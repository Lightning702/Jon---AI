@echo off
setlocal enabledelayedexpansion
title Jon-Setup.exe bauen
cd /d "%~dp0"
set ELECTRON_RUN_AS_NODE=
set NODE_OPTIONS=

echo ============================================
echo   Jon-Setup.exe bauen
echo ============================================
echo.

where py >nul 2>nul
if errorlevel 1 (
    set "PY=python"
) else (
    set "PY=py -3"
)

echo [1/5] Pruefe PyInstaller...
%PY% -c "import PyInstaller" >nul 2>nul
if errorlevel 1 (
    echo Installiere PyInstaller...
    %PY% -m pip install --disable-pip-version-check pyinstaller
    if errorlevel 1 goto :fail
)

echo [2/5] Stelle Backend-Abhaengigkeiten sicher...
%PY% -m pip install --disable-pip-version-check -r backend\requirements.txt
if errorlevel 1 goto :fail

echo [3/5] Buendle Backend zu jon-backend.exe ^(dauert ein paar Minuten^)...
cd /d "%~dp0backend"
rmdir /s /q build dist 2>nul
%PY% -m PyInstaller --noconfirm --clean jon-backend.spec
if errorlevel 1 goto :fail
if not exist "dist\jon-backend\jon-backend.exe" (
    echo jon-backend.exe wurde nicht erstellt.
    goto :fail
)

echo [4/5] Baue Frontend...
cd /d "%~dp0frontend"
if not exist "node_modules" (
    call npm install
    if errorlevel 1 goto :fail
)
call npm run build
if errorlevel 1 goto :fail

echo [5/5] Paketiere Installer ^(NSIS^)...
call npx electron-builder --config installer.config.json
if errorlevel 1 goto :fail

echo.
echo ============================================
echo   Fertig!
echo ============================================
echo Die Jon-Setup.exe liegt in:
echo   %~dp0frontend\release
echo.
start "" "%~dp0frontend\release"
pause
exit /b 0

:fail
echo.
echo Der Build ist fehlgeschlagen. Bitte die Meldungen oben pruefen.
pause
exit /b 1
