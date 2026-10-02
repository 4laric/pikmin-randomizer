"""Hidden, private, bounded replay launcher for the netplay harness.

Runs one fresh game process that replays a PKNI input file while writing a
per-tick state-hash log, then exits via PIKMIN_NETPLAY_EXIT_AFTER_TICKS.

Bootstrap follows tools/run_campaign_resume.py's non-campaign path:
junctioned read-only assets, a state.txt refresher thread, the game run with
the run dir as cwd (settings are read relative to cwd, so the user's
settings are never touched), NECTAR_SAVE_DIR pointed at a private dir,
PIKMIN_RANDOMIZER_TEST_BACKGROUND=1 and SDL_AUDIODRIVER=dummy.

Only the spawned PID is ever signalled. Nothing outside the run dir and the
private save dir is written.
"""

import argparse
import hashlib
import os
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


def refresh_loop(run, state_text, done, errors, replace=None, period=0.1):
    """Keep run/state.txt fresh (rewritten every `period` s) until `done`.

    Gapfix C (issue #885): os.replace can raise PermissionError [WinError 5]
    while the game holds state.txt open for its poll, and write_text can meet
    a transient AV / delete-pending lock. An uncaught error used to kill the
    refresher thread; the legacy poll then saw a stale state.txt and paused
    the sim until the run timed out. Every OSError (PermissionError is one)
    is now counted in errors["n"] / errors["last"] and retried on the next
    turn, as in coop_policy_native.py and run_pair.py, so the loop never
    dies. `replace` is injectable for tools/netplay/selftest.py.
    """
    replace = os.replace if replace is None else replace
    while not done.is_set():
        pending = run / "state.tmp"
        try:
            pending.write_text(state_text)
            replace(pending, run / "state.txt")
        except OSError as exc:
            errors["n"] += 1
            errors["last"] = f"{type(exc).__name__}: {exc}"
        done.wait(period)


