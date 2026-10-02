"""Replay a netplay session input log offline, on one machine (issue #1037).

Every netplay session writes `session-inputs.pknl` into its run folder: both
players' confirmed inputs for every frame, plus this game's state hash after
each frame (pc_port/netplay/pc_netplay_inlog.h). This tool starts the netplay
exe with PIKMIN_NETPLAY_REPLAY_LOG: the same session driver and the same
per-Advance body run with no network, one logged frame at a time, so the whole
deterministic sim replays from the session's start state. The exe prints
per-tick sub-hashes (PIKMIN_STATE_HASH_LOG, the usual `tick total navi piki
teki item world rng rand` lines) and compares its total against the recorded
one every frame. Nothing is simulated by this script; it only builds the run
folder and launches one hidden, private, bounded process (only that PID is ever
signalled).

Start state:
  pair mode      (the log was recorded by run_pair.py / --netplay-host UDP): the
                 recorded peer's run folder (--src-run, default: the folder the
                 log is in) supplies bootstrap.txt and pikmin_settings.conf; a
                 session that continued a campaign (meta checkpoint_gen > 0)
                 also needs --campaign-src (the campaign folder holding that
                 checkpoint and the card).
  launcher mode  (recorded by --netplay-host-ice / --netplay-join-ice): the
                 replay runs `--netplay-host-ice [--continue <folder>]` from a
                 private staging dir, so the launcher builds the run folder and
                 copies the continued checkpoint exactly as the session did;
                 --continue-from overrides the log's continue_from path (the
                 recorded run folder is only read). The recorded settings
                 (--src-run/settings-at-start.conf) become the replay's
                 pikmin_settings.conf.
The replay always runs as the HOST role (the sim is the same for both peers);
the log may be either peer's.

Exit code: 0 when the replay finished and every recorded hash reproduced, 8
when the exe finished with mismatches (the first one is named), other codes are
launch failures. With --compare-hashes FILE (a recorded run's hashes.txt) the
replay's own hash log is also diffed against it line by line.

  py -3.12 tools/netplay/replay_session.py --exe <np nectar.exe> --log
      <run>/session-inputs.pknl --out <scratch dir> [--dump-ticks 41536]
"""

import argparse
import hashlib
import os
import shutil
import subprocess
import sys
import threading
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import pknl  # noqa: E402
import run_pair as rp  # noqa: E402

DEFAULT_ASSETS = rp.DEFAULT_ASSETS


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def read_session_token(boot):
    for ln in Path(boot).read_text(errors="replace").splitlines():
        if ln.startswith("SESSION "):
            return ln[len("SESSION "):].strip()
    return None


def refresher(run, text, stop):
    while not stop.is_set():
        pending = run / "state.tmp"
        try:
            pending.write_text(text)
            os.replace(pending, run / "state.txt")
        except OSError:
            pass
        stop.wait(0.1)


def copy_campaign(src, dst, gen):
    """The checkpoint of generation `gen`, the card and the ledgers (not other checkpoints)."""
    dst.mkdir(parents=True, exist_ok=True)
    name = f"{gen:020d}.sav"
    shutil.copyfile(src / name, dst / name)
    for item in src.iterdir():
        if item.is_dir() and item.name == "card":
            shutil.copytree(item, dst / "card", dirs_exist_ok=True)
        elif item.is_file() and ".sav" not in item.name and ".tmp" not in item.name and not item.name.startswith("."):
            shutil.copyfile(item, dst / item.name)


