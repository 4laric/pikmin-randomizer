# Fast-forward a canonical line to a prepared, tested landing branch and push it.
#   land-batch.ps1 root   <sha>   -> codex/p2-main-review (origin)
#   land-batch.ps1 native <sha>   -> claude/p2-deepseek-wave-native (fork)
param([Parameter(Mandatory)][ValidateSet('root','native')]$Side, [Parameter(Mandatory)]$Sha)
$ErrorActionPreference = 'Stop'
Set-Location C:\Users\alari\pikmin-randomizer
if ($Side -eq 'root') { $wt = 'output/p2-main-review'; $repo = '.'; $remote = 'origin'; $line = 'codex/p2-main-review' }
else { $wt = 'output/dsw/native-wave'; $repo = 'native'; $remote = 'fork'; $line = 'claude/p2-deepseek-wave-native' }
if (git -C $wt status --porcelain --untracked-files=no) { throw "$wt has local changes" }
git -C $wt merge --ff-only $Sha
if ($LASTEXITCODE) { throw "fast-forward failed: $line moved since the batch was prepared; tell Claude" }
git -C $repo push $remote $line
if ($LASTEXITCODE) { throw 'push failed' }
"$line -> " + (git -C $repo rev-parse --short $line)