def parse_kv(items, what):
    out = {}
    for item in items or []:
        if "=" not in item:
            raise SystemExit(f"--{what} needs key=value, got {item!r}")
        key, value = item.split("=", 1)
        out[key.strip()] = value.strip()
    return out


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--exe", type=Path, required=True, help="game executable")
    p.add_argument("--replay", type=Path, required=True, help="PKNI input file")
    p.add_argument("--ticks", type=int, required=True)
    p.add_argument("--out", type=Path, required=True, help="private run dir")
    p.add_argument("--assets", type=Path, default=DEFAULT_ASSETS)
    p.add_argument(
        "--config-overrides",
        nargs="*",
        default=[],
        metavar="key=value",
        help="written into a private pikmin_settings.conf in the run dir",
    )
    p.add_argument("--preroll-rand", type=int, default=0)
    p.add_argument("--timeout", type=float, default=600)
    p.add_argument("--env", nargs="*", default=[], metavar="K=V")
    p.add_argument("--record", type=Path, default=None,
                   help="also record inputs while replaying (identity check: must equal --replay)")
    p.add_argument("--profile", default="foh-day2")
    p.add_argument("--exe-args", nargs="*", default=[])
    p.add_argument("--bootstrap-template", type=Path, default=None,
                   help="M4d: bootstrap file to use instead of the built-in schema-5 one "
                        "({TOKEN} = run token)")
    p.add_argument("--state-line", default=None,
                   help="M4d: state.txt line to refresh instead of the built-in schema-5 one "
                        "({TOKEN} = run token)")
    a = p.parse_args(argv)

    run = a.out.resolve()
    run.mkdir(parents=True, exist_ok=True)

    token = uuid.uuid4().hex * 2
    boot = run / "bootstrap.txt"
    if a.bootstrap_template is not None:
        boot.write_text(a.bootstrap_template.read_text().replace("{TOKEN}", token))
    else:
        boot.write_text(
            f"PIKMIN_RANDOMIZER 5\nSESSION {token}\nFINGERPRINT {token}\n"
            f"PROFILE {a.profile}\nCATALOG gameplay-checks-v5\nPLACEMENT identity-v1\n"
            f"GOAL 25\nDAYS repeat-day29-v1\nCOLOR red\nSTARTING_FLARLIC 10\nEND\n"
        )
    if a.state_line is not None:
        state_text = a.state_line.replace("{TOKEN}", token).strip() + "\n"
    else:
        state_text = f"PIKMIN_STATE 5 {token} 1 0 127 0 0 END\n"

    assets_link = run / "assets"
    if not assets_link.exists():
        if _winapi is not None:
            _winapi.CreateJunction(str(a.assets.resolve()), str(assets_link))
        else:
            os.symlink(str(a.assets.resolve()), str(assets_link), target_is_directory=True)

    overrides = parse_kv(a.config_overrides, "config-overrides")
    if overrides:
        with open(run / "pikmin_settings.conf", "w") as f:
            for key, value in sorted(overrides.items()):
                f.write(f"{key} = {value}\n")

    save_dir = run / "save"
    save_dir.mkdir(exist_ok=True)

    hash_log = run / "hashes.txt"
    stdout_log = run / "native.log"

    done = threading.Event()
    refresh_errors = {"n": 0, "last": ""}
    thread = threading.Thread(target=refresh_loop, args=(run, state_text, done, refresh_errors))
    thread.start()

    env = dict(os.environ)
    # A stray PIKMIN_* netplay switch in the caller's environment must never
    # leak into the run; the scratch idle_default.py scrubs these and so do we.
    for key in (
        "PIKMIN_INPUT_RECORD",
        "PIKMIN_INPUT_REPLAY",
        "PIKMIN_STATE_HASH_LOG",
        "PIKMIN_NETPLAY_EXIT_AFTER_TICKS",
        "PIKMIN_NETPLAY_TEST_PREROLL_RAND",
        "PIKMIN_NETPLAY_DETERMINISTIC",
        "PIKMIN_NETPLAY_UNTHROTTLED",
        "PIKMIN_NETPLAY_TEST_CAMERA_WOBBLE",
        "PIKMIN_NETPLAY_DEBUG_NAVI_POS",
    ):
        env.pop(key, None)
    # #965 lane H: also drop every other PIKMIN_NETPLAY_* / PIKMIN_INPUT_* name
    # (a `$env:` knob left set in the caller's PowerShell window); the run sets
    # what it needs below and takes test knobs through --env.
    for key in [k for k in env if k.upper().startswith(("PIKMIN_NETPLAY_", "PIKMIN_INPUT_"))]:
        del env[key]
    env.update(
        PIKMIN_RANDOMIZER_TEST_BACKGROUND="1",
        SDL_AUDIODRIVER="dummy",
        PIKMIN_NETPLAY_DETERMINISTIC="1",
        PIKMIN_NETPLAY_UNTHROTTLED="1",
        PIKMIN_STATE_HASH_LOG=str(hash_log),
        PIKMIN_INPUT_REPLAY=str(a.replay.resolve()),
        PIKMIN_NETPLAY_EXIT_AFTER_TICKS=str(a.ticks),
        NECTAR_SAVE_DIR=str(save_dir),
    )
    if a.record is not None:
        env["PIKMIN_INPUT_RECORD"] = str(a.record.resolve())
    if a.preroll_rand:
        env["PIKMIN_NETPLAY_TEST_PREROLL_RAND"] = str(a.preroll_rand)
    env.update(parse_kv(a.env, "env"))
    env.pop("BBFT_PORT", None)

    cmd = [str(a.exe.resolve()), "--randomizer-seed", str(boot)] + list(a.exe_args)
    startup = None
    if sys.platform == "win32":
        startup = subprocess.STARTUPINFO()
        startup.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        startup.wShowWindow = 0

    start = time.time()
    rc = 1
    with open(stdout_log, "w") as child_out:
        proc = subprocess.Popen(
            cmd, cwd=str(run), env=env, startupinfo=startup,
            stdout=child_out, stderr=subprocess.STDOUT,
        )
        try:
            rc = proc.wait(timeout=a.timeout)
        except subprocess.TimeoutExpired:
            # Only our own child PID is ever signalled.
            proc.kill()
            try:
                rc = proc.wait(timeout=30)
            except subprocess.TimeoutExpired:
                rc = 124
            print(f"run_replay: timeout after {a.timeout}s, killed pid {proc.pid}")
        finally:
            done.set()
            thread.join()
    secs = time.time() - start

    nlines = 0
    if hash_log.exists():
        with open(hash_log, "r", errors="replace") as f:
            nlines = sum(1 for line in f if line.strip())
    tps = (nlines / secs) if secs > 0 else 0.0
    print(f"run_replay: exit={rc} ticks={nlines}/{a.ticks} time={secs:.1f}s tps={tps:.1f}")
    print(f"run_replay: refresher retried errors={refresh_errors['n']}"
          + (f" last={refresh_errors['last']}" if refresh_errors["n"] else ""))
    exe_path = a.exe.resolve()
    print(f"run_replay: exe={exe_path} sha256={hashlib.sha256(exe_path.read_bytes()).hexdigest()}")
    print(f"STDOUT_LOG={stdout_log}")
    print(f"HASH_LOG={hash_log}")
    # A replay run only counts when the child proves it replayed: the
    # stdout log must show the replay load line and the hash log must hold
    # exactly --ticks lines. Otherwise a silent fallback to live input
    # would look like a success.
    ok = True
    try:
        text = stdout_log.read_text(errors="replace")
    except OSError:
        text = ""
    if "[netplay] input replay:" not in text:
        print("run_replay: FAIL: replay did not load (no '[netplay] input replay:' line)")
        ok = False
    if nlines != a.ticks:
        print(f"run_replay: FAIL: hash lines {nlines} != requested {a.ticks}")
        ok = False
    if isinstance(rc, int) and rc != 0:
        ok = False
    if not ok:
        return 1 if (isinstance(rc, int) and rc == 0) else (rc if isinstance(rc, int) else 1)
    return rc if isinstance(rc, int) else 1


if __name__ == "__main__":
    raise SystemExit(main())
