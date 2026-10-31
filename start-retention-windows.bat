@echo off
setlocal
cd /d "%~dp0"
where py >nul 2>nul
if errorlevel 1 (
  echo Install Python 3.11 or 3.12 from python.org first.
  if not defined CI pause
  exit /b 1
)
if not exist .venv-retention\Scripts\python.exe (
  py -3.11 -m venv .venv-retention
  if errorlevel 1 py -3.12 -m venv .venv-retention
  if errorlevel 1 goto fail
)
.venv-retention\Scripts\python.exe -m pip install -r requirements-retention.txt
if errorlevel 1 goto fail
if not exist analyst-studio\.env copy analyst-studio\.env.example analyst-studio\.env >nul
.venv-retention\Scripts\python.exe run_retention.py %*
if errorlevel 1 goto fail
exit /b 0
:fail
echo Setup or startup failed. Read the error above. Python 3.11 or 3.12 is required.
if not defined CI pause
exit /b 1
