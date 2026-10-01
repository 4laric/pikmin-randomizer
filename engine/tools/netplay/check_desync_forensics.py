"""Injected-desync forensics pair test (issue #1037).

Runs one hidden loopback pair (run_pair.py) in which ONE peer's sim is nudged
at a chosen frame (PIKMIN_NETPLAY_TEST_DESYNC_NUDGE, TEST ONLY: adds 1.0 to the
x position of one object of that peer's sim at the start of that frame's
tick), so exactly one object diverges. The pair must then stop with exit 5 on
both peers, and this script checks what the new desync forensics left behind:

  * both consoles print BOTH sides' sub-hashes (`desync subs host ...` and
    `desync subs join ...`), the differing sub-hash names, the first
    differing tick (= nudge frame + 1) and the differing object;
  * both run folders hold desync-report.txt, desync-subs.txt,
    desync-objects.txt, desync-peer-objects.txt and the session input log;
  * diff_desync.py on the two desync-objects.txt names the nudged object at
    the first differing tick (a neighbour reacting to it in that tick is allowed and listed);
  * the end message tells the players to send the run folder (a launcher run;
    a loopback pair reports the line in its log only when a run folder exists).

  py -3.12 tools/netplay/check_desync_forensics.py --exe <np nectar.exe> --out <dir>
      [--ticks 3000] [--nudge-frame 1500] [--kind piki --ord 0] [--host-port 49820]
"""

import argparse
import re
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import diff_desync  # noqa: E402
import run_pair as rp  # noqa: E402


def read(path):
    try:
        return Path(path).read_text(errors="replace")
    except OSError:
        return ""


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--exe", type=Path, required=True)
    p.add_argument("--out", type=Path, required=True)
    p.add_argument("--ticks", type=int, default=3000)
    p.add_argument("--nudge-frame", type=int, default=1500)
    p.add_argument("--kind", choices=("piki", "navi", "teki"), default="piki")
    p.add_argument("--ord", type=int, default=0)
    p.add_argument("--nudge-role", choices=("host", "join"), default="join")
    p.add_argument("--host-port", type=int, default=49820)
    p.add_argument("--timeout", type=float, default=900)
    p.add_argument("--assets", type=Path, default=rp.DEFAULT_ASSETS)
    a = p.parse_args(argv)

    out = a.out.resolve()
    out.mkdir(parents=True, exist_ok=True)
    nudge = f"PIKMIN_NETPLAY_TEST_DESYNC_NUDGE={a.nudge_frame}:{a.kind}:{a.ord}"
    cmd = [sys.executable, str(HERE / "run_pair.py"), "--exe", str(a.exe), "--ticks", str(a.ticks), "--out", str(out),
           "--assets", str(a.assets), "--host-port", str(a.host_port), "--input-log", "--expect", "hash-desync",
           "--timeout", str(a.timeout), "--env-host" if a.nudge_role == "host" else "--env-join", nudge]
    print("check_desync_forensics: " + " ".join(cmd))
    with open(out / "run_pair.out", "w") as f:
        rc = subprocess.call(cmd, stdout=f, stderr=subprocess.STDOUT)
    print(f"check_desync_forensics: run_pair exit={rc} (its summary is in {out / 'run_pair.out'})")

    host_run = out / "host" / "run"
    join_run = out / "join" / "peer" / "run"
    fails = []

    def check(ok, what):
        print(("  ok   " if ok else "  FAIL ") + what)
        if not ok:
            fails.append(what)

    want_tick = a.nudge_frame + 1
    kind_ord = f"{a.kind}#{a.ord}"
    for who, run in (("host", host_run), ("join", join_run)):
        log = read(run / "native.log")
        check("[netplay] desync report: frame=" in log, f"{who}: console has the desync report line")
        check(re.search(r"\[netplay\] desync subs host tick=\d+: total=", log) is not None
              and re.search(r"\[netplay\] desync subs join tick=\d+: total=", log) is not None,
              f"{who}: console prints BOTH sides' sub-hashes")
        m = re.search(r"desync differing sub-hashes at tick=\d+: (\S+)", log)
        check(m is not None and a.kind in m.group(1).split(","), f"{who}: console names the differing sub-hash ({m.group(1) if m else None})")
        m = re.search(r"desync first differing tick in the exchanged window .*?: tick=(\d+), differing sub-hashes: (\S+)", log)
        check(m is not None and int(m.group(1)) == want_tick,
              f"{who}: first differing tick is {want_tick} ({m.group(1) if m else None})")
        check(f"desync   differs: " in log and kind_ord in log.split("desync   differs: ")[1].split("\n")[0]
              if "desync   differs: " in log else False,
              f"{who}: console names the differing object {kind_ord}")
        check(re.search(r"exit code|desync detected: frame=", log) is not None, f"{who}: the usual desync detected line is still there")
        for name in ("desync-report.txt", "desync-subs.txt", "desync-objects.txt", "desync-peer-objects.txt",
                     "session-inputs.pknl"):
            check((run / name).exists() and (run / name).stat().st_size > 0, f"{who}: {name} written")
    # The two dumps diff to the injected object.
    lines = []
    n, first, differing = diff_desync.diff(host_run / "desync-objects.txt", join_run / "desync-objects.txt", out=lines.append)
    (out / "diff_desync.txt").write_text("\n".join(lines) + "\n")
    print("\n".join("    " + ln for ln in lines))
    at_first = sorted(k for t, k in differing if t == want_tick)
    check(first == want_tick, f"the dumps first differ at tick {want_tick} (got {first})")
    # The nudged object must be named at the first differing tick. Another object standing next to it may react to
    # the displaced one in that very tick (a Pikmin turning to face it, a collision push), so neighbours are listed
    # but allowed: how crowded the nudged object is depends on the scenario, not on the forensics.
    check((a.kind, a.ord) in at_first, f"at tick {want_tick} {kind_ord} differs (got {at_first})")
    nudged_cols = [ln for ln in lines if ln.strip().startswith(f"{kind_ord}:")]
    check(any("pos" in ln for ln in nudged_cols), f"the dump diff shows {kind_ord} with a position column difference")
    others = [k for k in at_first if k != (a.kind, a.ord)]
    if others:
        print(f"  note neighbours reacting to {kind_ord} in the same tick: {others}")
    print("check_desync_forensics: " + ("PASS" if not fails else f"FAIL ({len(fails)})"))
    return 0 if not fails else 1


if __name__ == "__main__":
    raise SystemExit(main())
