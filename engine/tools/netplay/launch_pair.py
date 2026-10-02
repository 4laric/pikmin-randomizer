"""Launcher pair test for the netplay one-command lane (issue #887).

Runs a host and a joiner through the one-command switches only
(--netplay-host-ice / --netplay-join-ice, --netplay-test-hidden,
--netplay-test-ticks, --netplay-input), moving the codes only through the
files a human would copy-paste through (the host's --netplay-code-out offer
file is the joiner's @file; the joiner's --netplay-code-out answer file is
the host's --netplay-answer-in).

What the harness does NOT do, so the launcher has to (fix round, B1/B2):
  * no bootstrap file, no --randomizer-seed, no state.txt refresher and no
    SESSION token for either peer: the host builds its bootstrap (default or
    --bootstrap-host), the joiner gets it from the offer, the launcher writes
    the run bootstrap and the randomizer writes its own static state.txt;
  * no NECTAR_SAVE_DIR: the launcher sets its private save dir before init;
  * no settings file for the joiner in variant (a).

Each peer runs with its own working directory (<out>/host, <out>/join),
each holding an `assets` junction (and, per variant, a settings file). The
exe runs from a staging dir (--stage), so the launcher's run dirs land in
<stage>/netplay/ under scratch, never under the build tree; the harness
checks that nothing was written to <stage>/save or <stage>/campaign.

Variants:
  a  no joiner settings file (pure bundle adoption).
  b  joiner settings differ in presentation keys only (window size, gamma,
     brightness, a keybind): identical session.
  c  joiner settings differ in sim keys (including dayLength) from a host
     file with other sim values: the session runs the host's, stays
     identical, and the joiner's file is byte-identical afterwards even
     though the F1 test hook runs the settings save path mid-session.
  d  host --bootstrap <file> (a real seed). M4 lane B2 (issue #885): a P2
     seed (ENEMY_P2) plays through the launcher: pass --p2-assets DIR (the
     joiner's own copy of the seed's P2 assets overlay, handed over as
     --netplay-p2-assets) and expect sync. --expect join-refuses checks that
     a P2 offer without --p2-assets is refused before any run folder exists;
     --env-host / --env-join add test knobs (for example
     PIKMIN_NETPLAY_TEST_TAMPER_SIDECARS=1) and --expect refuse expects both
     peers to exit 4 with a `handshake refused` line.

Gameplay proof (every sync pair): both logs carry `[Pikmin Randomizer]
initialized` and `START_STAGE`, and the navi/piki/teki/item hash columns are
non-zero and change; the number of distinct (navi, piki, teki, item) tuples
is reported.

Hidden, private, bounded: PIKMIN_RANDOMIZER_TEST_BACKGROUND=1 and
SDL_AUDIODRIVER=dummy (also set by --netplay-test-hidden), a hard timeout,
and only the two spawned PIDs are ever signalled.
"""

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import run_pair as rp  # noqa: E402  (link_assets, gen_inputs, CMP, DEFAULT_ASSETS)

# Every netplay/test env var a caller's shell might leak into the peers.
SCRUB_KEYS = tuple(rp.SCRUB_KEYS) + (
    "NECTAR_SAVE_DIR",
    "PIKMIN_NETPLAY_ICE_HOST",
    "PIKMIN_NETPLAY_ICE_JOIN",
    "PIKMIN_NETPLAY_ICE_CODE_OUT",
    "PIKMIN_NETPLAY_ICE_ANSWER_IN",
    "PIKMIN_NETPLAY_STUN",
    "PIKMIN_NETPLAY_TURN",
    "PIKMIN_NETPLAY_ICE_TURN_ONLY",
    "PIKMIN_NETPLAY_ICE_PORT_BEGIN",
    "PIKMIN_NETPLAY_ICE_PORT_END",
    "PIKMIN_NETPLAY_ICE_TIMEOUT_MS",
    "PIKMIN_NETPLAY_ICE_GATHER_TIMEOUT_MS",
    "PIKMIN_NETPLAY_ICE_BIND",
    "PIKMIN_NETPLAY_INPUT",
    "PIKMIN_NETPLAY_TEST_SESSION_TOKEN",
    "PIKMIN_NETPLAY_TEST_F1_CYCLE_TICK",
    "PIKMIN_RANDOMIZER_AUTOPLAY",
    "BBFT_PORT",
)

