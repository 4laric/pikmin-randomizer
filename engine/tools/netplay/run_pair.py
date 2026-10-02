"""Two-peer lockstep launcher for netplay M3 (issue #880).

Launches a host and a joiner as two hidden, private, bounded instances over
loopback UDP, each with its own scripted local input file (two different
gen_inputs.py seeds), the same bootstrap content, and the lossy impairment
env on both. Both peers run unthrottled (as fast as the session allows) for
tests and stop via PIKMIN_NETPLAY_EXIT_AFTER_TICKS.

Modelled on run_replay.py: junctioned read-only assets, a state.txt
refresher thread per run dir, the game run with the run dir as cwd
(settings are read relative to cwd), NECTAR_SAVE_DIR pointed at a private
dir, PIKMIN_RANDOMIZER_TEST_BACKGROUND=1 and SDL_AUDIODRIVER=dummy. Only
the spawned PIDs are ever signalled.

After both peers exit it compares the two hash logs with compare_hashes.py,
greps both stdout logs for desync / handshake-refused / disconnected lines,
and prints a summary.

Expectations (--expect):
  sync        both exit 0, identical hash logs, 0 desync lines (default)
  refuse      both exit 4 with a '[netplay] handshake refused:' line
  disconnect  joiner is killed mid-session; host exits 0 with a
              '[netplay] disconnected:' line
  desync      (B2 fix round 1) a day-end save barrier desync: both exit 5,
              both with a '[netplay] save barrier: ... mismatch' line
  barrier-timeout  (B2 fix round 1, with --env-host
              PIKMIN_NETPLAY_TEST_HOST_DIE_AT_BARRIER=1) the host exits 7 at
              its day-end save; the joiner exits 6 with '[netplay] save
              barrier timeout' and retracts its pending checkpoint
  --expect-hold N (M4 lane B1) implies sync and additionally requires
              exactly N '[netplay] hold at' / 'held at' / 'resume at'
              triples, identical on both peers (the per-peer held_ms is
              compared separately), and no 'disconnected:' line.
  hash-desync (gapfix C, issue #885) a per-tick state-hash desync: at least
              one peer logs '[netplay] desync detected:' and exits 5, no
              peer exits 0, and compare_hashes reports where the two hash
              logs first diverge and which columns differ.

M4 lane B1 (issue #885) inputs: --bootstrap-template (both bootstraps from
one template, {TOKEN} = run token for SESSION and FINGERPRINT),
--host-stale-window START:SECONDS (the host refresher writes nothing in
[START, START+SECONDS) wall seconds), --host-state-missing-until SECONDS
(no host state.txt at all until then) and --host-session-json FILE (copied
to <out>/session.json, the runner ledger the host reads). The summary adds
the hold/resume lines, per-peer START_STAGE / [Pikmin Randomizer] /
distinct navi-piki-teki-item tuple counts and the journal/mirror files
present in each run dir.

Gapfix C (issue #885) sim-frame keyed state scripts: an entry may be keyed
`f<N> PIKMIN_STATE ...` instead of `<seconds> PIKMIN_STATE ...`. Such an
entry takes effect once that peer's own hash log shows tick >= N (the
refresher reads the last complete line of hashes.txt; the game flushes it
every 300 ticks, so a key fires at the first flush at or after N: use
multiples of 300 for an exact lower bound). Entries apply strictly in file
order: each one waits for its own key and for every entry before it, so a
DeathLink keyed to a frame can never land before the field is populated,
however slowly a loaded machine runs. Scripts with only `<seconds>` keys
behave exactly as before (sorted by time). Every step switch is printed in
the summary with its wall time and the tick the refresher saw.

M4 lane B2 (issue #885) sessions across day ends: --token HEX64 reuses a run
token (SESSION and FINGERPRINT; session 2 must reuse session 1's, otherwise
its checkpoint's fingerprint does not match); --run-name NAME puts the run
dirs at out/host/NAME and out/join/peer/NAME while the derived campaign dirs
stay out/campaign and out/join/campaign, so a second session reuses both
campaigns; --join-campaign-mode keep|clear|foreign:<file.sav>|newer prepares
the joiner's campaign before launch (clear moves it aside to
campaign.moved-<n>; foreign plants a checkpoint from another run; newer
plants a valid copy of the host's newest checkpoint re-stamped as the next
generation, header and hash included). The summary adds both peers'
checkpoint / transfer / save barrier / CAMPAIGN_RESUMED / reseed lines and
the distinct tuples after the day-3 reseed tick.

M4 gap-fix lane S (issue #885) long-load tests: pass the
PIKMIN_NETPLAY_TEST_STALL_* injector (see pc_netplay_loadguard.h) through
--env. The summary prints both peers' load guard / test stall / long tick /
load window lines, and a sync run fails when the load windows' open/close
frames differ between the peers. Dead-peer tests: --expect disconnect with
--kill-role join|host picks the victim, --kill-on-line TEXT [--kill-delay S]
kills it once its native.log shows TEXT, the survivor's 'disconnected:'
latency after the kill is printed, and --max-detect-s bounds it.
Fix round 1: the load guard switches and the stall injector are scrubbed
from the inherited environment (pass them with --env/--env-host/--env-join);
a targeted kill fails the run when its trigger line never appeared or the
victim had already exited; and a sync or disconnect run fails when a peer
armed a test stall that applies to it ('test stall: armed ... this peer
stalls') but never logged 'test stall: begin'. The stall durations are
printed.

M5c lane B (issue #887) link profiles and adaptive delay: --net-profile
clean60|jitter|spikes|ramp (or --proxy-args for a custom one) starts the
netplay_impair_proxy test tool (--proxy-exe; built in netplay builds) on
--proxy-port (default host port + 1) and points the joiner at it, so both
directions of every datagram (handshake, GekkoNet, bulk) cross the same
impaired link whatever the executable: a baseline on an older exe sees the
same link as the lane exe. The in-exe lossy knobs stay at 0 in that mode.
Profiles (one-way ms per direction): clean60 = 30 (RTT 60); jitter = 30 +
uniform [0,60] (60 +/- 30) with 2% loss; spikes = 30 plus a 250-400 ms link
block every ~20 s; ramp = 20 ms, rising 30-120 s to 80 ms (RTT 40 -> 160),
held to 160 s, back to 20 ms by 200 s. The summary prints each peer's
adaptive-delay line, delay changes, final stats, delay timeline and
frame-time histogram (lane exe) or the exit stall line (any exe), plus the
proxy's block lines. PIKMIN_NETPLAY_ADAPTIVE_DELAY and
PIKMIN_NETPLAY_TEST_DELAY_SCHEDULE pass through --env/--env-host/--env-join.
"""

import argparse
import os
import re
import shutil
import struct
import subprocess
import sys
import threading
import time
import uuid
from pathlib import Path

try:
    import _winapi
except ImportError:  # non-Windows: junctions unavailable; caller must symlink
    _winapi = None

DEFAULT_ASSETS = Path("C:/Users/alari/bbft/dist/cohesion/pikmin/assets")
HERE = Path(__file__).resolve().parent
GEN = HERE / "gen_inputs.py"
CMP = HERE / "compare_hashes.py"


def parse_kv(items, what):
    out = {}
    for item in items or []:
        if "=" not in item:
            raise SystemExit(f"--{what} needs key=value, got {item!r}")
        key, value = item.split("=", 1)
        out[key.strip()] = value.strip()
    return out


def fnv1a64(data):
    """pc_randomizer.cpp checkpointHash (FNV-1a 64)."""
    h = 14695981039346656037
    for byte in data:
        h ^= byte
        h = (h * 1099511628211) & 0xFFFFFFFFFFFFFFFF
    return h


def restamp_checkpoint(src, dst, new_gen):
    """B2 --join-campaign-mode newer: a VALID checkpoint for new_gen: the
    header's generation field is replaced and the FNV-1a hash recomputed
    (a bare rename would be a header/name mismatch, which the joiner sets
    aside as stale instead of reporting a newer checkpoint)."""
    raw = Path(src).read_bytes()
    nl = raw.index(b"\n")
    header, block = raw[:nl].decode("ascii"), raw[nl + 1:]
    parts = header.split(" ")
    parts[2] = str(new_gen)
    body = " ".join(parts[:-1])
    h = fnv1a64(body.encode("ascii") + b"\n" + block)
    Path(dst).write_bytes((body + " " + str(h) + "\n").encode("ascii") + block)


