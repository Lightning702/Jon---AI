@echo off
setlocal

set "ROOT=%~dp0"
set "ROOT=%ROOT:~0,-1%"

title ECHO by FelWorks

if not exist "%ROOT%\bin\ECHO.exe" (
  echo.
  echo  Kein Build gefunden. Starte Kompilierung...
  echo.
  call "%ROOT%\build.bat"
  if errorlevel 1 (
    echo.
    echo  Build fehlgeschlagen. Spiel kann nicht gestartet werden.
    pause
    exit /b 1
  )
)

cd /d "%ROOT%"
start "" /wait "%ROOT%\bin\ECHO.exe" %*
exit /b %errorlevel%
