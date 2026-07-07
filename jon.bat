@echo off
setlocal
set "JON_ROOT=%~dp0"
pushd "%JON_ROOT%backend"
python -m app.cli %*
popd
endlocal