def prepare_join_campaign(mode, host_campaign, join_campaign):
    """B2: prepare the joiner's campaign dir; returns a description."""
    if mode in (None, "keep"):
        return "keep"
    if mode == "clear":
        if not join_campaign.exists():
            return "clear (nothing to move)"
        n = 1
        while (join_campaign.parent / f"campaign.moved-{n}").exists():
            n += 1
        dest = join_campaign.parent / f"campaign.moved-{n}"
        join_campaign.rename(dest)
        return f"clear (moved to {dest.name})"
    if mode.startswith("foreign:"):
        src = Path(mode[len("foreign:"):])
        join_campaign.mkdir(parents=True, exist_ok=True)
        dst = join_campaign / src.name
        if dst.exists():
            n = 1
            while (join_campaign / f"{src.name}.harness-replaced-{n}").exists():
                n += 1
            dst.rename(join_campaign / f"{src.name}.harness-replaced-{n}")
        shutil.copyfile(str(src), str(dst))
        return f"foreign ({src} -> {dst.name})"
    if mode == "newer":
        savs = sorted(p for p in host_campaign.glob("*.sav") if re.match(r"^\d{20}\.sav$", p.name))
        if not savs:
            raise SystemExit("--join-campaign-mode newer: the host has no checkpoint")
        gen = int(savs[-1].name[:20]) + 1
        join_campaign.mkdir(parents=True, exist_ok=True)
        dst = join_campaign / f"{gen:020d}.sav"
        restamp_checkpoint(savs[-1], dst, gen)
        return f"newer ({savs[-1].name} re-stamped as {dst.name})"
    raise SystemExit(f"bad --join-campaign-mode {mode}")


def write_bootstrap(path, token, profile, flarlic=10):
    path.write_text(
        f"PIKMIN_RANDOMIZER 5\nSESSION {token}\nFINGERPRINT {token}\n"
        f"PROFILE {profile}\nCATALOG gameplay-checks-v5\nPLACEMENT identity-v1\n"
        f"GOAL 25\nDAYS repeat-day29-v1\nCOLOR red\nSTARTING_FLARLIC {flarlic}\nEND\n"
    )


def load_state_script(path, token):
    """M4a --host-state-script/--join-state-script loader (issue #885).

    Text file, one schedule entry per line: `<seconds> <PIKMIN_STATE ...>`
    or (gapfix C) `f<N> <PIKMIN_STATE ...>`, keyed to sim tick N of the
    peer's own hash log. `{TOKEN}` in a line is replaced with the peer's run
    token. The first entry must be at t=0 (the refresher's initial content);
    later entries switch the hosted state.txt at that many wall seconds
    after the refresher starts, or once the peer's sim reaches tick N.
    Blank lines and `#` comments are ignored.

    Returns a list of (kind, value, line), kind "t" (seconds) or "f"
    (tick). A script with only time keys is sorted by time, as before; a
    script with any tick key keeps file order (each entry waits for the
    previous one), and its time keys and tick keys must each be
    non-decreasing.
    """
    sched = []
    for lineno, raw in enumerate(Path(path).read_text().splitlines(), 1):
        ln = raw.strip()
        if not ln or ln.startswith("#"):
            continue
        key, _, line = ln.partition(" ")
        kind = "t"
        try:
            if key[:1] in ("f", "F"):
                kind = "f"
                value = int(key[1:])
            else:
                value = float(key)
        except ValueError:
            raise SystemExit(f"state script {path}:{lineno}: bad key {key!r} "
                             "(want seconds or f<tick>)")
        if value < 0 or (kind == "f" and value < 1) or not line.strip().startswith("PIKMIN_STATE"):
            raise SystemExit(
                f"state script {path}:{lineno}: want '<seconds> PIKMIN_STATE ...' "
                "or 'f<tick> PIKMIN_STATE ...' (tick >= 1)")
        sched.append((kind, value, line.replace("{TOKEN}", token).strip() + "\n"))
    if all(kind == "t" for kind, _v, _l in sched):
        sched.sort(key=lambda e: e[1])
    if not sched or sched[0][0] != "t" or sched[0][1] != 0:
        raise SystemExit(f"state script {path}: first entry must be at t=0")
    if any(kind == "f" for kind, _v, _l in sched):
        for kind in ("t", "f"):
            vals = [v for k, v, _l in sched if k == kind]
            if vals != sorted(vals):
                raise SystemExit(f"state script {path}: {kind}-keys must be non-decreasing "
                                 "in a frame-keyed script (entries apply in file order)")
    return sched


def sched_step(sched, idx, elapsed, tick):
    """Advance a schedule cursor: the index of the entry to host now.

    Starting from `idx`, move past every following entry whose key has been
    reached (time key: elapsed wall seconds >= value; tick key: the peer's
    hash-log tick >= value), in file order, stopping at the first entry not
    yet reached."""
    while idx + 1 < len(sched):
        kind, value, _line = sched[idx + 1]
        reached = elapsed >= value if kind == "t" else (tick is not None and tick >= value)
        if not reached:
            break
        idx += 1
    return idx


def hash_log_tick(path, cache=None):
    """Last complete tick in a per-tick hash log, or None when there is none
    yet. Reads only the tail; `cache` (a dict) skips the read when the size
    is unchanged. Never raises: the game may be rewriting the file."""
    cache = {} if cache is None else cache
    try:
        size = os.path.getsize(path)
    except OSError:
        return cache.get("tick")
    if size == cache.get("size"):
        return cache.get("tick")
    try:
        with open(path, "rb") as f:
            f.seek(max(0, size - 1024))
            tail = f.read(1024)
    except OSError:
        return cache.get("tick")
    tick = cache.get("tick")
    for raw in reversed(tail.split(b"\n")[:-1]):  # complete lines only
        cols = raw.split()
        if len(cols) >= 2 and cols[0].isdigit():
            tick = int(cols[0])
            break
    cache["size"] = size
    cache["tick"] = tick
    return tick


def apply_lines(path):
    """Canonical `[netplay] randstate gen=<g> applied at frame=<F>` lines."""
    try:
        text = Path(path).read_text(errors="replace")
    except OSError:
        return []
    out = []
    for ln in text.splitlines():
        if "randstate gen=" in ln and "applied at frame=" in ln:
            out.append(ln[ln.index("randstate"):].strip())
    return out


def link_assets(run, assets):
    link = run / "assets"
    if not link.exists():
        if _winapi is not None:
            _winapi.CreateJunction(str(assets.resolve()), str(link))
        else:
            os.symlink(str(assets.resolve()), str(link), target_is_directory=True)


def gen_inputs(ticks, seed, out):
    r = subprocess.run(
        [sys.executable, str(GEN), "--ticks", str(ticks), "--seed", str(seed),
         "--out", str(out)],
        capture_output=True, text=True,
    )
    if r.returncode != 0:
        raise SystemExit(f"gen_inputs failed: {r.stderr[-2000:]}")


PKNI_HEADER = 10  # magic(4) + version/pad count/record size (3 x u16 LE)


def check_script_length(path, who, ticks):
    """#1028 review minor: a scripted --input-host/--input-join file shorter than
    --ticks + 50 records runs out mid-pair and the peer then plays hands-off (or
    the run silently tests less than asked). Refuse it up front."""
    data = Path(path).read_bytes()
    if data[:4] != b"PKNI":
        raise SystemExit(f"run_pair: {who} input {path} is not a PKNI file")
    version, pads, size = struct.unpack_from("<HHH", data, 4)
    if version != 2 or pads != 4 or size != 56:
        raise SystemExit(f"run_pair: {who} input {path}: unsupported PKNI v{version} pads={pads} size={size}")
    records = (len(data) - PKNI_HEADER) // size
    need = ticks + 50
    if records < need:
        raise SystemExit(f"run_pair: {who} input {path} has {records} records but --ticks {ticks} needs at "
                         f"least {need} (--ticks + 50); regenerate it longer")
    return records


def neutralize_after(path, keep):
    """M4 B1 fix round 1: keep the first `keep` records of a v2 .pkni as
    generated and make pad 0 hands-off afterwards (buttons, both sticks,
    triggers and analog A/B zeroed; the connected byte and control yaw stay
    as generated). Returns (records, neutralized)."""
    data = bytearray(Path(path).read_bytes())
    if data[:4] != b"PKNI":
        raise SystemExit(f"neutralize_after: {path} is not a PKNI file")
    version, pads, size = struct.unpack_from("<HHH", data, 4)
    if version != 2 or pads != 4 or size != 56:
        raise SystemExit(f"neutralize_after: unsupported PKNI v{version} pads={pads} size={size}")
    records = (len(data) - PKNI_HEADER) // size
    changed = 0
    for i in range(max(0, keep), records):
        off = PKNI_HEADER + i * size  # pad 0 is the first 14 bytes
        data[off:off + 10] = bytes(10)
        changed += 1
    Path(path).write_bytes(bytes(data))
    return records, changed


