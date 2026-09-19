<#
Switch the live workflow controller to the release this script lives in.

  & <root>\output\workflow\release\<sha>\scripts\Deploy-WorkflowRelease.ps1

Run it yourself from an operator shell. It creates the controller STOP file, waits for
every running controller and restart wrapper to exit (workers keep running), removes
STOP, starts Start-Pikmin2Controller.ps1 from this release against the canonical root,
and prints `service status`. If the old controller does not exit within -TimeoutSeconds
it leaves STOP in place and exits 1: rerun once it has stopped. Rolling back is running
the same script from an older release folder.
#>
param(
  [string]$WorkspaceRoot = 'C:\Users\alari\pikmin-randomizer',
  [string]$Config = '',
  [string]$Python = 'C:\Users\alari\AppData\Local\Microsoft\WindowsApps\PythonSoftwareFoundation.Python.3.12_qbz5n2kfra8p0\python.exe',
  [int]$TimeoutSeconds = 900
)
$ErrorActionPreference = 'Stop'
$release = Split-Path -Parent $PSScriptRoot
$wrapper = Join-Path $PSScriptRoot 'Start-Pikmin2Controller.ps1'
$entry = Join-Path $PSScriptRoot 'workflow_module.py'
if (-not $Config) { $Config = Join-Path $WorkspaceRoot 'output\workflow\controller\config.json' }
foreach ($path in @($wrapper, $entry, $Config, $Python)) {
  if (-not (Test-Path -LiteralPath $path)) { throw "Missing $path" }
}
$dirty = & git -C $release status --porcelain
if ($LASTEXITCODE -ne 0 -or $dirty) { throw "Release $release is not a clean git worktree" }
$sha = (& git -C $release rev-parse HEAD).Trim()
$settings = Get-Content -LiteralPath $Config -Raw | ConvertFrom-Json
if (-not $settings.output) { throw "Config $Config lacks output" }
$stop = Join-Path (Join-Path $WorkspaceRoot $settings.output) 'STOP'

function Get-Running {
  Get-CimInstance Win32_Process | Where-Object {
    $_.CommandLine -and ($_.CommandLine -like '*pikmin2_controller.py*' -or $_.CommandLine -like '*Start-Pikmin2Controller.ps1*')
  }
}

Write-Host "Deploying release $sha from $release"
New-Item -ItemType File -Force -Path $stop | Out-Null
$deadline = (Get-Date).AddSeconds($TimeoutSeconds)
while ($running = @(Get-Running)) {
  if ((Get-Date) -gt $deadline) {
    Write-Host "Still running after $TimeoutSeconds s (STOP left in place; rerun when these exit):"
    $running | Select-Object ProcessId, CommandLine | Format-List | Out-String | Write-Host
    exit 1
  }
  Write-Host ("Waiting for {0} controller/wrapper process(es) to exit..." -f $running.Count)
  Start-Sleep -Seconds 5
}
Remove-Item -LiteralPath $stop
$arguments = @('-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', "`"$wrapper`"",
  '-WorkspaceRoot', "`"$WorkspaceRoot`"", '-Config', "`"$Config`"", '-Python', "`"$Python`"")
$started = Start-Process -WindowStyle Hidden -FilePath powershell.exe -ArgumentList $arguments -PassThru
Write-Host "Started wrapper PID $($started.Id); waiting for the controller to claim..."
Start-Sleep -Seconds 20
& $Python $entry service status --root $WorkspaceRoot
