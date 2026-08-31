@echo off
setlocal
set "REPO_ROOT=%~dp0"
set "HG_PYTHON_EXECUTABLE=%REPO_ROOT%.venv\Scripts\python.exe"

if not exist "%HG_PYTHON_EXECUTABLE%" (
  echo.
  echo Holy Grail RP: Python virtual environment not found.
  echo Expected: %HG_PYTHON_EXECUTABLE%
  echo.
  echo From the repository root, provision once:
  echo   python -m venv .venv
  echo   .\.venv\Scripts\Activate.ps1
  echo   pip install -e ".[app]"
  echo.
  pause
  exit /b 1
)

cd /d "%REPO_ROOT%v2\rp_runtime"
call npm run app
endlocal
