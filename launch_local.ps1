param([int]$Port = 8501)
$ErrorActionPreference = 'Stop'
$projectDirectory = $PSScriptRoot
$pythonExecutable = Join-Path $projectDirectory '.venv-ai/Scripts/python.exe'
if (-not (Test-Path -LiteralPath $pythonExecutable)) {
    throw 'Create .venv-ai and install requirements-local.txt first; see README.md.'
}
Set-Location -LiteralPath $projectDirectory
$workerDatabase = Join-Path $projectDirectory 'reports/finscope_local.sqlite3'
$workerProcess = Start-Process -FilePath $pythonExecutable -ArgumentList @('-m', 'finscope.local_worker', '--db', ('"' + $workerDatabase + '"')) -WorkingDirectory $projectDirectory -WindowStyle Hidden -PassThru
try {
    & $pythonExecutable -m streamlit run streamlit_app.py --server.address localhost --server.port $Port
} finally {
    if (-not $workerProcess.HasExited) { Stop-Process -Id $workerProcess.Id }
}
