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
  $child = Start-Process -FilePath $Python -ArgumentList $arguments -PassThru -Wait -WindowStyle Hidden `
    -RedirectStandardOutput (Join-Path $outputPath 'controller.stdout.log') `
    -RedirectStandardError (Join-Path $outputPath 'controller.stderr.log')
  if ($child.ExitCode -eq 0) { break }
  $failures += 1
  Start-Sleep -Seconds ([Math]::Min(300, 15 * $failures))
}
