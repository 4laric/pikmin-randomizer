param(
  [Parameter(Mandatory=$true)][string]$WorkspaceRoot,
  [Parameter(Mandatory=$true)][string]$Config,
  [string]$Python = 'python.exe'
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
  if ($child.ExitCode -eq 0) { break }
  $failures += 1
  Start-Sleep -Seconds ([Math]::Min(300, 15 * $failures))
}