HOST_SETTINGS_C = {
    # Sim keys the randomizer does not mask, plus the M2 day length.
    "chainActions": "1", "betterPathfinding": "1", "noTrip": "1", "lockOn": "1",
    "charge": "1", "throwCancelB": "1", "instantWhistle": "1", "dayLength": "10",
    "pikiLimit": "150",
}
JOIN_SETTINGS_C = {
    "chainActions": "0", "betterPathfinding": "0", "noTrip": "0", "lockOn": "0",
    "charge": "0", "throwCancelB": "0", "instantWhistle": "0", "dayLength": "20",
    "pikiLimit": "50", "bluesOnlyWater": "1", "holdToPluck": "1",
    "windowWidth": "800", "windowHeight": "600",
}
JOIN_SETTINGS_B = {
    # Presentation only: window size, gamma, brightness, a keybind. (Audio
    # volume is a game option on the memory card, not a settings-file key;
    # the card is private per run.)
    "windowWidth": "800", "windowHeight": "600", "gamma": "1.5",
    "brightness": "0.1", "key_5": "44",
}


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def write_settings(path, kv):
    # A hand-written file (not the game's canonical format), so a rewrite by
    # the game would change its bytes.
    with open(path, "w", newline="\n") as f:
        f.write("# launch_pair settings\n")
        for key, value in kv.items():
            f.write(f"{key} = {value}\n")


def wait_code(path, timeout, what, procs):
    start = time.time()
    while time.time() - start < timeout:
        try:
            text = Path(path).read_text(errors="replace").strip()
        except OSError:
            text = ""
        if text.startswith("NPIX"):
            return text
        for p in procs:
            if p is not None and p.poll() is not None:
                raise RuntimeError(f"{what}: peer pid {p.pid} exited ({p.returncode}) before writing it")
        time.sleep(0.2)
    raise RuntimeError(f"timeout waiting for {what} at {path}")


def stage_exe(exe, stage):
    stage.mkdir(parents=True, exist_ok=True)
    dst = stage / "nectar.exe"
    if not dst.exists() or sha256_file(dst) != sha256_file(exe):
        shutil.copy2(str(exe), str(dst))
    return dst


def launch(exe, cwd, args, env_extra, log_path):
    env = rp.scrub_env(dict(os.environ))
    for key in SCRUB_KEYS:  # launch_pair-only extras (NECTAR_SAVE_DIR, PIKMIN_RANDOMIZER_AUTOPLAY, BBFT_PORT)
        env.pop(key, None)
    env.update(PIKMIN_RANDOMIZER_TEST_BACKGROUND="1", SDL_AUDIODRIVER="dummy")
    # Loopback-only sockets: test peers never touch a real adapter, so
    # Windows Firewall never prompts for the per-run exe copies.
    env["PIKMIN_NETPLAY_UDP_BIND"] = "127.0.0.1"
    env["PIKMIN_NETPLAY_ICE_BIND"] = "127.0.0.1"
    env.update(env_extra)
    startup = None
    if sys.platform == "win32":
        startup = subprocess.STARTUPINFO()
        startup.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        startup.wShowWindow = 0
    out = open(log_path, "w")
    proc = subprocess.Popen([str(exe)] + list(args), cwd=str(cwd), env=env, startupinfo=startup,
                            stdout=out, stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL)
    return proc, out


def grep(path, needle):
    try:
        text = Path(path).read_text(errors="replace")
    except OSError:
        return []
    return [ln for ln in text.splitlines() if needle in ln]


def gameplay_stats(hash_path):
    """Distinct (navi, piki, teki, item) tuples, and the gameplay ticks."""
    tuples, nonzero, first = set(), 0, None
    zero = "0" * 16
    try:
        lines = Path(hash_path).read_text(errors="replace").splitlines()
    except OSError:
        lines = []
    for ln in lines:
        parts = ln.split()
        if len(parts) < 6:
            continue
        cols = tuple(parts[2:6])  # navi piki teki item
        tuples.add(cols)
        if all(c != zero for c in cols):
            nonzero += 1
            if first is None:
                first = int(parts[0])
    return {"ticks": len(lines), "distinct_tuples": len(tuples), "all_four_nonzero_ticks": nonzero,
            "first_gameplay_tick": first}