SCRUB_KEYS = (
    "PIKMIN_INPUT_RECORD",
    "PIKMIN_INPUT_REPLAY",
    "PIKMIN_STATE_HASH_LOG",
    "PIKMIN_NETPLAY_EXIT_AFTER_TICKS",
    "PIKMIN_NETPLAY_TEST_PREROLL_RAND",
    "PIKMIN_NETPLAY_DETERMINISTIC",
    "PIKMIN_NETPLAY_UNTHROTTLED",
    "PIKMIN_NETPLAY_TEST_CAMERA_WOBBLE",
    "PIKMIN_NETPLAY_DEBUG_NAVI_POS",
    "PIKMIN_NETPLAY_HOST",
    "PIKMIN_NETPLAY_JOIN",
    "PIKMIN_NETPLAY_DELAY",
    "PIKMIN_NETPLAY_SEED",
    "PIKMIN_NETPLAY_LOCAL_INPUT_FILE",
    "PIKMIN_NETPLAY_TEST_LATENCY_MS",
    "PIKMIN_NETPLAY_TEST_JITTER_MS",
    "PIKMIN_NETPLAY_TEST_LOSS_PCT",
    "PIKMIN_NETPLAY_TEST_SEED",
    "PIKMIN_NETPLAY_TEST_REORDER_PCT",
    "PIKMIN_NETPLAY_TEST_REORDER_MS",
    "PIKMIN_NETPLAY_HANDSHAKE_TIMEOUT_MS",
    "PIKMIN_NETPLAY_TEST_DROP_HS_FIRST_N",
    "PIKMIN_NETPLAY_TEST_DROP_FINAL_ACK",
    "PIKMIN_NETPLAY_DISCONNECT_MS",
    "PIKMIN_NETPLAY_TEST_LOAD_DELAY_MS",
    "PIKMIN_NETPLAY_TEST_SCRIPT_VIA_ACCUM",
    "PIKMIN_NETPLAY_RANDSTATE_STREAM",
    "PIKMIN_NETPLAY_TEST_DEATHLINK_AS_ORDINARY",
    "PIKMIN_NETPLAY_TEST_HOST_SAVE_FAIL",
    "PIKMIN_NETPLAY_TEST_TAMPER_SIDECARS",
    "PIKMIN_NETPLAY_TEST_BARRIER_CORRUPT",
    "PIKMIN_NETPLAY_TEST_HOST_DIE_AT_BARRIER",
    "PIKMIN_NETPLAY_TEST_BULK_DROP_SAVE",
    "PIKMIN_NETPLAY_TEST_COOP_EVENTS",
    "PIKMIN_NETPLAY_TEST_NAVI_TO_BOSS",
    "PIKMIN_NETPLAY_TEST_COOP_PERTURB",
    # M4 gap-fix lane S (fix round 1, MN1): a stale export must never turn the
    # load guard off or inject a stall into a regression pair.
    "PIKMIN_NETPLAY_LOAD_GUARD",
    "PIKMIN_NETPLAY_LOAD_KEEPALIVE",
    "PIKMIN_NETPLAY_LOAD_WINDOW",
    "PIKMIN_NETPLAY_LOAD_DISCONNECT_MS",
    "PIKMIN_NETPLAY_TEST_STALL_MS",
    "PIKMIN_NETPLAY_TEST_STALL_AT",
    "PIKMIN_NETPLAY_TEST_STALL_ROLE",
    "PIKMIN_NETPLAY_TEST_STALL_SLICE_MS",
    # M5c lane B: a stale export must never pin or script the delay.
    "PIKMIN_NETPLAY_ADAPTIVE_DELAY",
    "PIKMIN_NETPLAY_TEST_DELAY_SCHEDULE",
    # #965 lane H: every remaining getenv("PIKMIN_NETPLAY_*") in pc_port/ and src/
    # (M5c lanes A and C camera/HUD/desync knobs, lane N's camlead key-skew
    # knob, the trace/debug switches, the socket/ICE binds and the handshake
    # test knobs). The prefix rule in scrub_env() below already drops every
    # PIKMIN_NETPLAY_* name, so this list is the explicit documentation of what
    # exists today (tools/netplay/selftest.py fails when a new getenv is missing).
    "PIKMIN_NETPLAY_AUDIO_LEGACY",  # #1030: captain-owned sounds, old behaviour
    "PIKMIN_NETPLAY_AUDIO_TRACE",   # #1030: [audio-trace] lines
    "PIKMIN_NETPLAY_BANNER_MS",
    "PIKMIN_NETPLAY_BUILD",
    "PIKMIN_NETPLAY_CAMERA_LEAD",
    "PIKMIN_NETPLAY_CAMERA_SHOT",
    "PIKMIN_NETPLAY_CAMERA_TRACE",
    "PIKMIN_NETPLAY_GFX_TRACE",  # #1031 presentation-start UI mapping trace
    "PIKMIN_NETPLAY_HUD",
    "PIKMIN_NETPLAY_ICE_DEBUG",
    "PIKMIN_NETPLAY_INPUT_TRACE",
    "PIKMIN_NETPLAY_JOINER_OWN_CAMERA",
    "PIKMIN_NETPLAY_LOCAL_PLAYER",
    "PIKMIN_NETPLAY_LOCAL_PROMPT_LABELS",  # #1029 test escape hatch
    "PIKMIN_TEST_PROMPT_GAMEPAD",          # #1029 test knobs (not PIKMIN_NETPLAY_*)
    "PIKMIN_TEST_RAW_START",
    "PIKMIN_TEST_CLOCK_TOD",               # #1029 forced time-of-day clock (a stale export changes the sim)
    "PIKMIN_NETPLAY_PROFILE_LOG",
    "PIKMIN_NETPLAY_STALL_TRACE",
    "PIKMIN_NETPLAY_UDP_BIND",
    "PIKMIN_NETPLAY_TEST_CAMERA_DRAG",
    "PIKMIN_NETPLAY_TEST_CAMLEAD_KEY_SKEW",  # lane N (#965), may not exist in an older exe
    "PIKMIN_NETPLAY_TEST_DESYNC_AT_FRAME",
    # #1037 desync forensics: the session input log, the offline replay, the
    # forensics switch / output folder and the one-object sim nudge (TEST ONLY).
    "PIKMIN_NETPLAY_INPUT_LOG",
    "PIKMIN_NETPLAY_REPLAY_LOG",
    "PIKMIN_NETPLAY_REPLAY_DUMP_TICKS",
    "PIKMIN_NETPLAY_FORENSICS",
    "PIKMIN_NETPLAY_FORENSICS_DIR",
    "PIKMIN_NETPLAY_TEST_DESYNC_NUDGE",
    "PIKMIN_NETPLAY_TEST_TELEPORT",
    "PIKMIN_NETPLAY_TEST_FORCE_AUTH_TEXINIT",
    "PIKMIN_NETPLAY_TEST_HANDSHAKE_LEN",
    "PIKMIN_NETPLAY_TEST_HUD_SHOT",
    "PIKMIN_NETPLAY_TEST_HUD_SHOT_FRAME",
    "PIKMIN_NETPLAY_TEST_HUD_TOGGLE_FRAME",
    "PIKMIN_NETPLAY_TEST_NO_UI_RESET",  # #1031 restores the pre-fix UI-state leak
    "PIKMIN_NETPLAY_TEST_PROTOCOL_VERSION",
    "PIKMIN_NETPLAY_TEST_SCRIPT_LIVE_YAW",
    "NECTAR_CARD_DEBUG",
)

# #965 lane H: robust scrub. A player-facing doc tells people to set knobs with
# `$env:...` which stays set for the whole PowerShell window; a harness launched
# from that window must not inherit them. Every PIKMIN_NETPLAY_* / PIKMIN_INPUT_*
# name is dropped from the inherited environment (so a knob added tomorrow is
# covered without touching this file); the harness then sets exactly the
# variables it needs, and callers pass test knobs through --env/--env-host/
# --env-join. There is deliberately no allow-list: nothing in tools/netplay
# relies on inheriting one of these from the parent shell.
# PIKMIN_TEST_ONLY_* are the sim-changing TEST_ONLY knobs (#1034 and later): a
# prefix rule, so one added tomorrow is covered too.
SCRUB_PREFIXES = ("PIKMIN_NETPLAY_", "PIKMIN_INPUT_", "PIKMIN_TEST_ONLY_")


def scrub_env(env):
    """Drop every knob a caller's shell could leak into a peer. Mutates and returns env."""
    explicit = set(SCRUB_KEYS)
    for key in list(env):
        if key.upper() in explicit or key.upper().startswith(SCRUB_PREFIXES):
            del env[key]
    return env

# M5c lane B (issue #887): netplay_impair_proxy link profiles.
NET_PROFILES = {
    "clean60": ["--lat", "30"],
    "jitter": ["--lat", "30", "--jit", "60", "--loss", "2"],
    "spikes": ["--lat", "30", "--spikes", "20000:250:400"],
    "ramp": ["--sched", "0:20,30:20,120:80,160:80,200:20"],
}


