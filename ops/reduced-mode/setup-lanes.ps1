# Prepare and register the reduced-mode lanes (idempotent; rerun safely after fixing a refusal).
# Per lane: root worktree (+ native worktree) off the canonical lines, brief.md, opencode.json, run/,
# then `pikmin2_workflow.py provision-pool-lane` and `configure-lane-launch` (this release's CLI).
# Usage (call in-process with &, never powershell -File: -File splits the -Lanes array):
#   & <release>\ops\reduced-mode\setup-lanes.ps1 -Root <workspace> -Lanes @('rd-a','rd-b') [-IncludeDeferred] [-DryRun]
# Reads <workspace>\output\reduced\lanes.json and output\reduced\briefs\brief-<lane without rd->.md.
param(
    [string]$Root = 'C:\Users\alari\pikmin-randomizer',
    [string]$Db = '',
    [string]$Manifest = '',
    [string[]]$Lanes = @(),
    [switch]$IncludeDeferred,
    [switch]$DryRun
)
$ErrorActionPreference = 'Stop'
$Here     = $PSScriptRoot
$Release  = (Resolve-Path (Join-Path $Here '..\..')).Path   # the release worktree this toolkit ships in
$Cli      = Join-Path $Release 'scripts\pikmin2_workflow.py'
$Helper   = Join-Path $Here 'reduced_setup.py'
if (-not $Manifest) { $Manifest = Join-Path $Root 'output\reduced\lanes.json' }
$ManifestPath = $Manifest
$M = Get-Content $ManifestPath -Raw | ConvertFrom-Json
$Native   = Join-Path $Root 'native'
if (-not $Db) { $Db = Join-Path $Root 'output\workflow\registry.sqlite3' }
if (-not (Test-Path (Join-Path $Root 'output\workflow\controller\STOP'))) { throw 'Controller STOP file missing: stop the controller first.' }
$Models = (Get-Content (Join-Path $Root 'output\workflow\controller\config.json') -Raw | ConvertFrom-Json).models
$AllLanes = @($M.lanes.PSObject.Properties.Name)
if ($Lanes.Count -eq 0) { $Lanes = @($AllLanes | Where-Object { $IncludeDeferred -or -not $M.lanes.$_.defer }) }

function Invoke-Git([string]$Repo) { $ErrorActionPreference = "Continue"; & git.exe -C $Repo @args 2>&1 | ForEach-Object { "$_" }; if ($LASTEXITCODE -ne 0) { throw "git -C $Repo $args failed" } }
function Invoke-Cli([string]$Command, [string]$Request) {
    $ErrorActionPreference = "Continue"; $out = & py -3.12 $Cli --root $Root --db $Db --request $Request $Command
    if ($LASTEXITCODE -ne 0) { throw "$Command failed for $Request (exit $LASTEXITCODE)" }
    $out
}
function Add-Worktree([string]$Repo, [string]$Path, [string]$Branch, [string]$Base) {
    if (Test-Path $Path) {
        $cur = (& git -C $Path rev-parse --abbrev-ref HEAD)
        if ($Branch -and $cur -ne $Branch) { throw "$Path exists on '$cur', expected '$Branch'" }
        Write-Host "  exists: $Path ($cur)"; return
    }
    if ($DryRun) { Write-Host "  would: git -C $Repo worktree add $(if ($Branch) {"-b $Branch"} else {'--detach'}) $Path $Base"; return }
    if ($Branch) {
        & git -C $Repo show-ref --verify --quiet "refs/heads/$Branch"
        if ($LASTEXITCODE -eq 0) { throw "Branch $Branch already exists in $Repo but $Path does not; resolve by hand." }
        Invoke-Git $Repo worktree add -b $Branch $Path $Base
    } else { Invoke-Git $Repo worktree add --detach $Path $Base }
}

$rootLine = (& git -C $Root rev-parse $M.root_line); if ($LASTEXITCODE) { throw 'root line missing' }
$nativeLine = (& git -C $Native rev-parse $M.native_line); if ($LASTEXITCODE) { throw 'native line missing' }
Write-Host "root line $($M.root_line) = $rootLine; native line $($M.native_line) = $nativeLine"

foreach ($lane in $Lanes) {
    $spec = $M.lanes.$lane
    if (-not $spec) { throw "Unknown lane $lane" }
    Write-Host "== $lane ($($spec.kind))"
    $dir = Join-Path $Root "output\reduced\$lane"
    if (-not $DryRun) { New-Item -ItemType Directory -Force (Join-Path $dir 'run') | Out-Null }
    if ($spec.kind -eq 'root') {
        Add-Worktree $Root (Join-Path $dir 'root') $spec.branch $M.root_line
    } else {
        Add-Worktree $Root (Join-Path $dir 'root') '' $M.root_line          # notes only, detached
        Add-Worktree $Native (Join-Path $dir 'native') $spec.branch $M.native_line
    }
    $brief = Join-Path $Root ('output\reduced\briefs\brief-' + $lane.Substring(3) + '.md')
    # opencode.json: managed format (no external_directory, no top-level '*') so the controller adds the
    # workspace-wide external_directory itself (managed_config.output_access); edits denied outside this lane.
    $deny = [ordered]@{ '*' = 'allow' }
    $deny[($Root -replace '\\','/') + '/native/**'] = 'deny'
    foreach ($p in 'output/dsw/**','output/p2-main-review/**','output/workflow/**') { $deny[($Root -replace '\\','/') + '/' + $p] = 'deny' }
    foreach ($o in $AllLanes) { if ($o -ne $lane) { $deny[($Root -replace '\\','/') + "/output/reduced/$o/**"] = 'deny' } }
    $cfg = [ordered]@{ '$schema' = 'https://opencode.ai/config.json'; model = $Models[0];
                       permission = [ordered]@{ task = 'deny'; question = 'deny'; edit = $deny } }
    if ($DryRun) { Write-Host "  would write brief.md, opencode.json (model $($Models[0]))"; continue }
    Copy-Item $brief (Join-Path $dir 'brief.md') -Force
    [IO.File]::WriteAllText((Join-Path $dir 'opencode.json'), ($cfg | ConvertTo-Json -Depth 5), (New-Object Text.UTF8Encoding $false))
    $ErrorActionPreference = "Continue"
    & py -3.12 $Helper request --root $Root --db $Db --manifest $ManifestPath --lane $lane
    $rc = $LASTEXITCODE; $ErrorActionPreference = "Stop"
    if ($rc -ne 0) { throw "request validation refused $lane (reason above)" }
    $prov = Join-Path $dir 'provision-request.json'
    if (Test-Path $prov) {
        Invoke-Cli 'provision-pool-lane' $prov | Out-Null
        Move-Item $prov (Join-Path $dir 'provision-request.applied.json') -Force
        Write-Host '  provisioned'
    }
    Invoke-Cli 'configure-lane-launch' (Join-Path $dir 'configure-request.json') | Out-Null
    Write-Host '  launch configured'
}
Write-Host 'Done. Next: add-reduced-lanes.ps1, then reduced_setup.py validate / kickoff.'
