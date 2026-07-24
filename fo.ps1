$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$Engine = Join-Path $Root "family-office-engine"
$VenvPython = Join-Path $Engine ".venv\Scripts\python.exe"

if (Test-Path -LiteralPath $VenvPython) {
    & $VenvPython -m family_office_engine.cli.main @args
} else {
    & python -m family_office_engine.cli.main @args
}
