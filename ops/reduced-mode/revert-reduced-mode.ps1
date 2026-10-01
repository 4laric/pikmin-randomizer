# Restore the controller config saved by apply-reduced-mode.ps1.
$ErrorActionPreference = 'Stop'
$Ctl    = 'C:\Users\alari\pikmin-randomizer\output\workflow\controller'
$Config = Join-Path $Ctl 'config.json'
$Backup = Join-Path $Ctl 'config.before-reduced-mode.json'
if (-not (Test-Path (Join-Path $Ctl 'STOP'))) { throw 'Controller STOP file missing: stop the controller before editing config.' }
if (-not (Test-Path $Backup)) { throw "No backup at $Backup" }
Copy-Item $Config (Join-Path $Ctl ('config.reduced-mode-' + (Get-Date -Format 'yyyyMMdd-HHmmss') + '.json'))
& py -c "import json,sys; json.load(open(sys.argv[1], encoding='utf-8-sig'))" $Backup
if ($LASTEXITCODE -ne 0) { throw 'Backup is not valid JSON; not restoring.' }
Copy-Item $Backup $Config -Force
Remove-Item $Backup
Write-Host 'Reverted config.json to pre-reduced-mode state (reduced config kept as config.reduced-mode-<stamp>.json).'
