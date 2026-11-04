param([string]$PythonPath = '', [switch]$NoLaunch)
$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
try {
    if (-not $PythonPath) {
        $existing = Join-Path $PSScriptRoot '.venv-ai\Scripts\python.exe'
        if (Test-Path -LiteralPath $existing) { $PythonPath = $existing }
        elseif (Get-Command py -ErrorAction SilentlyContinue) {
            foreach ($version in @('-3.12','-3.11')) {
                try {
                    $candidate = & py $version -c 'import sys; print(sys.executable)' 2>$null
                    if ($LASTEXITCODE -eq 0) { $PythonPath = $candidate; break }
                } catch { }
            }
        }
        elseif (Get-Command python -ErrorAction SilentlyContinue) { $PythonPath = (Get-Command python).Source }
    }
    if (-not $PythonPath -or -not (Test-Path -LiteralPath $PythonPath)) {
        throw 'Install 64-bit Python 3.11 or 3.12 from https://www.python.org/downloads/windows/ then run again. You can pass -PythonPath to select it.'
    }
    & $PythonPath -m finscope.bootstrap --check
    if ($LASTEXITCODE -ne 0) { throw 'Python/path/disk preflight failed. See the message above.' }
    Write-Host 'First installation downloads Python packages, not model weights. Daily launch does not install packages.'
    if ((Read-Host 'Create/repair .venv-ai and install requirements-install.txt? [y/N]') -ne 'y') { exit 0 }
    & $PythonPath -m finscope.bootstrap
    if ($LASTEXITCODE -ne 0) { throw 'Installation incomplete. Fix the reported error and rerun this installer.' }
    if (-not $NoLaunch) { & (Join-Path $PSScriptRoot 'launch_local.ps1') -Port 8511 }
} catch { Write-Host $_ -ForegroundColor Red; exit 1 }