def launch(exe, run, boot, extra_args, env_extra, stdout_log, unthrottled=True):
    cmd = [str(exe.resolve()), "--randomizer-seed", str(boot)] + list(extra_args)
    env = scrub_env(dict(os.environ))
    env.update(
        PIKMIN_RANDOMIZER_TEST_BACKGROUND="1",
        SDL_AUDIODRIVER="dummy",
        NECTAR_SAVE_DIR=str((run / "save").resolve()),
    )
    # M5: throttled runs (the path humans use: 30 Hz pacing + the
    # frames-ahead throttle) set PIKMIN_NETPLAY_UNTHROTTLED=0 explicitly.
    env["PIKMIN_NETPLAY_UNTHROTTLED"] = "1" if unthrottled else "0"
    # Loopback-only sockets: test peers never touch a real adapter, so
    # Windows Firewall never prompts for the per-run exe copies.
    env["PIKMIN_NETPLAY_UDP_BIND"] = "127.0.0.1"
    env["PIKMIN_NETPLAY_ICE_BIND"] = "127.0.0.1"
    env.update(env_extra)
    env.pop("BBFT_PORT", None)
    startup = None
    if sys.platform == "win32":
        startup = subprocess.STARTUPINFO()
        startup.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        startup.wShowWindow = 0
    child_out = open(stdout_log, "w")
    proc = subprocess.Popen(
        cmd, cwd=str(run), env=env, startupinfo=startup,
        stdout=child_out, stderr=subprocess.STDOUT,
    )
    return proc, child_out


def hold_lines(path):
    """M4 lane B1: (hold, held, resume, held_ms) from one native log.

    resume lines are canonicalised without their per-peer ` held_ms=<ms>`
    suffix (wall time differs per peer); the ms values come back separately.
    """
    try:
        text = Path(path).read_text(errors="replace")
    except OSError:
        return [], [], [], []
    hold, held, resume, ms = [], [], [], []
    for ln in text.splitlines():
        if "[netplay] hold at frame=" in ln:
            hold.append(ln[ln.index("hold at"):].strip())
        elif "[netplay] held at frame=" in ln:
            held.append(ln[ln.index("held at"):].strip())
        elif "[netplay] resume at frame=" in ln:
            body = ln[ln.index("resume at"):].strip()
            if " held_ms=" in body:
                body, _, val = body.partition(" held_ms=")
                try:
                    ms.append(float(val))
                except ValueError:
                    ms.append(-1.0)
            resume.append(body)
    return hold, held, resume, ms


def hash_tuples(path, lo=None, hi=None):
    """Distinct (navi, piki, teki, item) tuples of a hash log, i.e.
    awk '{print $3,$4,$5,$6}' hashes.txt | sort -u | wc -l, optionally
    restricted to ticks lo <= tick <= hi."""
    seen = set()
    try:
        with open(path, "r", errors="replace") as f:
            for line in f:
                cols = line.split()
                if len(cols) < 6:
                    continue
                try:
                    tick = int(cols[0])
                except ValueError:
                    continue
                if lo is not None and tick < lo:
                    continue
                if hi is not None and tick > hi:
                    continue
                seen.add(tuple(cols[2:6]))
    except OSError:
        return 0
    return len(seen)


def frame_of(line):
    """Integer after 'frame=' in a canonical hold/held/resume line."""
    try:
        return int(line.split("frame=", 1)[1].split()[0])
    except (IndexError, ValueError):
        return None


def count_lines(path):
    try:
        with open(path, "r", errors="replace") as f:
            return sum(1 for line in f if line.strip())
    except OSError:
        return 0


