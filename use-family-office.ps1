$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$Engine = Join-Path $Root "family-office-engine"
$VenvScripts = Join-Path $Engine ".venv\Scripts"
$FoExe = Join-Path $VenvScripts "fo.exe"

if (-not (Test-Path -LiteralPath $FoExe)) {
    $Python = Join-Path $VenvScripts "python.exe"
    if (-not (Test-Path -LiteralPath $Python)) {
        throw "Missing engine venv Python: $Python"
    }
    & $Python -m pip install -e $Engine
}

$PathParts = $env:Path -split [IO.Path]::PathSeparator
if ($PathParts -notcontains $VenvScripts) {
    $env:Path = $VenvScripts + [IO.Path]::PathSeparator + $env:Path
}

$env:FO_BOOTSTRAP_PATH = Join-Path $Root "family-office-bootstrap"
$env:FO_ENGINE_PATH = $Engine
$env:FO_RULES_PATH = Join-Path $Root "family-office-rules"
$env:FO_KNOWLEDGE_PATH = Join-Path $Root "family-office-knowledge"
$env:FO_WORKSPACE_PATH = Join-Path $Root "family-office-workspace"

Write-Host "Family Office CLI ready. Try: fo validate"