def compare_hash_logs(recorded, replayed):
    """(compared, first differing tick or None, differing columns) of two hash logs."""
    cols = ("total", "navi", "piki", "teki", "item", "world", "rng", "rand")
    a = recorded.read_text(errors="replace").splitlines()
    b = replayed.read_text(errors="replace").splitlines()
    n = min(len(a), len(b))
    for i in range(n):
        pa, pb = a[i].split(), b[i].split()
        if pa != pb:
            diff = [cols[j - 1] for j in range(1, min(len(pa), len(pb), 9)) if pa[j] != pb[j]]
            return n, int(pa[0]), diff, len(a), len(b)
    return n, None, [], len(a), len(b)


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--exe", type=Path, required=True, help="netplay nectar.exe (the one that recorded, or the one under test)")
    p.add_argument("--log", type=Path, required=True, help="session-inputs.pknl")
    p.add_argument("--out", type=Path, required=True, help="private output dir (created)")
    p.add_argument("--src-run", type=Path, default=None, help="the recorded peer's run folder (default: the log's folder)")
    p.add_argument("--campaign-src", type=Path, default=None, help="pair mode: campaign folder holding checkpoint_gen")
    p.add_argument("--continue-from", type=Path, default=None, help="launcher mode: override the log's continue_from folder")
    p.add_argument("--assets", type=Path, default=DEFAULT_ASSETS, help="game data folder (junctioned read-only)")
    p.add_argument("--mode", choices=("auto", "pair", "launcher"), default="auto")
    p.add_argument("--port", type=int, default=49890, help="pair mode: unused by the replay, only names the host role")
    p.add_argument("--ticks", type=int, default=0, help="stop after N frames (default: the whole log)")
    p.add_argument("--dump-ticks", type=str, default="", help="comma list of hash ticks to dump objects for (replay-objects.txt)")
    p.add_argument("--compare-hashes", type=Path, default=None, help="a recorded hashes.txt to diff the replay's against")
    p.add_argument("--state-text", type=str, default=None, help="pair mode: state.txt line ({TOKEN}) instead of the default")
    p.add_argument("--timeout", type=float, default=1800)
    p.add_argument("--env", nargs="*", default=[], metavar="K=V")
    a = p.parse_args(argv)

    log_path = a.log.resolve()
    log = pknl.load(log_path)
    if not log.frames:
        print("replay_session: the log has no frames")
        return 2
    src = (a.src_run or log_path.parent).resolve()
    mode = a.mode
    if mode == "auto":
        mode = "launcher" if log.get("launcher") == "1" else "pair"
    out = a.out.resolve()
    out.mkdir(parents=True, exist_ok=True)
    exe = a.exe.resolve()
    exe_sha = sha256_file(exe)
    print(f"replay_session: log {log_path}: {len(log.frames)} frames "
          f"({log.frames[0]['frame']}..{log.frames[-1]['frame']}), role={log.get('role')} mode={mode} "
          f"checkpoint_gen={log.get('checkpoint_gen')} truncated={log.truncated}")
    print(f"replay_session: replaying with exe {exe_sha[:16]}... (the exe's own handshake hash is checked "
          f"by the replay itself against the recording)")
    seed = log.get("netplay_seed", "0")

    env_extra = {
        "PIKMIN_NETPLAY_REPLAY_LOG": str(log_path),
        "PIKMIN_NETPLAY_SEED": seed,
        "PIKMIN_NETPLAY_DELAY": "2",
    }
    if a.dump_ticks:
        env_extra["PIKMIN_NETPLAY_REPLAY_DUMP_TICKS"] = a.dump_ticks
    if a.ticks:
        env_extra["PIKMIN_NETPLAY_EXIT_AFTER_TICKS"] = str(a.ticks)
    env_extra.update(rp.parse_kv(a.env, "env"))

    stop = threading.Event()
    threads = []
    t0 = time.time()
    try:
        if mode == "pair":
            run = out / "host" / "run"
            run.mkdir(parents=True, exist_ok=True)
            (run / "save").mkdir(exist_ok=True)
            boot_src = src / "bootstrap.txt"
            if not boot_src.exists():
                print(f"replay_session: {boot_src} not found (--src-run)")
                return 2
            boot = run / "bootstrap.txt"
            shutil.copyfile(boot_src, boot)
            if (src / "pikmin_settings.conf").exists():
                shutil.copyfile(src / "pikmin_settings.conf", run / "pikmin_settings.conf")
            rp.link_assets(run, a.assets)
            gen = int(log.get("checkpoint_gen", "0") or 0)
            if gen > 0:
                if a.campaign_src is None:
                    print(f"replay_session: the session continued checkpoint {gen}; pass --campaign-src")
                    return 2
                copy_campaign(a.campaign_src.resolve(), out / "campaign", gen)
            token = read_session_token(boot)
            state = (a.state_text or "PIKMIN_STATE 5 {TOKEN} 1 0 127 0 0 END").replace("{TOKEN}", token or "") + "\n"
            th = threading.Thread(target=refresher, args=(run, state, stop))
            th.start()
            threads.append(th)
            hash_log = run / "hashes.txt"
            env_extra["PIKMIN_STATE_HASH_LOG"] = str(hash_log)
            native_log = run / "native.log"
            proc, child_out = rp.launch(exe, run, boot, ["--netplay-host", str(a.port)], env_extra, native_log,
                                        unthrottled=True)
            result_dir = run
        else:
            stage = out / "stage"
            stage.mkdir(parents=True, exist_ok=True)
            import launch_pair as lp
            staged = lp.stage_exe(exe, stage)
            cwd = out / "cwd"
            cwd.mkdir(parents=True, exist_ok=True)
            rp.link_assets(cwd, a.assets)
            settings = src / "settings-at-start.conf"
            if settings.exists():
                shutil.copyfile(settings, cwd / "pikmin_settings.conf")
            args = ["--netplay-host-ice", "--netplay-test-hidden"]
            if log.get("continued") == "1":
                cont = a.continue_from or Path(log.get("continue_from"))
                if not Path(cont).is_dir():
                    print(f"replay_session: the continued run folder {cont} is gone; pass --continue-from")
                    return 2
                args += ["--continue", str(cont)]
            else:
                bsrc = log.get("bootstrap_source", "")
                if bsrc and bsrc not in ("default", "offer bundle") and Path(bsrc).is_file():
                    args += ["--bootstrap", bsrc]
            hash_log = out / "hashes.txt"
            env_extra["PIKMIN_STATE_HASH_LOG"] = str(hash_log)
            env_extra["PIKMIN_NETPLAY_UNTHROTTLED"] = "1"
            native_log = out / "native.log"
            proc, child_out = lp.launch(staged, cwd, args, env_extra, native_log)
            result_dir = out
        print(f"replay_session: pid {proc.pid} started")
        try:
            rc = proc.wait(timeout=a.timeout)
        except subprocess.TimeoutExpired:
            print(f"replay_session: timeout after {a.timeout}s, killing pid {proc.pid}")
            proc.kill()
            try:
                proc.wait(timeout=30)
            except subprocess.TimeoutExpired:
                pass
            rc = 124
        child_out.close()
    finally:
        stop.set()
        for th in threads:
            th.join()
    secs = time.time() - t0

    text = Path(native_log).read_text(errors="replace") if Path(native_log).exists() else ""
    done = [ln for ln in text.splitlines() if "[netplay] replay:" in ln]
    for ln in done[-12:]:
        print("  " + ln.strip())
    ticks = sum(1 for ln in Path(hash_log).read_text(errors="replace").splitlines() if ln.strip()) if Path(hash_log).exists() else 0
    print(f"replay_session: exit={rc} ticks hashed={ticks}/{len(log.frames)} time={secs:.1f}s "
          f"({ticks / secs if secs > 0 else 0:.0f} ticks/s)")
    ok = rc == 0 and "[netplay] replay: done:" in text and "every recorded hash reproduced" in text
    if a.compare_hashes is not None and Path(hash_log).exists():
        n, first, cols, la, lb = compare_hash_logs(a.compare_hashes.resolve(), Path(hash_log))
        if first is None and la == lb:
            print(f"replay_session: hash log identical to {a.compare_hashes} ({n} ticks)")
        elif first is None:
            print(f"replay_session: hash logs agree for {n} ticks but differ in length (recorded {la}, replay {lb})")
            if a.ticks == 0:
                ok = False
        else:
            print(f"replay_session: hash log DIFFERS from {a.compare_hashes} at tick {first} (columns: {','.join(cols) or '?'})")
            ok = False
    print(f"STDOUT_LOG={native_log}")
    print(f"HASH_LOG={hash_log}")
    print("replay_session: " + ("PASS: every recorded hash reproduced" if ok else "FAIL"))
    if ok:
        return 0
    return rc if isinstance(rc, int) and rc != 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
