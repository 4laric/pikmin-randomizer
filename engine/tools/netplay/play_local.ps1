# Local two-window netplay test (issue #887): one human, two windows on one
# PC. The host plays on the keyboard, the joiner on the first gamepad. No
# environment variables and no files to prepare.
#
# Usage (from any folder; every path may contain spaces):
#   tools\netplay\play_local.bat -Exe <path\to\netplay\nectar.exe>
#       [-Assets <game assets folder>] [-Bootstrap <seed bootstrap.txt>]
#       [-OutDir <work folder>] [-HostInput keyboard] [-JoinInput gamepad:0]
#
# What it does:
#   * gives each peer its own working folder under -OutDir (host\, join\)
#     with an `assets` junction to the game assets and its own settings file
#     (pikmin_settings.conf is read from the working folder);
#   * starts the host (--netplay-host-ice), waits until its offer code file
#     is complete (written atomically), then starts the joiner with that file
#     (--netplay-join-ice @offer.txt); the joiner's answer file is the host's
#     --netplay-answer-in, so no copy-paste is needed;
#   * uses loopback ICE host candidates only (PIKMIN_NETPLAY_STUN=none), so no
#     public STUN server is contacted;
#   * each peer's memory card, campaign files and logs stay private: the game
#     puts them in a fresh run folder under <exe folder>\netplay\ (see
#     docs\NETPLAY_PLAY.md), and each peer's console output goes to
#     <OutDir>\host\native.log / <OutDir>\join\native.log;
#   * stops only the two processes it started, on every exit path.
#
# Windows: both open windowed at -WindowSize (default 960x540), centred on
# the screen, so drag one aside; -WindowSize off keeps each peer's setting.
# Assets: -Assets, else <exe folder>\assets, else
# %APPDATA%\PikminRandomizer\game-data\assets (the installed game data).
# DLLs: when SDL2.dll is not next to the exe (a build tree), the MinGW runtime
# folder C:\msys64\mingw64\bin is put first on PATH for the two peers.
#
# -Hidden is the automated test mode: both windows hidden
# (--netplay-test-hidden), bounded (--netplay-test-ticks -Ticks and a hard
# -TimeoutSec), private, and -HostInputFile/-JoinInputFile feed scripted
# inputs (PIKMIN_NETPLAY_LOCAL_INPUT_FILE) with per-peer hash logs. It is the
# same script path as the visible run otherwise. Never run the visible mode
# from automation.
param(
    [Parameter(Mandatory = $true)][string]$Exe,
    [string]$Assets = "",
    [string]$Bootstrap = "",
    [string]$OutDir = "",
    [string]$HostInput = "keyboard",
    [string]$JoinInput = "gamepad:0",
    [switch]$Hidden,
    [int]$Ticks = 3000,
    [int]$TimeoutSec = 1200,
    [string]$HostInputFile = "",
    [string]$JoinInputFile = "",
    [int]$PortBase = 0,
    [string]$WindowSize = "960x540"
)

$ErrorActionPreference = "Stop"

