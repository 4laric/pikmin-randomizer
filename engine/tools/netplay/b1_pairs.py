"""M4 lane B1 acceptance pairs with fixed, load-robust inputs (gapfix C, issue #885).

Thin wrapper over run_pair.py (imported, like coop_policy_pair.py). It writes
the inputs for one case into --out, runs run_pair.main, then checks the
case's acceptance criteria on both peers. Every other run_pair option passes
through unchanged (exe, ticks, port, delay, impairment, --env ...).

    b1_pairs.py --case dl-c1|dl-c2|hold --exe <np exe> --ticks 9000 --out DIR
                --host-port PORT [--delay 4 --latency-ms 100 --jitter-ms 20
                --loss-pct 5] [--root-mirror ROOT]

Cases:

dl-c1 / dl-c2  B1's DeathLink pairs. Bootstrap: B1's boot-dl-impact template
    (PROFILE impact-day2, DEATHLINK unit 1; a hands-off impact-day2 co-op
    start keeps its field Pikmin, unlike foh-day2). Inputs hands-off
    (--host-script-ticks 0 --join-script-ticks 0). The DeathLink steps are
    keyed to SIM FRAMES (run_pair `f<tick>` keys), not wall seconds:
    DEATHLINK 2 at tick 600, DEATHLINK 3 at tick 1200. Under load a
    wall-clock step (the old t=20 s / t=35 s) applied at frame ~206, before
    any Pikmin was on the field, so the unit was dropped (killed=0) and the
    pair failed although lockstep held. A frame key always lands after the
    field is populated, however slowly the machine runs.
    dl-c1 adds PIKMIN_NETPLAY_TEST_DEATHLINK_AS_ORDINARY=1 on both peers.
    Checks (per peer, both identical): exactly 3 `DEATHLINK_APPLIED
    killed=1`, the DeathLink randstate generations applied at frames >= 600
    and >= 1200; dl-c1: 3 `PIKMIN_DEATH ordinary`, 0 induced, host
    deaths.txt exactly 1,2,3, no joiner deaths.txt; dl-c2: 3 `PIKMIN_DEATH
    induced`, 0 ordinary, no deaths.txt on either peer. With --root-mirror
    it also runs check_mirror.py.

hold  B1's HOLD pair: --host-stale-window 60:25 --expect-hold 1
    --expect-held-ms 20000 --min-tuples 100. The property under test is
    that a synchronized HOLD longer than the 15 s disconnect timeout
    survives, and the brief's bar is held_ms >= 20000. B1 used a 60:23
    window, which by construction yields a nominal hold of exactly 20 s
    (23 s stale minus the 3 s link-freshness threshold) plus a few frames
    of detection and resume latency, so the bar sat on the nominal value
    and a sample passed or failed by milliseconds (the integration run's
    joiner: 20006 ms; a B1 round-0 run: 19978 ms). The window is widened to
    60:25 (nominal hold 22 s; frozen time costs no ticks, only wall time)
    so the unchanged 20000 ms bar has a 2 s margin.
    The bar is not lowered: it still proves a hold 5 s past the disconnect
    timeout.
"""

import argparse
import re
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import run_pair  # noqa: E402

BOOT_DL = (
    "PIKMIN_RANDOMIZER 9\nSESSION {TOKEN}\nFINGERPRINT {TOKEN}\nPROFILE impact-day2\n"
    "CATALOG gameplay-checks-v9\nPLACEMENT identity-v1\nGOAL 25\nDAYS repeat-day29-v1\n"
    "COLOR red\nCHECKSET 0\nENEMIES 0\nSTARTING_FLARLIC 10\nDEATHLINK 1\nEND\n"
)
DL_KEYS = (600, 1200)
STATES_DL = (
    "# b1_pairs dl-c1/dl-c2 (gapfix C, #885): DeathLink steps keyed to sim frames\n"
    "0 PIKMIN_STATE 9 {TOKEN} 1 0 127 0 CHECKS 0 DEATHLINK 0 END\n"
    f"f{DL_KEYS[0]} PIKMIN_STATE 9 {{TOKEN}} 1 0 127 0 CHECKS 0 DEATHLINK 2 END\n"
    f"f{DL_KEYS[1]} PIKMIN_STATE 9 {{TOKEN}} 1 0 127 0 CHECKS 0 DEATHLINK 3 END\n"
)
HOLD_ARGS = ["--host-stale-window", "60:25", "--expect-hold", "1", "--expect-held-ms", "20000",
             "--min-tuples", "100"]
APPLY_RE = re.compile(r"randstate gen=(\d+) applied at frame=(\d+)")


def lines(path, needle):
    try:
        return [ln.strip() for ln in Path(path).read_text(errors="replace").splitlines() if needle in ln]
    except OSError:
        return []


def deathlink_apply_frames(log):
    """Frames of the randstate applies that raised the DeathLink total. The
    apply prints `[Pikmin Randomizer] DEATHLINK_TOTAL <n>` while it runs and
    the session prints `randstate gen=<g> applied at frame=<F>` right after,
    so each total takes the frame of the next apply line."""
    frames, waiting = [], False
    try:
        text = Path(log).read_text(errors="replace").splitlines()
    except OSError:
        return frames
    for ln in text:
        if "[Pikmin Randomizer] DEATHLINK_TOTAL " in ln:
            waiting = True
            continue
        m = APPLY_RE.search(ln)
        if m and waiting:
            frames.append(int(m.group(2)))
            waiting = False
    if waiting:
        frames.append(None)
    return frames


