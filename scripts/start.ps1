$ErrorActionPreference = 'Stop'
$projectRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$runtimeRoot = Join-Path $projectRoot '.runtime'
$pgBin = Join-Path $projectRoot '.tools\pgsql\bin'
$nodeRoot = (Get-ChildItem (Join-Path $projectRoot '.tools') -Directory -Filter 'node-*-win-x64' | Select-Object -First 1).FullName
if (-not $nodeRoot) { throw 'Install Node.js into .tools first; see README.md.' }
$env:PATH = "$nodeRoot;$env:PATH"
$pythonPath = Join-Path $projectRoot '.venv\Scripts\python.exe'
New-Item -ItemType Directory -Force $runtimeRoot | Out-Null

function Test-ManagedProcess([int]$ProcessId, [string]$CommandFragment) {
    $process = Get-CimInstance Win32_Process -Filter "ProcessId = $ProcessId" -ErrorAction SilentlyContinue
    return $null -ne $process -and $process.CommandLine -and $process.CommandLine.Contains($CommandFragment) -and $process.ExecutablePath -and $process.ExecutablePath.StartsWith($projectRoot, [System.StringComparison]::OrdinalIgnoreCase)
}

$processFile = Join-Path $runtimeRoot 'processes.json'
if (Test-Path -LiteralPath $processFile) {
    try {
        $recordedProcesses = Get-Content -LiteralPath $processFile -Raw | ConvertFrom-Json
        if ((Test-ManagedProcess $recordedProcesses.backend 'manage.py') -and (Test-ManagedProcess $recordedProcesses.frontend 'vite.js')) {
            Write-Output 'SportHub is already running: http://localhost:5173 (Django API: http://127.0.0.1:8000/api/)'
            return
        }
    } catch {
        # A stale or incomplete process file is replaced after a successful launch.
    }
    Remove-Item -LiteralPath $processFile -Force -ErrorAction SilentlyContinue
}

foreach ($port in 8000, 5173) {
    $listener = Get-NetTCPConnection -State Listen -LocalPort $port -ErrorAction SilentlyContinue | Select-Object -First 1
    if ($listener) { throw "Port $port is already in use. Stop the process using it, then run scripts\\start.ps1 again." }
}

& (Join-Path $pgBin 'pg_ctl.exe') -D (Join-Path $runtimeRoot 'postgres') status *> $null
if ($LASTEXITCODE -ne 0) {
    $pgControl = Start-Process -FilePath (Join-Path $pgBin 'pg_ctl.exe') -ArgumentList @('-D', ('"' + (Join-Path $runtimeRoot 'postgres') + '"'), '-l', ('"' + (Join-Path $runtimeRoot 'postgres.log') + '"'), '-w', 'start') -WindowStyle Hidden -PassThru
    # Wait only for pg_ctl; Start-Process -Wait also waits for its persistent server child.
    $pgControl.WaitForExit()
    if ($pgControl.ExitCode -ne 0) { throw 'PostgreSQL failed to start; see .runtime/postgres.log.' }
}
Push-Location (Join-Path $projectRoot 'backend')
try {
    & $pythonPath manage.py migrate --noinput
    if ($LASTEXITCODE -ne 0) { throw 'Database migrations failed.' }
} finally { Pop-Location }
$backendProcess = Start-Process -FilePath $pythonPath -ArgumentList @('manage.py','runserver','127.0.0.1:8000','--noreload') -WorkingDirectory (Join-Path $projectRoot 'backend') -WindowStyle Hidden -PassThru -RedirectStandardOutput (Join-Path $runtimeRoot 'backend.out.log') -RedirectStandardError (Join-Path $runtimeRoot 'backend.err.log')
$frontendProcess = Start-Process -FilePath (Join-Path $nodeRoot 'node.exe') -ArgumentList @('node_modules/vite/bin/vite.js','--host','127.0.0.1') -WorkingDirectory (Join-Path $projectRoot 'frontend') -WindowStyle Hidden -PassThru -RedirectStandardOutput (Join-Path $runtimeRoot 'frontend.out.log') -RedirectStandardError (Join-Path $runtimeRoot 'frontend.err.log')
@{ backend = $backendProcess.Id; frontend = $frontendProcess.Id } | ConvertTo-Json | Set-Content (Join-Path $runtimeRoot 'processes.json')
Write-Output 'SportHub: http://localhost:5173 (Django API: http://127.0.0.1:8000/api/)'
