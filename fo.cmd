@echo off
setlocal
set "ROOT=%~dp0"
set "ENGINE=%ROOT%family-office-engine"
set "VENV_PY=%ENGINE%\.venv\Scripts\python.exe"

if exist "%VENV_PY%" (
  "%VENV_PY%" -m family_office_engine.cli.main %*
) else (
  python -m family_office_engine.cli.main %*
)
endlocal