def check_deathlink(case, host_run, join_run):
    errors = []
    seqs = {}
    for who, run in (("host", host_run), ("join", join_run)):
        log = run / "native.log"
        applied = lines(log, "DEATHLINK_APPLIED")
        ordinary = lines(log, "PIKMIN_DEATH ordinary")
        induced = lines(log, "PIKMIN_DEATH induced")
        killed1 = [ln for ln in applied if "DEATHLINK_APPLIED killed=1 " in ln]
        frames = deathlink_apply_frames(log)
        seqs[who] = [ln[ln.index("[Pikmin Randomizer]"):] for ln in
                     lines(log, "DEATHLINK_APPLIED") + lines(log, "DEATHLINK_TOTAL")]
        print(f"b1_pairs: {who}: DEATHLINK_APPLIED={len(applied)} (killed=1: {len(killed1)}) "
              f"ordinary={len(ordinary)} induced={len(induced)} deathlink_apply_frames={frames}")
        if len(applied) != 3 or len(killed1) != 3:
            errors.append(f"{who}: want exactly 3 DEATHLINK_APPLIED killed=1, got {applied}")
        if len(frames) != 2 or any(f is None for f in frames) or any(
                f < key for f, key in zip(frames, DL_KEYS)):
            errors.append(f"{who}: DeathLink applies {frames} not at frames >= {DL_KEYS}")
        want_ord, want_ind = (3, 0) if case == "dl-c1" else (0, 3)
        if len(ordinary) != want_ord or len(induced) != want_ind:
            errors.append(f"{who}: want {want_ord} ordinary / {want_ind} induced deaths, got "
                          f"{len(ordinary)} / {len(induced)}")
    if seqs["host"] != seqs["join"]:
        errors.append("DEATHLINK_APPLIED / DEATHLINK_TOTAL sequences differ between peers")
    host_deaths = host_run / "deaths.txt"
    join_deaths = join_run / "deaths.txt"
    if join_deaths.exists():
        errors.append("the joiner wrote deaths.txt (journals are host-only)")
    if case == "dl-c1":
        got = host_deaths.read_text().split() if host_deaths.exists() else None
        print(f"b1_pairs: host deaths.txt={got}")
        if got != ["1", "2", "3"]:
            errors.append(f"host deaths.txt is {got}, want exactly 1,2,3")
    elif host_deaths.exists():
        errors.append(f"host deaths.txt exists in dl-c2: {host_deaths.read_text().split()}")
    return errors


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    pre = argparse.ArgumentParser(add_help=False)
    pre.add_argument("--case", choices=("dl-c1", "dl-c2", "hold"))
    pre.add_argument("--out", type=Path)
    pre.add_argument("--root-mirror", type=Path, default=None)
    pre.add_argument("--run-name", default="run")
    mine, rest = pre.parse_known_args(argv)
    if "-h" in argv or "--help" in argv:
        print(__doc__)
        return 0
    if mine.case is None or mine.out is None:
        print("b1_pairs: --case and --out are required")
        return 2
    out = mine.out.resolve()
    out.mkdir(parents=True, exist_ok=True)
    pass_argv = [x for x in argv]
    # Drop our own options before handing the rest to run_pair.
    for opt in ("--case", "--root-mirror"):
        while opt in pass_argv:
            i = pass_argv.index(opt)
            del pass_argv[i:i + 2]
    if mine.case in ("dl-c1", "dl-c2"):
        boot = out / "boot-dl-impact.txt"
        states = out / "states-dl-frames.txt"
        boot.write_text(BOOT_DL)
        states.write_text(STATES_DL)
        pass_argv += ["--bootstrap-template", str(boot), "--host-state-script", str(states),
                      "--join-state-script", str(states), "--host-script-ticks", "0",
                      "--join-script-ticks", "0", "--min-tuples", "100"]
        if mine.case == "dl-c1":
            item = "PIKMIN_NETPLAY_TEST_DEATHLINK_AS_ORDINARY=1"
            if "--env" in pass_argv:
                pass_argv.insert(pass_argv.index("--env") + 1, item)
            else:
                pass_argv += ["--env", item]
    else:
        pass_argv += HOLD_ARGS
    print(f"b1_pairs: case={mine.case} run_pair argv: {' '.join(pass_argv)}")
    rc = run_pair.main(pass_argv)
    ok = rc == 0
    print(f"b1_pairs: run_pair exit={rc}")
    host_run = out / "host" / mine.run_name
    join_run = out / "join" / "peer" / mine.run_name
    if mine.case in ("dl-c1", "dl-c2"):
        errors = check_deathlink(mine.case, host_run, join_run)
        for err in errors:
            print(f"b1_pairs: FAIL: {err}")
        ok = ok and not errors
        if mine.root_mirror is not None:
            r = subprocess.run([sys.executable, str(HERE / "check_mirror.py"), "--host-run", str(host_run),
                                "--join-run", str(join_run), "--root-mirror", str(mine.root_mirror)],
                               capture_output=True, text=True)
            for ln in (r.stdout + r.stderr).strip().splitlines():
                print(f"b1_pairs: {ln}")
            print(f"b1_pairs: check_mirror exit={r.returncode}")
            ok = ok and r.returncode == 0
    print(f"b1_pairs: {'PASS' if ok else 'FAIL'}")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