def grep(path, needle):
    try:
        text = Path(path).read_text(errors="replace")
    except OSError:
        return []
    return [ln for ln in text.splitlines() if needle in ln]


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--exe", type=Path, required=True, help="netplay game executable (host)")
    p.add_argument("--exe-b", type=Path, default=None, help="joiner executable override (exe negative test)")
    p.add_argument("--ticks", type=int, required=True)
    p.add_argument("--out", type=Path, required=True, help="private output dir (host/ + join/ below)")
    p.add_argument("--assets", type=Path, default=DEFAULT_ASSETS)
    p.add_argument("--profile", default="foh-day2")
    p.add_argument("--host-port", type=int, default=5077)
    p.add_argument("--seed-a", type=int, default=101, help="host local-input gen seed")
    p.add_argument("--seed-b", type=int, default=202, help="joiner local-input gen seed")
    p.add_argument("--input-host", type=Path, default=None, metavar="PKNI",
                   help="the host's scripted input file instead of the seeded random walk "
                        "(tools/netplay/gen_coop_input.py); needs >= --ticks + 50 records")
    p.add_argument("--input-join", type=Path, default=None, metavar="PKNI",
                   help="the joiner's scripted input file instead of the seeded random walk")
    p.add_argument("--netplay-seed", type=int, default=1, help="PIKMIN_NETPLAY_SEED for both")
    p.add_argument("--delay", type=str, default="2",
                   help="PIKMIN_NETPLAY_DELAY for both (frames, or 'auto')")
    p.add_argument("--delay-host", type=str, default=None,
                   help="PIKMIN_NETPLAY_DELAY for the host only (asymmetric test)")
    p.add_argument("--delay-join", type=str, default=None,
                   help="PIKMIN_NETPLAY_DELAY for the joiner only (asymmetric test)")
    p.add_argument("--latency-ms", type=float, default=0.0)
    p.add_argument("--jitter-ms", type=float, default=0.0)
    p.add_argument("--loss-pct", type=float, default=0.0)
    p.add_argument("--impair-seed", type=int, default=7)
    p.add_argument("--net-profile", choices=sorted(NET_PROFILES), default=None,
                   help="M5c: impair the link through netplay_impair_proxy (see the docstring)")
    p.add_argument("--proxy-args", type=str, default=None,
                   help="M5c: custom netplay_impair_proxy arguments (instead of --net-profile)")
    p.add_argument("--proxy-exe", type=Path, default=None, help="M5c: netplay_impair_proxy.exe")
    p.add_argument("--proxy-port", type=int, default=None, help="M5c: proxy listen port (host port + 1)")
    p.add_argument("--timeout", type=float, default=900)
    p.add_argument("--handshake-timeout-ms", type=int, default=30000)
    p.add_argument("--env", nargs="*", default=[], metavar="K=V", help="extra env for both peers")
    p.add_argument("--env-host", nargs="*", default=[], metavar="K=V")
    p.add_argument("--env-join", nargs="*", default=[], metavar="K=V")
    p.add_argument("--config-overrides", nargs="*", default=[], metavar="key=value",
                   help="private pikmin_settings.conf for both peers")
    p.add_argument("--config-overrides-join", nargs="*", default=[], metavar="key=value",
                   help="extra private settings for the joiner only (settings negative test)")
    p.add_argument("--bootstrap-b", type=Path, default=None,
                   help="joiner bootstrap override file (bootstrap negative test)")
    p.add_argument("--throttled", action="store_true",
                   help="run the real-time 30 Hz path (no UNTHROTTLED); M5 evidence")
    p.add_argument("--no-restamp-session", action="store_true",
                   help="keep --bootstrap-b bytes verbatim (m8 SESSION-strip positive test)")
    p.add_argument("--session-only-difference", action="store_true",
                   help="m8 positive test: join bootstrap differs from the host only in "
                        "SESSION (same FINGERPRINT); the handshake must succeed")
    p.add_argument("--input-log", action="store_true",
                   help="#1037: both peers write their session input log (PKNL) to "
                        "<run>/session-inputs.pknl; tools/netplay/replay_session.py replays it")
    p.add_argument("--exe-args", nargs="*", default=[])
    p.add_argument("--expect", choices=("sync", "refuse", "disconnect", "desync", "barrier-timeout",
                                        "hash-desync"),
                   default="sync")
    p.add_argument("--kill-joiner-after", type=float, default=20.0,
                   help="disconnect test: seconds after start to kill the joiner")
    p.add_argument("--kill-role", choices=("join", "host"), default="join",
                   help="M4 gap-fix S: disconnect test victim (default join); the other peer must "
                        "report the disconnect and exit 0")
    p.add_argument("--kill-on-line", type=str, default=None, metavar="TEXT",
                   help="M4 gap-fix S: kill the victim once its native.log contains TEXT (then "
                        "--kill-delay), instead of --kill-joiner-after seconds from start")
    p.add_argument("--kill-delay", type=float, default=0.0, metavar="SECONDS",
                   help="M4 gap-fix S: extra wait after --kill-on-line matched")
    p.add_argument("--max-detect-s", type=float, default=None, metavar="SECONDS",
                   help="M4 gap-fix S: disconnect test fails when the survivor's 'disconnected:' "
                        "line comes later than this after the kill")
    p.add_argument("--flarlic", type=int, default=10,
                   help="STARTING_FLARLIC in both bootstraps (M4a: <10 allows a "
                        "flarlic change in a state script)")
    p.add_argument("--host-state-script", type=Path, default=None,
                   help="M4a: schedule file for the host state.txt refresher "
                        "(lines: '<seconds> PIKMIN_STATE ...' or, gapfix C, 'f<tick> "
                        "PIKMIN_STATE ...' keyed to the peer's sim tick; {TOKEN} = run token)")
    p.add_argument("--join-state-script", type=Path, default=None,
                   help="M4a: schedule file for the joiner state.txt refresher "
                        "(negative control: a deliberately different schedule)")
    p.add_argument("--bootstrap-template", type=Path, default=None,
                   help="M4 B1: both peers' bootstrap from this template; {TOKEN} "
                        "becomes the run token (SESSION and FINGERPRINT)")
    p.add_argument("--host-stale-window", type=str, default=None, metavar="START:SECONDS",
                   help="M4 B1: the host state.txt refresher writes nothing during "
                        "[START, START+SECONDS) wall seconds (link goes stale -> HOLD)")
    p.add_argument("--host-state-missing-until", type=float, default=None, metavar="SECONDS",
                   help="M4 B1: the host has no state.txt at all until SECONDS "
                        "(any existing file is removed first)")
    p.add_argument("--host-session-json", type=Path, default=None,
                   help="M4 B1: copied to parent^2(host run)/session.json, i.e. "
                        "<out>/session.json (the runner mirror ledger)")
    p.add_argument("--expect-hold", type=int, default=None, metavar="N",
                   help="M4 B1: implies sync; exactly N hold/held/resume triples, "
                        "identical on both peers, and 0 disconnected lines")
    p.add_argument("--expect-held-ms", type=float, default=None, metavar="MIN",
                   help="M4 B1 fix round 1: with --expect-hold, every resume line's "
                        "held_ms (hold at -> resume, per peer) must be >= MIN")
    p.add_argument("--min-tuples", type=int, default=None, metavar="N",
                   help="M4 B1 fix round 1: with --expect-hold, each peer's distinct "
                        "tuples after each resume frame, and before each hold frame "
                        "when that frame exceeds N, must exceed N; otherwise each "
                        "peer's total must exceed N")
    p.add_argument("--expect-no-hold", action="store_true",
                   help="M4 B1 fix round 1 (negative control): implies sync; no hold, "
                        "held or resume line on either peer")
    p.add_argument("--host-script-ticks", type=int, default=None, metavar="N",
                   help="M4 B1 fix round 1: the host's scripted pad 0 plays the seed-a "
                        "records for the first N submits, then stays hands-off")
    p.add_argument("--join-script-ticks", type=int, default=None, metavar="N",
                   help="M4 B1 fix round 1: the same for the joiner (seed b); 0 = "
                        "hands-off from the first submit")
    p.add_argument("--token", type=str, default=None, metavar="HEX64",
                   help="M4 B2: reuse this run token (SESSION and FINGERPRINT); default random, printed")
    p.add_argument("--run-name", type=str, default="run",
                   help="M4 B2: run dirs out/host/NAME and out/join/peer/NAME (the campaigns stay "
                        "out/campaign and out/join/campaign)")
    p.add_argument("--join-campaign-mode", type=str, default="keep",
                   help="M4 B2: keep | clear | foreign:<file.sav> | newer (see the module docstring)")
    a = p.parse_args(argv)
    if a.token is not None and not re.match(r"^[0-9a-f]{64}$", a.token):
        raise SystemExit("--token wants 64 lowercase hex characters")
    if not re.match(r"^[A-Za-z0-9._-]+$", a.run_name):
        raise SystemExit("--run-name wants a plain folder name")
    if a.expect_hold is not None or a.expect_no_hold:
        a.expect = "sync"
    stale_window = None
    if a.host_stale_window:
        try:
            st0, _, dur = a.host_stale_window.partition(":")
            stale_window = (float(st0), float(st0) + float(dur))
        except ValueError:
            raise SystemExit("--host-stale-window wants START:SECONDS")

    out = a.out.resolve()
    # Slice lane (issue #880): each peer gets a per-peer campaign dir.
    # pc_randomizer.cpp derives it as bootstrap-grandparent + "campaign", so
    # the run dirs sit at different depths to force different grandparents:
    # parent^2(out/host/run) is out, while parent^2(out/join/peer/run) is
    # out/join. Day-end writes a
    # card save and a campaign checkpoint from inside the sim on both peers
    # at the same tick; sharing one campaign dir makes the two writers
    # collide on the same checkpoint file (filesystem rename error, the loser
    # terminates and the pair disconnects). In production the peers are on
    # different machines; per-peer dirs are the faithful layout, and they
    # make the post-test save comparison meaningful.
    host_run = out / "host" / a.run_name
    join_run = out / "join" / "peer" / a.run_name
    host_run.mkdir(parents=True, exist_ok=True)
    join_run.mkdir(parents=True, exist_ok=True)
    # B2: prepare the joiner's derived campaign dir (parent^2(join run)).
    campaign_note = prepare_join_campaign(a.join_campaign_mode, out / "campaign", out / "join" / "campaign")
    print(f"run_pair: join campaign: {campaign_note}")

    token = a.token if a.token is not None else uuid.uuid4().hex * 2
    print(f"run_pair: token {token}")
    token_join = token
    host_boot = host_run / "bootstrap.txt"
    template = None
    if a.bootstrap_template is not None:
        template = a.bootstrap_template.read_text().replace("{TOKEN}", token)
        host_boot.write_text(template)
    else:
        write_bootstrap(host_boot, token, a.profile, a.flarlic)
    join_boot = join_run / "bootstrap.txt"
    if template is not None and a.bootstrap_b is None:
        join_boot.write_text(template)
    elif a.bootstrap_b is not None:
        shutil.copyfile(str(a.bootstrap_b.resolve()), str(join_boot))
        if not a.no_restamp_session:
            # Re-stamp the per-run SESSION token to this run's token (the
            # handshake hash strips SESSION lines by design, so the manifest
            # difference under test is preserved while state.txt admission,
            # which compares the session token, keeps working).
            lines = join_boot.read_text().splitlines()
            lines = [f"SESSION {token}" if ln.startswith("SESSION ") else ln for ln in lines]
            join_boot.write_text("\n".join(lines) + "\n")
        else:
            # m8: keep --bootstrap-b bytes verbatim AND stamp the joiner's
            # state.txt with the join bootstrap's own SESSION, so local
            # admission passes on both sides while the handshake must still
            # succeed on the stripped hash (SESSION differs, all else same).
            for ln in join_boot.read_text().splitlines():
                if ln.startswith("SESSION "):
                    token_join = ln[len("SESSION "):].strip()
                    break
    else:
        write_bootstrap(join_boot, token, a.profile, a.flarlic)
    if a.session_only_difference:
        # m8 positive test: same manifest, different per-run SESSION token.
        # The joiner's state.txt (below) uses token_join so local admission
        # passes; the handshake strips SESSION, so it must succeed.
        token_join = uuid.uuid4().hex * 2
        assert token_join != token
        join_boot.write_text(
            f"PIKMIN_RANDOMIZER 5\nSESSION {token_join}\nFINGERPRINT {token}\n"
            f"PROFILE {a.profile}\nCATALOG gameplay-checks-v5\nPLACEMENT identity-v1\n"
            f"GOAL 25\nDAYS repeat-day29-v1\nCOLOR red\nSTARTING_FLARLIC 10\nEND\n"
        )

    link_assets(host_run, a.assets)
    link_assets(join_run, a.assets)

    overrides = parse_kv(a.config_overrides, "config-overrides")
    if overrides:
        for run in (host_run, join_run):
            with open(run / "pikmin_settings.conf", "w") as f:
                for key, value in sorted(overrides.items()):
                    f.write(f"{key} = {value}\n")
    join_extra_cfg = parse_kv(a.config_overrides_join, "config-overrides-join")
    if join_extra_cfg:
        with open(join_run / "pikmin_settings.conf", "a") as f:
            for key, value in sorted(join_extra_cfg.items()):
                f.write(f"{key} = {value}\n")

    for run in (host_run, join_run):
        (run / "save").mkdir(exist_ok=True)
    if a.host_session_json is not None:
        # B1: the host reads the runner ledger at parent^2(run)/session.json.
        shutil.copyfile(str(a.host_session_json.resolve()), str(host_run.parent.parent / "session.json"))
    if a.host_state_missing_until is not None:
        try:
            (host_run / "state.txt").unlink()
        except FileNotFoundError:
            pass

    # Per-peer scripted local inputs (brief: two different seeds).
    tag = "" if a.run_name == "run" else a.run_name + "_"
    host_inputs = out / f"{tag}host_inputs.pkni"
    join_inputs = out / f"{tag}join_inputs.pkni"
    for given, dst, seed in ((a.input_host, host_inputs, a.seed_a), (a.input_join, join_inputs, a.seed_b)):
        if given is not None:
            check_script_length(given, "host" if dst is host_inputs else "join", a.ticks)
            shutil.copyfile(str(given), str(dst))  # coop fix: a scripted file (gen_coop_input.py)
        else:
            gen_inputs(a.ticks + 50, seed, dst)
    for who, keep, path in (("host", a.host_script_ticks, host_inputs),
                            ("join", a.join_script_ticks, join_inputs)):
        if keep is not None:
            records, changed = neutralize_after(path, keep)
            print(f"run_pair: {who} inputs: first {min(keep, records)} of {records} records "
                  f"scripted, {changed} hands-off")

    host_hash = host_run / "hashes.txt"
    join_hash = join_run / "hashes.txt"
    host_log = host_run / "native.log"
    join_log = join_run / "native.log"

    impair = {
        "PIKMIN_NETPLAY_TEST_LATENCY_MS": str(a.latency_ms),
        "PIKMIN_NETPLAY_TEST_JITTER_MS": str(a.jitter_ms),
        "PIKMIN_NETPLAY_TEST_LOSS_PCT": str(a.loss_pct),
        "PIKMIN_NETPLAY_TEST_SEED": str(a.impair_seed),
    }
    base_extra = {
        "PIKMIN_NETPLAY_SEED": str(a.netplay_seed),
        "PIKMIN_NETPLAY_DELAY": str(a.delay),
        "PIKMIN_NETPLAY_EXIT_AFTER_TICKS": str(a.ticks),
        "PIKMIN_NETPLAY_HANDSHAKE_TIMEOUT_MS": str(a.handshake_timeout_ms),
        "PIKMIN_STATE_HASH_LOG": "",  # replaced per peer below
    }
    base_extra.update(impair)
    base_extra.update(parse_kv(a.env, "env"))

    host_extra = dict(base_extra)
    host_extra["PIKMIN_STATE_HASH_LOG"] = str(host_hash)
    host_extra["PIKMIN_NETPLAY_LOCAL_INPUT_FILE"] = str(host_inputs.resolve())
    if a.delay_host is not None:
        host_extra["PIKMIN_NETPLAY_DELAY"] = str(a.delay_host)
    if a.input_log:
        host_extra["PIKMIN_NETPLAY_INPUT_LOG"] = str((host_run / "session-inputs.pknl").resolve())
    host_extra.update(parse_kv(a.env_host, "env-host"))
    join_extra = dict(base_extra)
    join_extra["PIKMIN_STATE_HASH_LOG"] = str(join_hash)
    join_extra["PIKMIN_NETPLAY_LOCAL_INPUT_FILE"] = str(join_inputs.resolve())
    if a.delay_join is not None:
        join_extra["PIKMIN_NETPLAY_DELAY"] = str(a.delay_join)
    if a.input_log:
        join_extra["PIKMIN_NETPLAY_INPUT_LOG"] = str((join_run / "session-inputs.pknl").resolve())
    join_extra.update(parse_kv(a.env_join, "env-join"))

    join_exe = a.exe_b.resolve() if a.exe_b is not None else a.exe.resolve()
    host_args = ["--netplay-host", str(a.host_port)] + list(a.exe_args)
    join_port = a.host_port
    proxy_cmd = None
    proxy_log = out / f"{tag}impair_proxy.log"
    if a.net_profile is not None or a.proxy_args is not None:
        # M5c lane B: the joiner talks to the proxy, the proxy to the host.
        if a.proxy_exe is None or not a.proxy_exe.exists():
            raise SystemExit("--net-profile/--proxy-args need --proxy-exe (netplay_impair_proxy.exe)")
        if a.latency_ms or a.jitter_ms or a.loss_pct:
            raise SystemExit("--net-profile replaces --latency-ms/--jitter-ms/--loss-pct (leave them 0)")
        join_port = a.proxy_port if a.proxy_port is not None else a.host_port + 1
        pargs = NET_PROFILES[a.net_profile] if a.net_profile is not None else a.proxy_args.split()
        proxy_cmd = [str(a.proxy_exe.resolve()), "--listen", str(join_port), "--upstream", str(a.host_port),
                     "--seed", str(a.impair_seed), "--run-seconds", str(int(a.timeout) + 120)] + list(pargs)
    join_args = ["--netplay-join", f"127.0.0.1:{join_port}"] + list(a.exe_args)

    stop = threading.Event()

    def default_sched(tok):
        return [("t", 0.0, f"PIKMIN_STATE 5 {tok} 1 0 127 0 0 END\n")]

    sched_host = load_state_script(a.host_state_script, token) if a.host_state_script else default_sched(token)
    sched_join = load_state_script(a.join_state_script, token_join) if a.join_state_script else default_sched(token_join)

    t0 = time.time()
    steps = {"host": [], "join": []}  # gapfix C: (index, key, wall s, tick seen)

    def refresh_sched(run, sched, host=False):
        who = "host" if host else "join"
        idx = 0
        tick_cache = {}
        framed = any(kind == "f" for kind, _v, _l in sched)
        while not stop.is_set():
            el = time.time() - t0
            if host and a.host_state_missing_until is not None and el < a.host_state_missing_until:
                stop.wait(0.1)  # B1: no host state.txt at all yet
                continue
            if host and stale_window is not None and stale_window[0] <= el < stale_window[1]:
                stop.wait(0.1)  # B1: stale link window, nothing written
                continue
            tick = hash_log_tick(run / "hashes.txt", tick_cache) if framed else None
            new_idx = sched_step(sched, idx, el, tick)
            for i in range(idx + 1, new_idx + 1):
                kind, value, _line = sched[i]
                steps[who].append((i, f"f{value}" if kind == "f" else f"{value:g}s", el, tick))
            idx = new_idx
            cur = sched[idx][2]
            pending = run / "state.tmp"
            try:
                pending.write_text(cur)
                os.replace(pending, run / "state.txt")
            except OSError:
                pass
            stop.wait(0.1)

    threads = [threading.Thread(target=refresh_sched, args=(host_run, sched_host, True)),
               threading.Thread(target=refresh_sched, args=(join_run, sched_join, False))]
    for t in threads:
        t.start()

    rc_host, rc_join = 1, 1
    detect_s = None  # M4 gap-fix S: survivor's disconnect latency after a targeted kill
    kill_fail = []   # fix round 1 (MN2): the targeted kill did not test anything
    host_proc = join_proc = None
    host_out = join_out = None
    start = time.time()
    proxy_proc = None
    proxy_out = None
    try:
        if proxy_cmd is not None:
            proxy_out = open(proxy_log, "w")
            proxy_proc = subprocess.Popen(proxy_cmd, stdout=proxy_out, stderr=subprocess.STDOUT,
                                          creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
            print(f"run_pair: impair proxy pid {proxy_proc.pid}: {' '.join(proxy_cmd)}")
            time.sleep(0.5)
        host_proc, host_out = launch(a.exe, host_run, host_boot, host_args, host_extra, host_log,
                                       unthrottled=not a.throttled)
        # Stagger the joiner slightly so the host's socket is bound first.
        time.sleep(1.0)
        join_proc, join_out = launch(join_exe, join_run, join_boot, join_args, join_extra, join_log,
                                     unthrottled=not a.throttled)
        if a.expect == "disconnect" and (a.kill_role == "host" or a.kill_on_line is not None):
            # M4 gap-fix S: targeted kill (either role, optionally when the
            # victim's log shows a line) and the survivor's detection latency.
            victim, survivor = (host_proc, join_proc) if a.kill_role == "host" else (join_proc, host_proc)
            victim_log, survivor_log = (host_log, join_log) if a.kill_role == "host" else (join_log, host_log)
            if a.kill_on_line is None:
                time.sleep(a.kill_joiner_after)
                seen = True
            else:
                t_wait = time.time()
                seen = False
                while not seen and victim.poll() is None and time.time() - t_wait < a.timeout:
                    seen = any(a.kill_on_line in ln for ln in grep(victim_log, a.kill_on_line))
                    if not seen:
                        time.sleep(0.05)
                print(f"run_pair: kill trigger {'seen' if seen else 'NOT seen'}: {a.kill_on_line!r}")
                if not seen:
                    kill_fail.append(f"kill trigger {a.kill_on_line!r} never appeared in the "
                                     f"{a.kill_role}'s log")
                if seen and a.kill_delay > 0:
                    time.sleep(a.kill_delay)
            t_kill = time.time()
            if victim.poll() is None:
                print(f"run_pair: killing {a.kill_role} pid {victim.pid} for disconnect test")
                victim.kill()
            else:
                print(f"run_pair: {a.kill_role} already exited ({victim.poll()}) before the kill")
                kill_fail.append(f"the {a.kill_role} exited ({victim.poll()}) before the kill, so "
                                 "nothing was killed")
            t_detect = None
            while survivor.poll() is None and time.time() - t_kill < a.timeout:
                if grep(survivor_log, "disconnected:"):
                    t_detect = time.time()
                    break
                time.sleep(0.05)
            if t_detect is None and grep(survivor_log, "disconnected:"):
                t_detect = time.time()  # exited between polls: upper bound
            detect_s = None if t_detect is None else t_detect - t_kill
            print("run_pair: survivor 'disconnected:' "
                  + ("not seen" if detect_s is None else f"{detect_s:.2f}s after the kill")
                  + f" (survivor={'join' if a.kill_role == 'host' else 'host'})")
            try:
                rc_victim = victim.wait(timeout=30)
            except subprocess.TimeoutExpired:
                rc_victim = 124
            try:
                rc_survivor = survivor.wait(timeout=a.timeout)
            except subprocess.TimeoutExpired:
                survivor.kill()
                rc_survivor = 124
            rc_host, rc_join = (rc_victim, rc_survivor) if a.kill_role == "host" else (rc_survivor, rc_victim)
        elif a.expect == "disconnect":
            time.sleep(a.kill_joiner_after)
            if join_proc.poll() is None:
                print(f"run_pair: killing joiner pid {join_proc.pid} for disconnect test")
                join_proc.kill()
            try:
                rc_join = join_proc.wait(timeout=30)
            except subprocess.TimeoutExpired:
                rc_join = 124
            try:
                rc_host = host_proc.wait(timeout=a.timeout)
            except subprocess.TimeoutExpired:
                host_proc.kill()
                rc_host = 124
        else:
            try:
                rc_host = host_proc.wait(timeout=a.timeout)
            except subprocess.TimeoutExpired:
                host_proc.kill()
                try:
                    rc_host = host_proc.wait(timeout=30)
                except subprocess.TimeoutExpired:
                    rc_host = 124
                print(f"run_pair: host timeout after {a.timeout}s, killed pid {host_proc.pid}")
            try:
                rc_join = join_proc.wait(timeout=60)
            except subprocess.TimeoutExpired:
                join_proc.kill()
                try:
                    rc_join = join_proc.wait(timeout=30)
                except subprocess.TimeoutExpired:
                    rc_join = 124
                print("run_pair: joiner timeout, killed pid "
                      f"{join_proc.pid if join_proc else '?'}")
    finally:
        stop.set()
        for t in threads:
            t.join()
        for f in (host_out, join_out):
            try:
                if f is not None:
                    f.close()
            except OSError:
                pass
        for proc in (host_proc, join_proc, proxy_proc):
            try:
                if proc is not None and proc.poll() is None:
                    proc.kill()
            except OSError:
                pass
        if proxy_proc is not None:
            try:
                proxy_proc.wait(timeout=10)
            except subprocess.TimeoutExpired:
                pass
        if proxy_out is not None:
            try:
                proxy_out.close()
            except OSError:
                pass
    secs = time.time() - start

    n_host = count_lines(host_hash)
    n_join = count_lines(join_hash)
    cmp_rc, cmp_tail = None, ""
    if a.expect == "sync":
        r = subprocess.run([sys.executable, str(CMP), str(host_hash), str(join_hash)],
                           capture_output=True, text=True)
        cmp_rc = r.returncode
        cmp_tail = (r.stdout + r.stderr).strip().splitlines()
        cmp_tail = cmp_tail[-1] if cmp_tail else ""
    des_host = grep(host_log, "desync detected")
    des_join = grep(join_log, "desync detected")
    ref_host = grep(host_log, "handshake refused")
    ref_join = grep(join_log, "handshake refused")
    dis_host = grep(host_log, "disconnected:")
    dis_join = grep(join_log, "disconnected:")
    # M4a same-frame apply pair: the canonical randstate apply lines must be
    # identical on both peers (same gens at the same frames).
    app_host = apply_lines(host_log)
    app_join = apply_lines(join_log)

    print(f"run_pair: expect={a.expect} ticks={a.ticks} time={secs:.1f}s")
    print(f"run_pair: host exit={rc_host} hashes={n_host} log={host_log}")
    print(f"run_pair: join exit={rc_join} hashes={n_join} log={join_log}")
    if a.expect == "sync":
        print(f"run_pair: compare exit={cmp_rc}: {cmp_tail}")
    print(f"run_pair: desync lines host={len(des_host)} join={len(des_join)}")
    print(f"run_pair: refused lines host={len(ref_host)} join={len(ref_join)}")
    print(f"run_pair: disconnected lines host={len(dis_host)}")
    print(f"run_pair: randstate applies host={len(app_host)} join={len(app_join)}")
    for who in ("host", "join"):
        for i, key, el, tick in steps[who]:
            print(f"run_pair: {who} state step {i} ({key}) at wall {el:.1f}s tick_seen={tick}")
    for ln in app_host[:12]:
        print(f"run_pair: apply host: {ln}")
    for ln in app_join[:12]:
        print(f"run_pair: apply join: {ln}")
    # M4 lane B1 summary: hold/resume lines, gameplay proof, run-dir files.
    hh = hold_lines(host_log)
    hj = hold_lines(join_log)
    print(f"run_pair: disconnected lines join={len(dis_join)}")
    for who, (hold, held, resume, ms) in (("host", hh), ("join", hj)):
        for ln in hold + held + resume:
            print(f"run_pair: {who}: {ln}")
        if ms:
            print(f"run_pair: {who}: held_ms={','.join(f'{v:.0f}' for v in ms)}")
    # Frozen time (held at -> resume, all holds) from the exit line's held=<ms>.
    for who, log in (("host", host_log), ("join", join_log)):
        vals = [ln.split(" held=")[1].split("ms")[0] for ln in grep(log, " held=")
                if " holds=" in ln]
        if vals:
            print(f"run_pair: {who}: frozen held={vals[-1]}ms (exit line)")
    tuple_fail = []
    for who, log, hashes, run in (("host", host_log, host_hash, host_run),
                                  ("join", join_log, join_hash, join_run)):
        starts = len(grep(log, "START_STAGE"))
        rand = len(grep(log, "[Pikmin Randomizer]"))
        tuples = hash_tuples(hashes)
        files = [n for n in ("checks.txt", "deaths.txt", "emperor.txt", "benefits-used.txt",
                             "mirror-events.txt") if (run / n).exists()]
        print(f"run_pair: {who}: START_STAGE={starts} randomizer_lines={rand} "
              f"distinct_tuples={tuples} files={','.join(files) if files else '-'}")
        if a.min_tuples is not None and not hh[0] and tuples <= a.min_tuples:
            tuple_fail.append(f"{who} distinct tuples {tuples} <= {a.min_tuples}")
        for hold, resume in zip(hh[0], hh[2]):
            hf, rf = frame_of(hold), frame_of(resume)
            if hf is not None and rf is not None:
                # tick = frame + 1: ticks <= H ran before the hold frame,
                # ticks > R ran from the resume frame on.
                pre = hash_tuples(hashes, hi=hf)
                post = hash_tuples(hashes, lo=rf + 1)
                print(f"run_pair: {who}: tuples before hold frame {hf}={pre} "
                      f"after resume frame {rf}={post}")
                # Before the hold only when the hold frame leaves room for
                # more than N distinct tuples (a missing-state HOLD at frame
                # 4 cannot have any gameplay before it).
                pre_due = a.min_tuples is not None and hf > a.min_tuples
                if a.min_tuples is not None and ((pre_due and pre <= a.min_tuples) or post <= a.min_tuples):
                    tuple_fail.append(f"{who} tuples before {hf}={pre} / after {rf}={post} "
                                      f"not both > {a.min_tuples}")

    # B2 summary: checkpoint decision, transfer, save barrier, resume, reseed.
    b2_needles = ("[netplay] checkpoint", "[netplay] transfer", "[netplay] save barrier",
                  "CAMPAIGN_RESUMED", "CAMPAIGN_SAVED", "[netplay] local campaign checkpoint is stale",
                  "[netplay] set aside", "[netplay] local checkpoint:", "reseed day=", "START_STAGE",
                  "handshake refused", "[netplay] bulk impairment", "[netplay] test:", "[netplay] desync",
                  "[netplay] p2 ", "[netplay] sidecars")
    for who, log, hashes in (("host", host_log, host_hash), ("join", join_log, join_hash)):
        try:
            text = Path(log).read_text(errors="replace").splitlines()
        except OSError:
            text = []
        for ln in text:
            if any(n in ln for n in b2_needles):
                print(f"run_pair: {who}: {ln.strip()}")
        for ln in text:
            m = re.search(r"reseed day=(\d+) .*tick=(\d+)", ln)
            if m:
                after = hash_tuples(hashes, lo=int(m.group(2)) + 1)
                print(f"run_pair: {who}: distinct tuples after the day-{m.group(1)} reseed tick "
                      f"{m.group(2)}: {after}")

    # M4 gap-fix S: load guard lines (test stall, long ticks, load windows).
    # The windows open and close at deterministic frames, so their frame
    # sequence must be identical on both peers (the durations are not).
    lg_needles = ("[netplay] load guard", "[netplay] test stall", "[netplay] long tick",
                  "[netplay] load window", "[netplay] test load delay", "[netplay] disconnect timeout")
    win_frames = {}
    for who, log in (("host", host_log), ("join", join_log)):
        try:
            text = Path(log).read_text(errors="replace").splitlines()
        except OSError:
            text = []
        wins = []
        for ln in text:
            if any(n in ln for n in lg_needles):
                print(f"run_pair: {who}: {ln.strip()}")
            m = re.search(r"\[netplay\] load window: (open|closed) at frame=(\d+)", ln)
            if m:
                wins.append((m.group(1), int(m.group(2))))
        win_frames[who] = wins
    win_same = win_frames["host"] == win_frames["join"]
    print(f"run_pair: load windows host={len(win_frames['host'])} join={len(win_frames['join'])} "
          f"frames {'identical' if win_same else 'DIFFER'}")
    # Fix round 1 (MN3): a peer that armed a stall applying to it must have
    # stalled; otherwise the run would pass without testing anything.
    stall_fail = []
    for who, log in (("host", host_log), ("join", join_log)):
        armed = [ln for ln in grep(log, "[netplay] test stall: armed") if "this peer stalls" in ln]
        begins = grep(log, "[netplay] test stall: begin")
        ends = [re.search(r"test stall: end after (\d+) ms", ln) for ln in grep(log, "[netplay] test stall: end")]
        took = [int(m.group(1)) for m in ends if m]
        if armed or begins:
            print(f"run_pair: {who}: test stall armed={len(armed)} fired={len(begins)} "
                  f"durations_ms={','.join(str(v) for v in took) if took else '-'}")
        if armed and not begins:
            stall_fail.append(f"{who} armed a test stall for itself but never stalled "
                              "(no 'test stall: begin' line)")

    # M5c lane B: adaptive delay, stall stats and the link proxy.
    ad_needles = ("[netplay] adaptive delay:", "[netplay] delay change:", "[netplay] delay hold at",
                  "[netplay] stats final:", "[netplay] delay timeline:", "[netplay] frame-time histogram",
                  "[netplay] auto delay:", "[netplay] session started:")
    for who, log in (("host", host_log), ("join", join_log)):
        try:
            text = Path(log).read_text(errors="replace").splitlines()
        except OSError:
            text = []
        changes = [ln for ln in text if "[netplay] delay change:" in ln]
        many = len(changes) > 40
        for ln in text:
            if any(n in ln for n in ad_needles) and not ("[netplay] delay change:" in ln and many):
                print(f"run_pair: {who}: {ln.strip()}")
        if many:
            print(f"run_pair: {who}: {len(changes)} delay changes (first/last shown)")
            for ln in changes[:5] + changes[-5:]:
                print(f"run_pair: {who}: {ln.strip()}")
        exits = [ln for ln in text if "[netplay] wall=" in ln and " stall=" in ln]
        if exits:
            print(f"run_pair: {who}: {exits[-1].strip()}")
    if proxy_cmd is not None:
        try:
            for ln in Path(proxy_log).read_text(errors="replace").splitlines():
                if ln.startswith(("[impair] block", "[impair] done", "[impair] listening")):
                    print(f"run_pair: proxy: {ln.strip()}")
        except OSError:
            print(f"run_pair: proxy log missing: {proxy_log}")

    ok = True
    if a.expect in ("sync", "disconnect"):
        for msg in stall_fail:
            print(f"run_pair: FAIL: {msg}")
            ok = False
    if a.expect == "sync":
        if not win_same:
            print("run_pair: FAIL: load window frames differ between peers")
            ok = False
        if rc_host != 0 or rc_join != 0:
            ok = False
        if cmp_rc != 0:
            ok = False
        if des_host or des_join:
            ok = False
        if app_host != app_join:
            print("run_pair: FAIL: randstate apply lines differ between peers")
            ok = False
        if n_host != a.ticks or n_join != a.ticks:
            print(f"run_pair: FAIL: hash lines {n_host}/{n_join} != requested {a.ticks}")
            ok = False
        if a.expect_hold is not None:
            n = a.expect_hold
            for who, (hold, held, resume, _ms) in (("host", hh), ("join", hj)):
                if len(hold) != n or len(held) != n or len(resume) != n:
                    print(f"run_pair: FAIL: {who} hold/held/resume counts "
                          f"{len(hold)}/{len(held)}/{len(resume)} != {n}")
                    ok = False
            if hh[:3] != hj[:3]:
                print("run_pair: FAIL: hold/held/resume lines differ between peers")
                ok = False
            if dis_host or dis_join:
                print("run_pair: FAIL: disconnected lines present")
                ok = False
            if a.expect_held_ms is not None:
                for who, (_h, _d, _r, ms) in (("host", hh), ("join", hj)):
                    if not ms or min(ms) < a.expect_held_ms:
                        print(f"run_pair: FAIL: {who} held_ms {ms} not all >= {a.expect_held_ms:.0f}")
                        ok = False
        if a.expect_no_hold:
            for who, (hold, held, resume, _ms) in (("host", hh), ("join", hj)):
                if hold or held or resume:
                    print(f"run_pair: FAIL: {who} has hold/held/resume lines "
                          f"({len(hold)}/{len(held)}/{len(resume)}) in a negative control")
                    ok = False
        for msg in tuple_fail:
            print(f"run_pair: FAIL: {msg}")
            ok = False
    elif a.expect == "refuse":
        if rc_host != 4 or rc_join != 4:
            print(f"run_pair: FAIL: expected both exit 4, got {rc_host}/{rc_join}")
            ok = False
        if not ref_host or not ref_join:
            print("run_pair: FAIL: expected refused lines on both peers")
            ok = False
    elif a.expect == "disconnect":
        s_role = "join" if a.kill_role == "host" else "host"
        rc_s, dis_s = (rc_join, dis_join) if s_role == "join" else (rc_host, dis_host)
        if rc_s != 0:
            print(f"run_pair: FAIL: expected {s_role} exit 0, got {rc_s}")
            ok = False
        if not dis_s:
            print(f"run_pair: FAIL: expected a disconnected line on the {s_role}")
            ok = False
        if a.max_detect_s is not None and (detect_s is None or detect_s > a.max_detect_s):
            print(f"run_pair: FAIL: detection {detect_s} s not within {a.max_detect_s} s of the kill")
            ok = False
        for msg in kill_fail:
            print(f"run_pair: FAIL: {msg}")
            ok = False
    elif a.expect == "desync":
        # B2 fix round 1 (C1): a barrier desync must end BOTH peers with exit 5.
        if rc_host != 5 or rc_join != 5:
            print(f"run_pair: FAIL: expected both exit 5, got {rc_host}/{rc_join}")
            ok = False
        for who, log in (("host", host_log), ("join", join_log)):
            if not [ln for ln in grep(log, "[netplay] save barrier:") if "mismatch" in ln]:
                print(f"run_pair: FAIL: no save barrier mismatch line on the {who}")
                ok = False
    elif a.expect == "hash-desync":
        # Gapfix C: a deliberate one-sided sim-state change (for example
        # PIKMIN_NETPLAY_TEST_COOP_PERTURB on one peer) must be caught by the
        # per-tick state hash: a '[netplay] desync detected:' line, exit 5 on
        # every detecting peer, and no clean exit.
        detectors = [who for who, lines in (("host", des_host), ("join", des_join)) if lines]
        for ln in des_host + des_join + grep(host_log, "desync subs") + grep(join_log, "desync subs"):
            print(f"run_pair: {ln.strip()}")
        if not detectors:
            print("run_pair: FAIL: no '[netplay] desync detected:' line on either peer")
            ok = False
        for who, rc, lines in (("host", rc_host, des_host), ("join", rc_join, des_join)):
            if lines and rc != 5:
                print(f"run_pair: FAIL: the {who} detected the desync but exited {rc}, not 5")
                ok = False
            if rc == 0:
                print(f"run_pair: FAIL: the {who} exited 0: the run was not stopped by the desync")
                ok = False
        r = subprocess.run([sys.executable, str(CMP), str(host_hash), str(join_hash)],
                           capture_output=True, text=True)
        tail = (r.stdout + r.stderr).strip().splitlines()
        for ln in tail:
            print(f"run_pair: compare: {ln}")
    elif a.expect == "barrier-timeout":
        # B2 fix round 1 (C2): the host dies at its day-end save (test knob,
        # exit 7); the joiner's barrier times out (exit 6) and retracts.
        if rc_host != 7 or rc_join != 6:
            print(f"run_pair: FAIL: expected host exit 7 and joiner exit 6, got {rc_host}/{rc_join}")
            ok = False
        if not grep(join_log, "[netplay] save barrier timeout"):
            print("run_pair: FAIL: no save barrier timeout line on the joiner")
            ok = False
    print(f"run_pair: {'PASS' if ok else 'FAIL'}")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
