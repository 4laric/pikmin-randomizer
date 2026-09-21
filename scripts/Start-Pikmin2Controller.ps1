param(
  [Parameter(Mandatory=$true)][string]$WorkspaceRoot,
  [Parameter(Mandatory=$true)][string]$Config,
  [string]$Python = 'python.exe',
  [int]$RestartDelaySeconds = 15,
  [int]$KeepCrashLogs = 20
)
$ErrorActionPreference = 'Stop'
$implementation = Join-Path $PSScriptRoot 'pikmin2_controller.py'
$settings = Get-Content -LiteralPath $Config -Raw | ConvertFrom-Json
$outputPath = Join-Path $WorkspaceRoot $settings.output
$stopPath = Join-Path $outputPath 'STOP'
New-Item -ItemType Directory -Force -Path $outputPath | Out-Null
$failures = 0
while (-not (Test-Path -LiteralPath $stopPath)) {
  $arguments = @("`"$implementation`"", '--root', "`"$WorkspaceRoot`"", '--config', "`"$Config`"")
  $child = Start-Process -FilePath $Python -ArgumentList $arguments -PassThru -WindowStyle Hidden `
    -RedirectStandardOutput (Join-Path $outputPath 'controller.stdout.log') `
    -RedirectStandardError (Join-Path $outputPath 'controller.stderr.log')
  # Start-Process -Wait waits for descendants too (including independent agents).
  # Wait only for the controller so a crash can be reconciled while its workers live.
  $null = $child.Handle # Retain the handle so PowerShell exposes the real exit code.
  $child.WaitForExit()
  $code = $child.ExitCode
  if ($code -eq 0) { break }
  # The next Start-Process truncates both logs: move a failed run's output aside first, keep the
  # newest $KeepCrashLogs per stream, and leave a note the next controller records as an event.
  $stamp = (Get-Date).ToUniversalTime().ToString('yyyyMMddTHHmmssZ')
  $saved = @{}
  foreach ($stream in @('stdout', 'stderr')) {
    $source = Join-Path $outputPath "controller.$stream.log"
    $target = Join-Path $outputPath "controller.$stamp.exit$code.$stream.log"
    try {
      if (Test-Path -LiteralPath $source) {
        Move-Item -LiteralPath $source -Destination $target -Force
        $saved[$stream] = $target
      }
      Get-ChildItem -LiteralPath $outputPath -Filter "controller.*.exit*.$stream.log" |
        Sort-Object Name -Descending | Select-Object -Skip $KeepCrashLogs | Remove-Item -Force
    } catch {
      Write-Warning "Could not preserve controller $stream log: $_"
    }
  }
  $note = [ordered]@{ previous_pid = $child.Id; exit_code = $code; stderr_log = $saved['stderr'];
    stdout_log = $saved['stdout']; stamp = $stamp; at = [DateTimeOffset]::UtcNow.ToUnixTimeSeconds() }
  try {
    $note | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $outputPath 'controller-exit.json') -Encoding UTF8
  } catch {
    Write-Warning "Could not write controller exit note: $_"
  }
  $failures += 1
  Start-Sleep -Seconds ([Math]::Min(300, $RestartDelaySeconds * $failures))
}
