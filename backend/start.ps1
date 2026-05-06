#Requires -Version 5.0

$RootLauncher = Join-Path (Join-Path $PSScriptRoot "..") "START_SMARTRASH.bat"

if (-not (Test-Path $RootLauncher)) {
    Write-Host "[ERROR] START_SMARTRASH.bat not found at $RootLauncher" -ForegroundColor Red
    exit 1
}

& $RootLauncher @args
exit $LASTEXITCODE
