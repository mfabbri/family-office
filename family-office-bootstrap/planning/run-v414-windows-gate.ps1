# Local deterministic Windows test runner. No Codex or model calls.
# Requires the Engine virtual environment, does not alter user-wide TEMP settings.
[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)] [string]$RepoRoot,
    [switch]$PreflightOnly,
    [switch]$FullSuite
)
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
if ($PreflightOnly -and $FullSuite) { throw 'Use -PreflightOnly or -FullSuite, not both.' }
$RepoRoot = [IO.Path]::GetFullPath($RepoRoot)
$engineRoot = Join-Path $RepoRoot 'family-office-engine'
$py = Join-Path $engineRoot '.venv\Scripts\python.exe'
$preflight = Join-Path $RepoRoot 'family-office-bootstrap\planning\test-temp-preflight.py'
if (-not (Test-Path -LiteralPath (Join-Path $RepoRoot 'AGENTS.md') -PathType Leaf)) { throw 'Invalid RepoRoot: AGENTS.md missing.' }
if (-not (Test-Path -LiteralPath $py -PathType Leaf)) { throw "Engine venv is required: $py" }
if (-not (Test-Path -LiteralPath $preflight -PathType Leaf)) { throw "Preflight script missing: $preflight" }

# Local .runtime is explicitly gitignored by family-office-bootstrap/.gitignore.
# Each run uses a new directory; never delete another run's artifacts.
$baseDir = Join-Path $RepoRoot 'family-office-bootstrap\planning\.runtime\test-gate'
$runId = [DateTime]::UtcNow.ToString('yyyyMMdd-HHmmss') + '-' + [Guid]::NewGuid().ToString('N').Substring(0, 8)
$runDir = Join-Path $baseDir $runId
$scratch = Join-Path $runDir 'scratch'
New-Item -ItemType Directory -Path $scratch -Force | Out-Null
$summaryPath = Join-Path $runDir 'summary.json'

