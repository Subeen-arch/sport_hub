$ErrorActionPreference = 'Stop'
$projectRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$runtimeRoot = Join-Path $projectRoot '.runtime'
$processFile = Join-Path $runtimeRoot 'processes.json'
if (Test-Path -LiteralPath $processFile) {
    $recordedProcesses = Get-Content -LiteralPath $processFile -Raw | ConvertFrom-Json
    foreach ($processId in @($recordedProcesses.backend, $recordedProcesses.frontend)) {
        $running = Get-CimInstance Win32_Process -Filter "ProcessId = $processId" -ErrorAction SilentlyContinue
        if ($running -and $running.CommandLine -and ($running.CommandLine.Contains('manage.py') -or $running.CommandLine.Contains('vite.js')) -and $running.ExecutablePath.StartsWith($projectRoot, [System.StringComparison]::OrdinalIgnoreCase)) {
            Stop-Process -Id $processId
        }
    }
    Remove-Item -LiteralPath $processFile
}
& (Join-Path $projectRoot '.tools\pgsql\bin\pg_ctl.exe') -D (Join-Path $runtimeRoot 'postgres') -m fast -w stop
