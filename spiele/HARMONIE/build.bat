@echo off
setlocal enabledelayedexpansion

set "ROOT=%~dp0"
set "ROOT=%ROOT:~0,-1%"
set "WERK=%ROOT%\..\felwerk\src"
set "OUTDIR=%ROOT%\bin"
set "OBJDIR=%LOCALAPPDATA%\FelWorks\HARMONIE\obj"
if not exist "%LOCALAPPDATA%\FelWorks" mkdir "%LOCALAPPDATA%\FelWorks"
if not exist "%LOCALAPPDATA%\FelWorks\HARMONIE" mkdir "%LOCALAPPDATA%\FelWorks\HARMONIE"

echo.
echo  ==================================================
echo   Harmonische Inseln by FelWorks - Build
echo  ==================================================
echo.

set "VCVARS="
for %%V in (
  "C:\Program Files (x86)\Microsoft Visual Studio\18\BuildTools\VC\Auxiliary\Build\vcvars64.bat"
  "C:\Program Files\Microsoft Visual Studio\18\BuildTools\VC\Auxiliary\Build\vcvars64.bat"
  "C:\Program Files\Microsoft Visual Studio\2022\Community\VC\Auxiliary\Build\vcvars64.bat"
  "C:\Program Files\Microsoft Visual Studio\2022\Professional\VC\Auxiliary\Build\vcvars64.bat"
  "C:\Program Files\Microsoft Visual Studio\2022\Enterprise\VC\Auxiliary\Build\vcvars64.bat"
  "C:\Program Files\Microsoft Visual Studio\2022\BuildTools\VC\Auxiliary\Build\vcvars64.bat"
  "C:\Program Files (x86)\Microsoft Visual Studio\2022\BuildTools\VC\Auxiliary\Build\vcvars64.bat"
  "C:\Program Files (x86)\Microsoft Visual Studio\2019\BuildTools\VC\Auxiliary\Build\vcvars64.bat"
) do (
  if exist %%V if not defined VCVARS set "VCVARS=%%~V"
)

if not defined VCVARS (
  for /f "usebackq tokens=*" %%I in (`"%ProgramFiles(x86)%\Microsoft Visual Studio\Installer\vswhere.exe" -latest -products * -find VC\Auxiliary\Build\vcvars64.bat 2^>nul`) do (
    if not defined VCVARS set "VCVARS=%%I"
  )
)

if not defined VCVARS (
  echo  [FEHLER] Kein MSVC gefunden.
  echo  Bitte "Visual Studio Build Tools" mit C++ Workload installieren.
  exit /b 1
)

where cl.exe >nul 2>&1
if errorlevel 1 (
  echo  [1/4] MSVC Umgebung: !VCVARS!
  call "!VCVARS!" >nul 2>&1
) else (
  echo  [1/4] MSVC Umgebung bereits aktiv
)

where cl.exe >nul 2>&1
if errorlevel 1 (
  echo  [FEHLER] cl.exe nicht verfuegbar.
  exit /b 1
)

if not exist "%OUTDIR%" mkdir "%OUTDIR%"
if not exist "%OBJDIR%" mkdir "%OBJDIR%"
if not exist "%ROOT%\saves" mkdir "%ROOT%\saves"

if /i "%~1"=="clean" (
  echo  Bereinige Build-Verzeichnis...
  del /q "%OBJDIR%\*" >nul 2>&1
  del /q "%OUTDIR%\HARMONIE.exe" >nul 2>&1
)

set "SRCLIST="
set SRCCOUNT=0
for /r "%ROOT%\src" %%F in (*.cpp) do (
  set "SRCLIST=!SRCLIST! "%%F""
  set /a SRCCOUNT+=1
)
for /r "%ROOT%\tests" %%F in (*.cpp) do (
  set "SRCLIST=!SRCLIST! "%%F""
  set /a SRCCOUNT+=1
)
for /r "%WERK%" %%F in (*.cpp) do (
  set "SRCLIST=!SRCLIST! "%%F""
  set /a SRCCOUNT+=1
)

if %SRCCOUNT%==0 (
  echo  [FEHLER] Keine Quelldateien gefunden.
  exit /b 1
)

echo  [2/4] %SRCCOUNT% Quelldateien gefunden

set "CFLAGS=/nologo /std:c++20 /EHsc /MT /GR- /W3 /wd4244 /wd4305 /wd4267 /wd4018 /permissive- /utf-8 /Zc:preprocessor /DNOMINMAX /DWIN32_LEAN_AND_MEAN /D_CRT_SECURE_NO_WARNINGS"
set "INCLUDES=/I "%ROOT%\src" /I "%WERK%""
set "OPTFLAGS=/O2 /Oi /fp:precise /GS- /DNDEBUG"
if /i "%~1"=="debug" set "OPTFLAGS=/Od /Zi /fp:precise /D_DEBUG"
if /i "%~2"=="debug" set "OPTFLAGS=/Od /Zi /fp:precise /D_DEBUG"

set "LIBS=opengl32.lib user32.lib gdi32.lib shell32.lib winmm.lib"
set "LDFLAGS=/link /INCREMENTAL:NO /OPT:REF /OPT:ICF /SUBSYSTEM:CONSOLE"

echo  [3/4] Kompiliere...
echo.

pushd "%OBJDIR%"
cl %CFLAGS% %INCLUDES% %OPTFLAGS% /MP !SRCLIST! /Fe:"%OUTDIR%\HARMONIE.exe" /Fd:"%OBJDIR%\HARMONIE.pdb" %LIBS% %LDFLAGS%
set BUILDERR=%errorlevel%
if not "%BUILDERR%"=="0" (
  echo.
  echo  Wiederhole Build ohne Parallelisierung...
  echo.
  cl %CFLAGS% %INCLUDES% %OPTFLAGS% !SRCLIST! /Fe:"%OUTDIR%\HARMONIE.exe" /Fd:"%OBJDIR%\HARMONIE.pdb" %LIBS% %LDFLAGS%
  set BUILDERR=!errorlevel!
)
popd

echo.
if not "%BUILDERR%"=="0" (
  echo  ==================================================
  echo   BUILD FEHLGESCHLAGEN
  echo  ==================================================
  exit /b %BUILDERR%
)

echo  [4/4] Fertig: %OUTDIR%\HARMONIE.exe
echo.
echo  ==================================================
echo   BUILD ERFOLGREICH
echo  ==================================================
exit /b 0
