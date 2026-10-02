"""Single-process co-op policy fixture runner (netplay M4 D-policy, issue #885).

Boots one hidden, private, bounded game with --coop and
PIKMIN_RANDOMIZER_TEST_SCRIPT=coop-policy / PIKMIN_COOP_POLICY_CASE=<case>
(needs a -DPIKMIN_RANDOMIZER_TEST_HOOKS=ON build: the fixture, like the
existing `benefits` fixture, is compiled only into diagnostic builds).

The bootstrap is the schema-9 template from the M4d brief (CHECKSET 6,
BENEFITS 30, DEATHLINK 3). A refresher thread keeps state.txt current; the
fixture prints `TEST_ONLY coop_policy_phase case=<c> n=<k>` when it wants
phase k's grants, and the runner switches the state line.

Exit 0 only when the child exits 0 after printing
`TEST_ONLY coop_policy_pass case=<case>`. Only the spawned PID is signalled.
"""

import argparse
import hashlib
import os
import re
import subprocess
import sys
import threading
import time
import uuid
from pathlib import Path

try:
    import _winapi
except ImportError:  # non-Windows: junctions unavailable
    _winapi = None

DEFAULT_ASSETS = Path("C:/Users/alari/bbft/dist/cohesion/pikmin/assets")

BOOTSTRAP = (
    "PIKMIN_RANDOMIZER 9\nSESSION {TOKEN}\nFINGERPRINT {TOKEN}\nPROFILE {PROFILE}\n"
    "CATALOG gameplay-checks-v9\nPLACEMENT identity-v1\nGOAL 25\nDAYS repeat-day29-v1\n"
    "COLOR red\nCHECKSET 6\nENEMIES 0\nSTARTING_FLARLIC 2\nBENEFITS 30\nDEATHLINK 3\nEND\n"
)

BENEFIT_ORDER = ("delivery", "flowers", "heal", "whistle", "pluck",
                 "bombs", "bombtrap", "progg", "prerelease")


def state_line(token, deathlink=0, **benefits):
    """Schema-9 state line in parse_state_stream order (pc_randomizer.cpp)."""
    unknown = set(benefits) - set(BENEFIT_ORDER)
    if unknown:
        raise SystemExit(f"unknown benefit(s) {sorted(unknown)}")
    counts = " ".join(str(benefits.get(k, 0)) for k in BENEFIT_ORDER)
    return (f"PIKMIN_STATE 9 {token} 1 0 127 0 CHECKS 0 BENEFITS {counts} "
            f"DEATHLINK {deathlink} END\n")


# Per case: phase number -> state-line arguments. Phase 0 is the boot line.
# Grants are cumulative receipts, so later phases repeat earlier counts.
CASES = {
    "heal-p2-only": {0: dict(heal=1)},
    "heal-lowest": {0: dict(heal=3)},
    "heal-trigger": {0: dict(heal=2)},
    "heal-p1-down": {0: dict(heal=1)},
    "anchors": {0: dict(), 1: dict(bombtrap=3, flowers=2, progg=1, prerelease=1)},
    "any-alive": {0: dict(), 1: dict(delivery=1, flowers=1, bombtrap=1)},
    "deathlink-p1-down": {0: dict(deathlink=0), 1: dict(deathlink=1)},
}

