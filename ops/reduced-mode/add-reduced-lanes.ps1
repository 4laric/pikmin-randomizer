# Merge ONLY reduced-lanes.patch.json into the controller config (RFC 7396), after setup-lanes.ps1.
# Refuses unless STOP exists. Lanes whose root dir, brief.md or opencode.json is missing (e.g. the deferred
# rd-demon-chain-b) are left out with a warning; configure-lane-launch's registry launch spec alone also suffices.
# Backup: config.before-reduced-lanes.json (refuses if present). Revert: -Revert.
param([string]$Root = 'C:\Users\alari\pikmin-randomizer', [switch]$Revert)
$ErrorActionPreference = 'Stop'
$Ctl    = Join-Path $Root 'output\workflow\controller'
$Config = Join-Path $Ctl 'config.json'
$Backup = Join-Path $Ctl 'config.before-reduced-lanes.json'
$Source = Join-Path $PSScriptRoot 'reduced-lanes.patch.json'
if (-not (Test-Path (Join-Path $Ctl 'STOP'))) { throw 'Controller STOP file missing: stop the controller before editing config.' }
if ($Revert) {
    if (-not (Test-Path $Backup)) { throw "No backup at $Backup" }
    & py -3.12 -c "import json,sys; json.load(open(sys.argv[1], encoding='utf-8-sig'))" $Backup
    if ($LASTEXITCODE -ne 0) { throw 'Backup is not valid JSON; not restoring.' }
    Copy-Item $Config (Join-Path $Ctl ('config.reduced-lanes-' + (Get-Date -Format 'yyyyMMdd-HHmmss') + '.json'))
    Copy-Item $Backup $Config -Force; Remove-Item $Backup
    Write-Host 'Reverted config.json to the pre-reduced-lanes state.'; return
}
if (Test-Path $Backup) { throw "Backup already exists ($Backup); revert first or remove it deliberately." }
$lanes = (Get-Content $Source -Raw | ConvertFrom-Json).lanes
$missing = @(); $present = [ordered]@{}
foreach ($p in $lanes.PSObject.Properties) {
    $gone = @('root','brief','config' | Where-Object { -not (Test-Path (Join-Path $Root $p.Value.$_)) })
    if ($gone.Count) { $missing += "$($p.Name) (missing $($gone -join ','))" } else { $present[$p.Name] = $p.Value }
}
if ($present.Count -eq 0) { throw 'No prepared lanes; run setup-lanes.ps1 first.' }
if ($missing) { Write-Warning ("Leaving out unprepared lanes:`n  " + ($missing -join "`n  ")) }
$Patch = Join-Path $env:TEMP 'reduced-lanes.present.patch.json'
[IO.File]::WriteAllText($Patch, (@{ lanes = $present } | ConvertTo-Json -Depth 6), (New-Object Text.UTF8Encoding $false))
Copy-Item $Config $Backup
$py = @'
import json, sys, os
def merge(t, p):
    if not isinstance(p, dict): return p
    t = dict(t) if isinstance(t, dict) else {}
    for k, v in p.items():
        if v is None: t.pop(k, None)
        else: t[k] = merge(t.get(k), v)
    return t
cfg_path, patch = sys.argv[1], sys.argv[2]
cfg = merge(json.load(open(cfg_path, encoding='utf-8-sig')), json.load(open(patch, encoding='utf-8-sig')))
tmp = cfg_path + '.tmp'
with open(tmp, 'w', encoding='utf-8') as f: json.dump(cfg, f, indent=2); f.write('\n')
json.load(open(tmp, encoding='utf-8'))
os.replace(tmp, cfg_path)
print('lanes:', sorted(cfg['lanes']))
print('throughput.enabled=%s shepherd=%s' % (cfg['throughput']['enabled'], cfg['shepherd']['enabled']))
'@
$tmpPy = Join-Path $env:TEMP 'add_reduced_lanes.py'
[IO.File]::WriteAllText($tmpPy, $py, (New-Object Text.UTF8Encoding $false))
& py -3.12 $tmpPy $Config $Patch
if ($LASTEXITCODE -ne 0) { Copy-Item $Backup $Config -Force; Remove-Item $Backup; throw 'Patch failed; config restored.' }
Write-Host "Applied. Backup: $Backup"
