# Apply reduced-mode merge patch (RFC 7396) to the controller config.
# Usage: .\apply-reduced-mode.ps1 [-WithLanes]   (-WithLanes also merges reduced-lanes.patch.json;
#        only after the 8 lanes are registered and their worktree/brief/opencode.json exist)
param([switch]$WithLanes)
$ErrorActionPreference = 'Stop'
$Repo   = 'C:\Users\alari\pikmin-randomizer'
$Ctl    = Join-Path $Repo 'output\workflow\controller'
$Config = Join-Path $Ctl 'config.json'
$Backup = Join-Path $Ctl 'config.before-reduced-mode.json'
$Here   = $PSScriptRoot
if (-not (Test-Path (Join-Path $Ctl 'STOP'))) { throw 'Controller STOP file missing: stop the controller before editing config.' }
if (Test-Path $Backup) { throw "Backup already exists ($Backup); revert first or remove it deliberately." }
Copy-Item $Config $Backup
$patches = @((Join-Path $Here 'reduced-mode.patch.json'))
if ($WithLanes) { $patches += (Join-Path $Here 'reduced-lanes.patch.json') }
$py = @'
import json, sys, os
def merge(t, p):
    if not isinstance(p, dict): return p
    t = dict(t) if isinstance(t, dict) else {}
    for k, v in p.items():
        if v is None: t.pop(k, None)
        else: t[k] = merge(t.get(k), v)
    return t
cfg_path, patches = sys.argv[1], sys.argv[2:]
cfg = json.load(open(cfg_path, encoding='utf-8-sig'))
for p in patches: cfg = merge(cfg, json.load(open(p, encoding='utf-8-sig')))
tmp = cfg_path + '.tmp'
with open(tmp, 'w', encoding='utf-8') as f: json.dump(cfg, f, indent=2); f.write('\n')
json.load(open(tmp, encoding='utf-8'))
os.replace(tmp, cfg_path)
print('lanes:', sorted(cfg['lanes']))
print('throughput.enabled=%s shepherd=%s queue_pressure=%s' % (cfg['throughput']['enabled'], cfg['shepherd']['enabled'], cfg['queue_pressure']['enabled']))
'@
$tmpPy = Join-Path $env:TEMP 'apply_reduced_mode.py'
Set-Content -Path $tmpPy -Value $py -Encoding utf8
& py $tmpPy $Config @patches
if ($LASTEXITCODE -ne 0) { Copy-Item $Backup $Config -Force; throw 'Patch failed; config restored from backup.' }
Write-Host "Applied. Backup: $Backup"
