param([int]$Port = 8501)
$ErrorActionPreference = 'Stop'
$projectDirectory = $PSScriptRoot
$pythonExecutable = Join-Path $projectDirectory '.venv-ai/Scripts/python.exe'
if (-not (Test-Path -LiteralPath $pythonExecutable)) {
    throw 'Run Install FinScope.cmd first; see README.md.'
}
Set-Location -LiteralPath $projectDirectory
& $pythonExecutable -m finscope.bootstrap --check-dependencies
if ($LASTEXITCODE -ne 0) { throw 'Dependencies missing or incompatible. Run Install FinScope.cmd to repair.' }
$probe = New-Object System.Net.Sockets.TcpListener([System.Net.IPAddress]::Loopback, $Port)
try { $probe.Start() } catch { throw "Port $Port is already in use. Existing processes were left running; choose another -Port." } finally { $probe.Stop() }
$workerDatabase = Join-Path $projectDirectory 'reports/finscope_local.sqlite3'
$workerProcess = Start-Process -FilePath $pythonExecutable -ArgumentList @('-m', 'finscope.local_worker', '--db', ('"' + $workerDatabase + '"')) -WorkingDirectory $projectDirectory -WindowStyle Hidden -PassThru
try {
    & $pythonExecutable -m streamlit run streamlit_app.py --server.address localhost --server.port $Port
} finally {
    if (-not $workerProcess.HasExited) { Stop-Process -Id $workerProcess.Id }
}