# Windows command-line quoting for one argument (CommandLineToArgvW rules).
function Quote-Arg([string]$s) {
    if ($s -ne "" -and $s -notmatch '[\s"]') { return $s }
    $out = '"'
    $bs = 0
    foreach ($ch in $s.ToCharArray()) {
        if ($ch -eq '\') { $bs++; continue }
        if ($ch -eq '"') { $out += ('\' * (2 * $bs + 1)) + '"'; $bs = 0; continue }
        $out += ('\' * $bs) + $ch
        $bs = 0
    }
    return $out + ('\' * (2 * $bs)) + '"'
}
function Join-Args([string[]]$list) { return ($list | ForEach-Object { Quote-Arg $_ }) -join ' ' }

$exePath = (Resolve-Path -LiteralPath $Exe).Path
$exeDir = Split-Path -Parent $exePath

if ($Assets -eq "") {
    $candidates = @((Join-Path $exeDir "assets"))
    if ($env:APPDATA) { $candidates += (Join-Path $env:APPDATA "PikminRandomizer\game-data\assets") }
    foreach ($c in $candidates) {
        if ((Test-Path -LiteralPath $c) -and (Get-ChildItem -LiteralPath $c | Where-Object { $_.Name -ne "README.md" } | Select-Object -First 1)) {
            $Assets = $c; break
        }
    }
    if ($Assets -eq "") { throw "play_local: no game assets found; pass -Assets <folder with the game's assets>" }
}
$assetsPath = (Resolve-Path -LiteralPath $Assets).Path

if ($OutDir -eq "") {
    $base = if ($env:LOCALAPPDATA) { $env:LOCALAPPDATA } else { [IO.Path]::GetTempPath() }
    $OutDir = Join-Path $base "Nectar\netplay-local"
}
New-Item -ItemType Directory -Force -Path $OutDir | Out-Null
$root = (Resolve-Path -LiteralPath $OutDir).Path
$hostDir = Join-Path $root "host"
$joinDir = Join-Path $root "join"
foreach ($d in @($hostDir, $joinDir)) {
    New-Item -ItemType Directory -Force -Path $d | Out-Null
    $link = Join-Path $d "assets"
    if (-not (Test-Path -LiteralPath $link)) {
        New-Item -ItemType Junction -Path $link -Target $assetsPath | Out-Null
    }
}
$offerFile = Join-Path $root "offer.txt"
$answerFile = Join-Path $root "answer.txt"
foreach ($f in @($offerFile, $answerFile, "$offerFile.tmp", "$answerFile.tmp")) {
    Remove-Item -LiteralPath $f -Force -ErrorAction SilentlyContinue
}

# Environment for the two peers (inherited by Start-Process).
$env:PIKMIN_NETPLAY_STUN = "none"
# Loopback-only sockets for the local test: Windows Firewall never prompts
# for a socket bound to 127.0.0.1 (real two-PC play binds every interface).
$env:PIKMIN_NETPLAY_ICE_BIND = "127.0.0.1"
$env:PIKMIN_NETPLAY_UDP_BIND = "127.0.0.1"
if (-not (Test-Path -LiteralPath (Join-Path $exeDir "SDL2.dll")) -and (Test-Path "C:\msys64\mingw64\bin\SDL2.dll")) {
    $env:PATH = "C:\msys64\mingw64\bin;" + $env:PATH
}
if ($Hidden) {
    $env:PIKMIN_RANDOMIZER_TEST_BACKGROUND = "1"
    $env:SDL_AUDIODRIVER = "dummy"
} elseif ($WindowSize -ne "" -and $WindowSize -ne "off") {
    # Two borderless full-screen windows would cover each other: open both
    # windowed at this size, centred (drag one aside). Presentation only.
    $env:PIKMIN_P2_ROOM_WINDOW = $WindowSize
}

$hostArgs = @("--netplay-host-ice", "--netplay-code-out", $offerFile,
              "--netplay-answer-in", $answerFile, "--netplay-input", $HostInput)
$joinArgs = @("--netplay-join-ice", "@$offerFile", "--netplay-code-out", $answerFile,
              "--netplay-input", $JoinInput)
if ($Bootstrap -ne "") {
    $hostArgs += @("--bootstrap", (Resolve-Path -LiteralPath $Bootstrap).Path)
}
if ($Hidden) {
    $hostArgs += @("--netplay-test-hidden", "--netplay-test-ticks", "$Ticks")
    $joinArgs += @("--netplay-test-hidden", "--netplay-test-ticks", "$Ticks")
}

function Start-Peer([string]$dir, [string[]]$argList, [string]$inputFile, [int]$portBegin) {
    # Per-peer variables are set right before Start-Process (which captures
    # the environment) and cleared after.
    if ($Hidden) {
        $env:PIKMIN_STATE_HASH_LOG = Join-Path $dir "hashes.txt"
        if ($inputFile -ne "") { $env:PIKMIN_NETPLAY_LOCAL_INPUT_FILE = (Resolve-Path -LiteralPath $inputFile).Path }
    }
    if ($portBegin -gt 0) {
        $env:PIKMIN_NETPLAY_ICE_PORT_BEGIN = "$portBegin"
        $env:PIKMIN_NETPLAY_ICE_PORT_END = "$($portBegin + 9)"
    }
    $sp = @{
        FilePath               = $exePath
        ArgumentList           = (Join-Args $argList)
        WorkingDirectory       = $dir
        RedirectStandardOutput = (Join-Path $dir "native.log")
        RedirectStandardError  = (Join-Path $dir "native.err.log")
        PassThru               = $true
    }
    if ($Hidden) { $sp.WindowStyle = "Hidden" } else { $sp.NoNewWindow = $true }
    try {
        $proc = Start-Process @sp
        # Windows PowerShell 5.1 only reports ExitCode for a Start-Process
        # object whose handle was opened while the process ran.
        $null = $proc.Handle
        return $proc
    } finally {
        Remove-Item Env:PIKMIN_STATE_HASH_LOG, Env:PIKMIN_NETPLAY_LOCAL_INPUT_FILE, Env:PIKMIN_NETPLAY_ICE_PORT_BEGIN, Env:PIKMIN_NETPLAY_ICE_PORT_END -ErrorAction SilentlyContinue
    }
}

function Wait-Code([string]$path, $procs, [string]$what, [int]$seconds) {
    $deadline = [DateTime]::Now.AddSeconds($seconds)
    while ([DateTime]::Now -lt $deadline) {
        if (Test-Path -LiteralPath $path) {
            $text = (Get-Content -LiteralPath $path -Raw -ErrorAction SilentlyContinue)
            if ($text -and $text.Trim().StartsWith("NPIX")) { return $text.Trim() }
        }
        foreach ($p in $procs) {
            if ($p.HasExited) { throw "play_local: $what not produced: pid $($p.Id) exited with $($p.ExitCode); see its native.log" }
        }
        Start-Sleep -Milliseconds 200
    }
    throw "play_local: timed out waiting for the $what"
}

Write-Host "play_local: exe      $exePath"
Write-Host "play_local: assets   $assetsPath"
Write-Host "play_local: peers    $hostDir (host, $HostInput) and $joinDir (joiner, $JoinInput)"
$hostProc = $null
$joinProc = $null
$started = @()
try {
    $hostProc = Start-Peer $hostDir $hostArgs $HostInputFile $PortBase
    $started += $hostProc
    Write-Host "play_local: host started (pid $($hostProc.Id)); waiting for its offer code ..."
    $offer = Wait-Code $offerFile @($hostProc) "offer code" 180
    Write-Host "play_local: offer ready ($($offer.Length) chars); starting the joiner ..."
    $joinProc = Start-Peer $joinDir $joinArgs $JoinInputFile $(if ($PortBase -gt 0) { $PortBase + 10 } else { 0 })
    $started += $joinProc
    Write-Host "play_local: joiner started (pid $($joinProc.Id))"
    if ($Hidden) {
        $deadline = [DateTime]::Now.AddSeconds($TimeoutSec)
        foreach ($p in $started) {
            $left = [int][Math]::Max(1, ($deadline - [DateTime]::Now).TotalMilliseconds)
            if (-not $p.WaitForExit($left)) { Write-Host "play_local: pid $($p.Id) still running at the timeout" }
        }
    } else {
        Write-Host "play_local: both windows are up. The keyboard window is the host; the gamepad"
        Write-Host "play_local: drives the joiner even while the host window has focus. Close both"
        Write-Host "play_local: game windows (or press Ctrl+C here) to finish."
        Wait-Process -Id ($started | ForEach-Object { $_.Id })
    }
} finally {
    foreach ($p in $started) {
        if ($p -and -not $p.HasExited) {
            Write-Host "play_local: stopping pid $($p.Id)"
            Stop-Process -Id $p.Id -Force -ErrorAction SilentlyContinue
        }
    }
    foreach ($p in $started) {
        if ($p) { $p.WaitForExit(10000) | Out-Null }
    }
    $hostExit = if ($hostProc -and $hostProc.HasExited) { $hostProc.ExitCode } else { "n/a" }
    $joinExit = if ($joinProc -and $joinProc.HasExited) { $joinProc.ExitCode } else { "n/a" }
    Write-Host "play_local: done host_exit=$hostExit join_exit=$joinExit"
    Write-Host "play_local: logs $hostDir\native.log and $joinDir\native.log"
}
