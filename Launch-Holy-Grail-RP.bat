@echo off
setlocal
cd /d "%~dp0v2\rp_runtime"
call npm run app
endlocal