$previous = @{
    TEMP = [Environment]::GetEnvironmentVariable('TEMP', 'Process')
    TMP = [Environment]::GetEnvironmentVariable('TMP', 'Process')
    TMPDIR = [Environment]::GetEnvironmentVariable('TMPDIR', 'Process')
    PYTHONPATH = [Environment]::GetEnvironmentVariable('PYTHONPATH', 'Process')
    PYTHONDONTWRITEBYTECODE = [Environment]::GetEnvironmentVariable('PYTHONDONTWRITEBYTECODE', 'Process')
}
$results = New-Object 'System.Collections.Generic.List[object]'
$testExit = 0
try {
    # Constrain the subprocess's temp directory to the writable workspace.
    # This does NOT change test inputs, assertions, coverage or exit criteria.
    $env:TEMP = $scratch
    $env:TMP = $scratch
    $env:TMPDIR = $scratch
    $env:PYTHONDONTWRITEBYTECODE = '1'
    $src = Join-Path $engineRoot 'src'
    $env:PYTHONPATH = if ($previous.PYTHONPATH) { $src + [IO.Path]::PathSeparator + $previous.PYTHONPATH } else { $src }

    Write-Host "Test run: $runDir"
    Write-Host "Python: $py"
    $preflightOut = Join-Path $runDir 'preflight.json'
    $preflightErr = Join-Path $runDir 'preflight.stderr.log'
    # unittest and Python emit normal diagnostics to stderr. PS 5.1 can otherwise
    # misclassify native stderr as terminating NativeCommandError.
    $ErrorActionPreference = 'Continue'
    try {
        & $py $preflight --expected-parent $scratch 1> $preflightOut 2> $preflightErr
        $preflightExit = [int]$LASTEXITCODE
    } finally { $ErrorActionPreference = 'Stop' }
    if ($preflightExit -ne 0) {
        Get-Content -LiteralPath $preflightErr | Write-Host
        throw "TEMP preflight failed; suite not started. Investigate ACL/sandbox. Evidence: $runDir"
    }
    Write-Host 'TEMP write/read/cleanup preflight: PASS' -ForegroundColor Green
    if ($PreflightOnly) { return }

    Push-Location $engineRoot
    try {
        $cases = @(
            @{ name='rules-v6'; args=@('-m','unittest','discover','-s','tests/unit','-p','test_italian_old_age_rule_pack_v6.py') },
            @{ name='citation-index'; args=@('-m','unittest','discover','-s','tests/unit','-p','test_citation_index.py') }
        )
        if ($FullSuite) {
            $cases += @{ name='complete-engine'; args=@('-m','unittest','discover','-s','tests/unit','-p','test_*.py') }
        }
        foreach ($case in $cases) {
            $caseLog = Join-Path $runDir ($case.name + '.stderr.log')
            $caseStdout = Join-Path $runDir ($case.name + '.stdout.log')
            $commandArgs = [string[]]$case['args']
            $ErrorActionPreference = 'Continue'
            try {
                & $py @commandArgs 1> $caseStdout 2> $caseLog
                $rc = [int]$LASTEXITCODE
            } finally { $ErrorActionPreference = 'Stop' }
            $raw = (Get-Content -LiteralPath $caseLog -Raw -Encoding UTF8) + "`n" +
                   (Get-Content -LiteralPath $caseStdout -Raw -Encoding UTF8)
            $ranMatch = [regex]::Match($raw, 'Ran\s+(\d+)\s+tests?\s+in\s+')
            $ran = if ($ranMatch.Success) { [int]$ranMatch.Groups[1].Value } else { $null }
            $failureCount = 0; $errorCount = 0; $skippedCount = 0
            $failureMatch = [regex]::Match($raw, 'failures\s*=\s*(\d+)')
            $errorMatch = [regex]::Match($raw, 'errors\s*=\s*(\d+)')
            $skipMatch = [regex]::Match($raw, 'skipped\s*=\s*(\d+)')
            if ($failureMatch.Success) { $failureCount = [int]$failureMatch.Groups[1].Value }
            if ($errorMatch.Success) { $errorCount = [int]$errorMatch.Groups[1].Value }
            if ($skipMatch.Success) { $skippedCount = [int]$skipMatch.Groups[1].Value }
            $pass = ($rc -eq 0 -and $null -ne $ran -and $failureCount -eq 0 -and $errorCount -eq 0 -and $skippedCount -eq 0 -and $raw -match '(?m)^OK\s*$')
            $results.Add([pscustomobject]@{
                name=$case.name; exit_code=$rc; tests=$ran; failures=$failureCount;
                errors=$errorCount; skipped=$skippedCount; passed=$pass; log=$caseLog
            })
            $state = if ($pass) { 'PASS' } else { 'FAIL' }
            Write-Host "$($case.name): $state (tests=$ran; failures=$failureCount; errors=$errorCount; skipped=$skippedCount; exit=$rc)"
            if (-not $pass) {
                Write-Host "Last 24 log lines ($caseLog):" -ForegroundColor Yellow
                Get-Content -LiteralPath $caseLog -Tail 24 | Write-Host
                $testExit = 1
                break # Do not cascade into 1,000 tests if a prerequisite is broken.
            }
        }
    } finally { Pop-Location }
    $results | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath $summaryPath -Encoding UTF8
    if ($testExit -ne 0) { throw "Gate FAILED. No state changes were made. Evidence: $runDir" }
    Write-Host "Technical test gate PASSED for requested scope. Evidence: $summaryPath" -ForegroundColor Green
    Write-Host 'Note: test PASS does not confer a normative GO or automatically complete V4.14.'
} finally {
    foreach ($name in $previous.Keys) {
        [Environment]::SetEnvironmentVariable($name, $previous[$name], 'Process')
    }
    # Preserve per-run log evidence; delete only this run's isolated scratch tree.
    $safeBase = [IO.Path]::GetFullPath($baseDir).TrimEnd('\','/') + [IO.Path]::DirectorySeparatorChar
    $safeScratch = [IO.Path]::GetFullPath($scratch)
    if ($safeScratch.StartsWith($safeBase, [StringComparison]::OrdinalIgnoreCase) -and
        (Test-Path -LiteralPath $scratch -PathType Container)) {
        try { Remove-Item -LiteralPath $scratch -Recurse -Force -ErrorAction Stop }
        catch { Write-Warning "Could not clean scratch (access/lock): $scratch - $($_.Exception.Message)" }
    }
}