def run_dir_of(log_path):
    for ln in grep(log_path, "[netplay] launch: role="):
        m = re.search(r"run dir (.+)$", ln)
        if m:
            return Path(m.group(1).strip())
    return None


def tree(path):
    out = []
    if path is None or not Path(path).exists():
        return out
    for root, dirs, files in os.walk(path):
        # B2: never walk into a junction (play/assets points at a P2 overlay).
        dirs[:] = sorted(d for d in dirs if not os.path.isjunction(os.path.join(root, d)))
        for name in sorted(files):
            full = Path(root) / name
            rel = full.relative_to(path).as_posix()
            if "/shader_cache/" in "/" + rel:
                continue  # driver-generated binaries: counted, not listed
            out.append(f"{rel} ({full.stat().st_size} B)")
        if Path(root).name == "shader_cache":
            out.append(f"{Path(root).relative_to(path).as_posix()}/ ({len(files)} shader binaries)")
    return out


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--exe", type=Path, required=True, help="netplay build nectar.exe (copied into --stage)")
    p.add_argument("--stage", type=Path, required=True, help="exe dir for the pair (scratch)")
    p.add_argument("--out", type=Path, required=True, help="pair dir: host/ and join/ cwds, codes, logs")
    p.add_argument("--variant", choices=("a", "b", "c", "d"), default="a")
    p.add_argument("--ticks", type=int, default=3000)
    p.add_argument("--assets", type=Path, default=rp.DEFAULT_ASSETS)
    p.add_argument("--port-base", type=int, default=48100, help="host ICE ports base..base+9, joiner +10..+19")
    p.add_argument("--seed-a", type=int, default=101, help="host scripted-input seed")
    p.add_argument("--seed-b", type=int, default=202, help="joiner scripted-input seed")
    p.add_argument("--bootstrap-host", type=Path, default=None, help="host --bootstrap <file> (variant d)")
    p.add_argument("--expect", choices=("sync", "host-refuses", "join-refuses", "refuse"), default="sync")
    p.add_argument("--p2-assets", type=Path, default=None,
                   help="M4 B2: the joiner's P2 assets overlay (passed as --netplay-p2-assets)")
    p.add_argument("--env-host", nargs="*", default=[], metavar="K=V", help="M4 B2: extra env for the host")
    p.add_argument("--env-join", nargs="*", default=[], metavar="K=V", help="M4 B2: extra env for the joiner")
    p.add_argument("--f1-cycle-tick", type=int, default=0,
                   help="joiner: open/close F1 after this tick (settings save path); variant c defaults to 1500")
    p.add_argument("--timeout", type=float, default=1200)
    p.add_argument("--code-timeout", type=float, default=180)
    p.add_argument("--min-distinct", type=int, default=100,
                   help="gameplay proof: minimum distinct (navi,piki,teki,item) tuples")
    a = p.parse_args(argv)

    out = a.out.resolve()
    if out.exists():
        shutil.rmtree(out)
    host_cwd, join_cwd = out / "host", out / "join"
    host_cwd.mkdir(parents=True)
    join_cwd.mkdir(parents=True)
    rp.link_assets(host_cwd, a.assets)
    rp.link_assets(join_cwd, a.assets)
    stage = a.stage.resolve()
    exe = stage_exe(a.exe.resolve(), stage)
    stage_before = {d: sorted(os.listdir(stage / d)) if (stage / d).exists() else None
                    for d in ("save", "campaign")}

    host_conf, join_conf = host_cwd / "pikmin_settings.conf", join_cwd / "pikmin_settings.conf"
    if a.variant == "b":
        write_settings(join_conf, JOIN_SETTINGS_B)
    elif a.variant == "c":
        write_settings(host_conf, HOST_SETTINGS_C)
        write_settings(join_conf, JOIN_SETTINGS_C)
    sha_before = {name: sha256_file(f) for name, f in (("host", host_conf), ("join", join_conf)) if f.exists()}

    offer_file, answer_file = out / "offer.txt", out / "answer.txt"
    host_hash, join_hash = host_cwd / "hashes.txt", join_cwd / "hashes.txt"
    host_log, join_log = out / "host.log", out / "join.log"
    host_inputs, join_inputs = out / "host_inputs.pkni", out / "join_inputs.pkni"
    rp.gen_inputs(a.ticks + 50, a.seed_a, host_inputs)
    rp.gen_inputs(a.ticks + 50, a.seed_b, join_inputs)

    common = {
        "PIKMIN_NETPLAY_STUN": "none",          # loopback: host candidates only
        "PIKMIN_NETPLAY_UNTHROTTLED": "1",      # tests run as fast as the session allows
        "PIKMIN_NETPLAY_ICE_TIMEOUT_MS": "120000",
        "PIKMIN_NETPLAY_HANDSHAKE_TIMEOUT_MS": "30000",
    }
    host_env = dict(common, PIKMIN_STATE_HASH_LOG=str(host_hash),
                    PIKMIN_NETPLAY_LOCAL_INPUT_FILE=str(host_inputs),
                    PIKMIN_NETPLAY_ICE_PORT_BEGIN=str(a.port_base),
                    PIKMIN_NETPLAY_ICE_PORT_END=str(a.port_base + 9))
    join_env = dict(common, PIKMIN_STATE_HASH_LOG=str(join_hash),
                    PIKMIN_NETPLAY_LOCAL_INPUT_FILE=str(join_inputs),
                    PIKMIN_NETPLAY_ICE_PORT_BEGIN=str(a.port_base + 10),
                    PIKMIN_NETPLAY_ICE_PORT_END=str(a.port_base + 19))
    host_env.update(rp.parse_kv(a.env_host, "env-host"))
    join_env.update(rp.parse_kv(a.env_join, "env-join"))
    f1_tick = a.f1_cycle_tick or (1500 if a.variant == "c" else 0)
    if f1_tick:
        join_env["PIKMIN_NETPLAY_TEST_F1_CYCLE_TICK"] = str(f1_tick)

    host_args = ["--netplay-host-ice", "--netplay-code-out", str(offer_file),
                 "--netplay-answer-in", str(answer_file), "--netplay-test-hidden",
                 "--netplay-test-ticks", str(a.ticks), "--netplay-input", "keyboard"]
    if a.bootstrap_host is not None:
        host_args += ["--bootstrap", str(a.bootstrap_host.resolve())]
    join_args = ["--netplay-join-ice", f"@{offer_file}", "--netplay-code-out", str(answer_file),
                 "--netplay-test-hidden", "--netplay-test-ticks", str(a.ticks),
                 "--netplay-input", "gamepad:0"]
    if a.p2_assets is not None:
        join_args += ["--netplay-p2-assets", str(a.p2_assets.resolve())]

    summary = {"variant": a.variant, "ticks": a.ticks, "exe": str(exe), "exe_sha256": sha256_file(exe),
               "host_cmd": [str(exe)] + host_args, "join_cmd": [str(exe)] + join_args}
    rc_host = rc_join = None
    host_proc = join_proc = None
    files = []
    start = time.time()
    try:
        host_proc, f = launch(exe, host_cwd, host_args, host_env, host_log)
        files.append(f)
        if a.expect == "host-refuses":
            rc_host = host_proc.wait(timeout=120)
        elif a.expect == "join-refuses":
            offer = wait_code(offer_file, a.code_timeout, "host offer", [host_proc])
            summary["offer_chars"] = len(offer)
            join_proc, f = launch(exe, join_cwd, join_args, join_env, join_log)
            files.append(f)
            rc_join = join_proc.wait(timeout=120)
            # The host waits for an answer that never comes: stop our own PID.
            if host_proc.poll() is None:
                host_proc.kill()
                host_proc.wait(timeout=30)
            rc_host = host_proc.returncode
        elif a.expect == "refuse":
            offer = wait_code(offer_file, a.code_timeout, "host offer", [host_proc])
            summary["offer_chars"] = len(offer)
            join_proc, f = launch(exe, join_cwd, join_args, join_env, join_log)
            files.append(f)
            for proc in (host_proc, join_proc):
                proc.wait(timeout=240)
            rc_host, rc_join = host_proc.returncode, join_proc.returncode
        else:
            offer = wait_code(offer_file, a.code_timeout, "host offer", [host_proc])
            summary["offer_chars"] = len(offer)
            join_proc, f = launch(exe, join_cwd, join_args, join_env, join_log)
            files.append(f)
            answer = wait_code(answer_file, a.code_timeout, "joiner answer", [host_proc, join_proc])
            summary["answer_chars"] = len(answer)
            deadline = start + a.timeout
            for proc in (host_proc, join_proc):
                proc.wait(timeout=max(1.0, deadline - time.time()))
            rc_host, rc_join = host_proc.returncode, join_proc.returncode
    except (RuntimeError, subprocess.TimeoutExpired) as e:
        summary["error"] = str(e)
        print(f"launch_pair: {e}")
    finally:
        for proc in (host_proc, join_proc):
            if proc is not None and proc.poll() is None:
                print(f"launch_pair: killing pid {proc.pid}")
                proc.kill()
                try:
                    proc.wait(timeout=30)
                except subprocess.TimeoutExpired:
                    pass
        for f in files:
            f.close()
    summary["seconds"] = round(time.time() - start, 1)
    summary["exit"] = {"host": rc_host, "join": rc_join}

    ok = True
    # B2: the P2 / checkpoint / transfer lines of both peers, and whether each
    # peer's hello.txt advertises the P2 bridge.
    b2 = {}
    for side, log in (("host", host_log), ("join", join_log)):
        b2[side] = [ln.strip() for ln in (grep(log, "[netplay] p2") + grep(log, "[netplay] launch: P2")
                                        + grep(log, "[netplay] checkpoint") + grep(log, "[netplay] transfer")
                                        + grep(log, "sidecars received") + grep(log, "handshake refused")
                                        + grep(log, "[netplay] launch: refusing") + grep(log, "settings file pinned"))]
        rd = run_dir_of(log)
        hellos = sorted(Path(rd).glob("session/runs/*/hello.txt")) if rd else []
        b2[side + "_hello_p2_bridge"] = any("p2-enemy-bridge-v1" in h.read_text(errors="replace") for h in hellos)
    summary["b2"] = b2
    for side in ("host", "join"):
        for ln in b2[side]:
            print(f"launch_pair: {side} {ln}")
        print(f"launch_pair: {side} hello.txt advertises p2-enemy-bridge-v1: {b2[side + '_hello_p2_bridge']}")
    if a.expect == "join-refuses":
        refusal = grep(join_log, "[netplay] launch:")
        created = grep(join_log, "[netplay] launch: role=")
        summary["refusal"] = refusal
        ok = rc_join == 2 and bool(grep(join_log, "--netplay-p2-assets")) and not created
        print(f"launch_pair: join exit={rc_join} (expect 2), run dir created={bool(created)}")
        for ln in refusal:
            print(f"launch_pair: join {ln.strip()}")
    elif a.expect == "refuse":
        ref_h, ref_j = grep(host_log, "handshake refused"), grep(join_log, "handshake refused")
        ok = rc_host == 4 and rc_join == 4 and bool(ref_h) and bool(ref_j)
        print(f"launch_pair: exit host={rc_host} join={rc_join} (expect 4/4); refused host={ref_h} join={ref_j}")
    elif a.expect == "host-refuses":
        refusal = grep(host_log, "[netplay] launch: refusing")
        summary["refusal"] = refusal
        created = [ln for ln in grep(host_log, "[netplay] launch: role=")]
        ok = rc_host == 2 and bool(refusal) and not created and not offer_file.exists()
        print(f"launch_pair: host exit={rc_host} (expect 2), refusal lines={len(refusal)}, run dir created={bool(created)}")
        for ln in refusal:
            print(f"launch_pair: {ln.strip()}")
    else:
        r = subprocess.run([sys.executable, str(rp.CMP), str(host_hash), str(join_hash)],
                           capture_output=True, text=True)
        cmp_tail = (r.stdout + r.stderr).strip().splitlines()
        summary["compare"] = {"exit": r.returncode, "last": cmp_tail[-1] if cmp_tail else ""}
        for side, log, hashes in (("host", host_log, host_hash), ("join", join_log, join_hash)):
            stats = gameplay_stats(hashes)
            info = {
                "stats": stats,
                "randomizer_initialized": grep(log, "[Pikmin Randomizer] initialized")[:1],
                "start_stage": grep(log, "START_STAGE")[:2],
                "launcher_state": grep(log, "netplay launcher state")[:1],
                "desync": grep(log, "desync detected"),
                "refused": grep(log, "handshake refused"),
                "config": grep(log, "[netplay] config=")[:1],
                "session_config": grep(log, "[netplay] launch: session config")[:1],
                "bootstrap": grep(log, "[netplay] bootstrap=")[:1],
                "launch": grep(log, "[netplay] launch:"),
                "settings": grep(log, "[PC Settings]"),
                "card": grep(log, "CARDInit()"),
                "adopted": grep(log, "adopted the host's sim settings"),
                "f1": grep(log, "test hook"),
                "delay": grep(log, "auto delay:")[:1],
            }
            rd = run_dir_of(log)
            info["run_dir"] = str(rd) if rd else None
            info["run_tree"] = tree(rd)
            summary[side] = info
            if not info["randomizer_initialized"] or not info["start_stage"]:
                print(f"launch_pair: FAIL: {side} log lacks the randomizer init / START_STAGE lines")
                ok = False
            if stats["ticks"] != a.ticks:
                print(f"launch_pair: FAIL: {side} hash lines {stats['ticks']} != {a.ticks}")
                ok = False
            if stats["all_four_nonzero_ticks"] == 0 or stats["distinct_tuples"] < a.min_distinct:
                print(f"launch_pair: FAIL: {side} shows no gameplay ({stats})")
                ok = False
            if info["desync"] or info["refused"]:
                ok = False
            card = info["card"][0] if info["card"] else ""
            if not rd or str(rd).replace("\\", "/").lower() not in card.replace("\\", "/").lower():
                print(f"launch_pair: FAIL: {side} CARDInit path is not inside its run dir: {card}")
                ok = False
        if rc_host != 0 or rc_join != 0 or r.returncode != 0:
            ok = False
        if not summary["host"]["session_config"] or \
           summary["host"]["session_config"] != summary["join"]["session_config"]:
            print("launch_pair: FAIL: the peers do not log the same session config")
            ok = False
        if summary["host"]["config"] != summary["join"]["config"] or \
           summary["host"]["bootstrap"] != summary["join"]["bootstrap"]:
            print("launch_pair: FAIL: config/bootstrap hash lines differ between the peers")
            ok = False
        if summary["host"]["run_dir"] == summary["join"]["run_dir"]:
            print("launch_pair: FAIL: the peers share a run dir")
            ok = False
    sha_after = {name: sha256_file(f) for name, f in (("host", host_conf), ("join", join_conf)) if f.exists()}
    summary["settings_sha256"] = {"before": sha_before, "after": sha_after}
    if sha_before != sha_after:
        print(f"launch_pair: FAIL: a settings file changed: {sha_before} -> {sha_after}")
        ok = False
    stage_after = {d: sorted(os.listdir(stage / d)) if (stage / d).exists() else None
                   for d in ("save", "campaign")}
    summary["stage_save_campaign"] = {"before": stage_before, "after": stage_after}
    if stage_after != stage_before or any(v is not None for v in stage_after.values()):
        print(f"launch_pair: FAIL: something was written to {stage}/save or {stage}/campaign: {stage_after}")
        ok = False
    summary["pass"] = ok

    (out / "summary.json").write_text(json.dumps(summary, indent=2))
    print(f"launch_pair: variant={a.variant} ticks={a.ticks} time={summary['seconds']}s exe={exe}")
    if a.expect == "sync":
        print(f"launch_pair: exit host={rc_host} join={rc_join}; compare: {summary['compare']['last']}")
        for side in ("host", "join"):
            s = summary[side]
            print(f"launch_pair: {side} run dir {s['run_dir']}")
            print(f"launch_pair: {side} gameplay {s['stats']}")
            for key in ("randomizer_initialized", "start_stage", "launcher_state", "session_config", "config",
                        "bootstrap",
                        "card", "adopted", "f1", "delay"):
                for ln in s[key]:
                    print(f"launch_pair: {side} {ln.strip()}")
        print(f"launch_pair: offer {summary.get('offer_chars')} chars, answer {summary.get('answer_chars')} chars")
    print(f"launch_pair: settings sha256 before={sha_before} after={sha_after}")
    print(f"launch_pair: {stage}/save and /campaign: {stage_after}")
    print(f"launch_pair: {'PASS' if ok else 'FAIL'}")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