SCRUB_PREFIXES = ("PIKMIN_NETPLAY_", "PIKMIN_INPUT_", "PIKMIN_STATE_HASH_LOG", "PIKMIN_COOP",
                  "PIKMIN_RANDOMIZER_TEST_")


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--exe", type=Path, required=True, help="TEST_HOOKS game executable")
    p.add_argument("--assets", type=Path, default=DEFAULT_ASSETS)
    p.add_argument("--out", type=Path, required=True, help="private output dir (run/ below)")
    p.add_argument("--case", required=True, choices=sorted(CASES))
    p.add_argument("--timeout", type=float, default=120)
    p.add_argument("--env", nargs="*", default=[], metavar="K=V")
    p.add_argument("--no-coop", action="store_true", help="diagnostic: boot without --coop")
    p.add_argument("--profile", default="foh-day2",
                   choices=("foh-day2", "navel-day2", "impact-day2", "spring-day2", "trial-day2"),
                   help="start profile; FoH has no Candypop/Geyser, so the anchors case only "
                        "requires a PRERELEASE grant on another profile")
    a = p.parse_args(argv)

    out = a.out.resolve()
    run = out / "run"
    run.mkdir(parents=True, exist_ok=True)
    token = uuid.uuid4().hex * 2
    boot = run / "bootstrap.txt"
    boot.write_text(BOOTSTRAP.replace("{TOKEN}", token).replace("{PROFILE}", a.profile))
    phases = {n: state_line(token, **kw) for n, kw in CASES[a.case].items()}
    (run / "states.txt").write_text("".join(f"{n} {line}" for n, line in sorted(phases.items())))

    link = run / "assets"
    if not link.exists():
        if _winapi is not None:
            _winapi.CreateJunction(str(a.assets.resolve()), str(link))
        else:
            os.symlink(str(a.assets.resolve()), str(link), target_is_directory=True)
    save_dir = run / "save"
    save_dir.mkdir(exist_ok=True)
    log = run / "native.log"

    current = {"phase": 0}
    done = threading.Event()

    def refresh():
        while not done.is_set():
            pending = run / "state.tmp"
            try:
                pending.write_text(phases[current["phase"]])
                os.replace(pending, run / "state.txt")
            except OSError:
                pass
            done.wait(0.1)

    env = {k: v for k, v in os.environ.items() if not k.startswith(SCRUB_PREFIXES)}
    env.update(
        PIKMIN_RANDOMIZER_TEST_BACKGROUND="1",
        SDL_AUDIODRIVER="dummy",
        NECTAR_SAVE_DIR=str(save_dir),
        PIKMIN_RANDOMIZER_TEST_SCRIPT="coop-policy",
        PIKMIN_COOP_POLICY_CASE=a.case,
        PIKMIN_COOP_POLICY_PRERELEASE="0" if a.profile == "foh-day2" else "1",
    )
    for item in a.env:
        key, _, value = item.partition("=")
        env[key.strip()] = value.strip()
    env.pop("BBFT_PORT", None)

    startup = None
    if sys.platform == "win32":
        startup = subprocess.STARTUPINFO()
        startup.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        startup.wShowWindow = 0
    cmd = [str(a.exe.resolve()), "--randomizer-seed", str(boot)] + ([] if a.no_coop else ["--coop"])
    phase_re = re.compile(r"TEST_ONLY coop_policy_phase case=(\S+) n=(\d+)")

    refresh_thread = threading.Thread(target=refresh)
    refresh_thread.start()
    start = time.time()
    rc = None
    try:
        with open(log, "w") as child_out:
            proc = subprocess.Popen(cmd, cwd=str(run), env=env, startupinfo=startup,
                                    stdout=child_out, stderr=subprocess.STDOUT)
            deadline = start + a.timeout
            while proc.poll() is None and time.time() < deadline:
                try:
                    text = log.read_text(errors="replace")
                except OSError:
                    text = ""
                for case, n in phase_re.findall(text):
                    n = int(n)
                    if case == a.case and n in phases and n > current["phase"]:
                        current["phase"] = n
                        print(f"coop_policy_native: phase {n} -> {phases[n].strip()}")
                time.sleep(0.05)
            if proc.poll() is None:
                proc.kill()  # only our own child PID
                try:
                    proc.wait(timeout=30)
                except subprocess.TimeoutExpired:
                    pass
                print(f"coop_policy_native: timeout after {a.timeout}s, killed pid {proc.pid}")
                rc = 124
            else:
                rc = proc.returncode
    finally:
        done.set()
        refresh_thread.join()
    secs = time.time() - start

    text = log.read_text(errors="replace") if log.exists() else ""
    lines = text.splitlines()
    keep = [ln for ln in lines if "START_STAGE" in ln or "TEST_ONLY" in ln or "[coop-policy]" in ln
            or "DEATHLINK_APPLIED" in ln or "BOMB_AMBUSH" in ln or "FLOWER_SHOWER" in ln
            or "PROGG_AMBUSH" in ln or "PRERELEASE_BEGIN" in ln or "PIKMIN_DELIVERY" in ln
            or "[NETPLAY] coop_active" in ln]
    for ln in keep:
        print(f"  {ln}")
    passed = rc == 0 and f"TEST_ONLY coop_policy_pass case={a.case}" in text
    has_stage = any("START_STAGE" in ln for ln in lines)
    print(f"coop_policy_native: case={a.case} exit={rc} time={secs:.1f}s start_stage={int(has_stage)} log={log}")
    exe_path = a.exe.resolve()
    print(f"coop_policy_native: exe={exe_path} sha256={hashlib.sha256(exe_path.read_bytes()).hexdigest()}")
    print(f"coop_policy_native: {'PASS' if passed and has_stage else 'FAIL'}")
    return 0 if passed and has_stage else 1


if __name__ == "__main__":
    raise SystemExit(main())
