"""Scripted co-op pairs for issue #1028: captain 2's whistle and Onion.

Runs run_pair.py on the netplay exe with scripted inputs (gen_coop_input.py) on
Forest of Hope day 2 (the default profile) and checks the native.log lines the
game prints in co-op:

  whistle  the host (captain 1) disbands its squad at tick 420; the joiner
           (captain 2) walks to the freed Pikmin and holds B. Expect
           `[coop] gather navi=1` and `[coop] gather end navi=1 formation=N`
           with N >= 1 and every recruit counted under navi1 (navi0=0).
  onion    the host deposits Pikmin in the red Onion, the joiner opens the same
           Onion and takes 3 out. Expect `[coop] onion exit request navi=1
           count=3` and three `[coop] onion exit piki joins navi=1` lines
           (before the fix they joined navi=0).

Both also need run_pair's own verdict: identical hash logs on both peers.
The scripted positions were measured on this profile (captain start
(-483, 1966) / (-462, 1973), red Onion at (-378, 2156)), so a different
profile needs its own numbers.

Usage: coop_whistle_pair.py --exe nectar.exe --out DIR [--port 49700]
                            [--scenario whistle|onion|both]
"""
import argparse
import re
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
GEN = HERE / "gen_coop_input.py"
RUN_PAIR = HERE / "run_pair.py"


def gen(out, ticks, segs):
    cmd = [sys.executable, str(GEN), "--ticks", str(ticks), "--out", str(out)]
    for seg in segs:
        cmd += ["--seg", seg]
    subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL)


def tap_series(stick, n):
    """n single-click stick pulses (a held stick only counts once in the Onion menu)."""
    segs = []
    for _ in range(n):
        segs += [f"2:-:{stick}", "4:-:0:0"]
    return segs


# run_pair refuses a scripted input file shorter than --ticks + 50 records (#1028), so each
# generator below writes at least ticks + SCRIPT_MARGIN records. The last segment repeats
# (hands-off), so the extra tail does not change what the scenario does.
SCRIPT_MARGIN = 50
WHISTLE_TICKS = 800
ONION_TICKS = 1700


def whistle_inputs(out):
    gen(out / "host.pkni", 1200, ["420:-:0:0", "3:X:0:0", "777:-:0:0"])
    gen(out / "join.pkni", 1200, ["480:-:0:0", "17:-:-59:-80", "8:-:0:0", "40:B:0:0", "400:-:0:0"])
    return WHISTLE_TICKS


def onion_inputs(out):
    gen(out / "host.pkni", ONION_TICKS + SCRIPT_MARGIN,
        ["400:-:0:0", "37:-:40:-92", "20:-:0:0", "3:A:0:0", "140:-:0:0"] + tap_series("0:100", 6)
        + ["10:-:0:0", "3:A:0:0", "1000:-:0:0"])
    gen(out / "join.pkni", ONION_TICKS + SCRIPT_MARGIN,
        ["900:-:0:0", "36:-:33:-94", "40:-:0:0", "3:A:0:0", "140:-:0:0"] + tap_series("0:-100", 3)
        + ["10:-:0:0", "3:A:0:0", "700:-:0:0"])
    return ONION_TICKS


def run(name, exe, out, port, ticks):
    run_dir = out / name
    cmd = [sys.executable, str(RUN_PAIR), "--exe", str(exe), "--ticks", str(ticks), "--out", str(run_dir / "pair"),
           "--host-port", str(port), "--delay", "2", "--input-host", str(run_dir / "host.pkni"),
           "--input-join", str(run_dir / "join.pkni"), "--min-tuples", "50", "--timeout", "600"]
    r = subprocess.run(cmd, capture_output=True, text=True)
    (run_dir / "run_pair.log").write_text(r.stdout + r.stderr, encoding="utf-8")
    return r.returncode == 0 and "run_pair: PASS" in r.stdout, run_dir / "pair"


def peer_logs(pair):
    return {"host": pair / "host" / "run" / "native.log", "join": pair / "join" / "peer" / "run" / "native.log"}


def check_whistle(pair):
    problems = []
    for who, log in peer_logs(pair).items():
        text = log.read_text(encoding="utf-8", errors="replace")
        if "[coop] gather navi=1" not in text:
            problems.append(f"{who}: no '[coop] gather navi=1' (captain 2's whistle never entered Gather)")
        m = re.search(r"\[coop\] gather end navi=1 formation=(\d+) \(navi0=(\d+) navi1=(\d+)\)", text)
        if not m:
            problems.append(f"{who}: no '[coop] gather end navi=1' line")
        elif int(m.group(1)) < 1 or int(m.group(1)) != int(m.group(3)):
            problems.append(f"{who}: whistle recruited {m.group(1)} (navi1={m.group(3)}), expected >= 1")
        else:
            print(f"  {who}: captain 2's whistle recruited {m.group(1)} Pikmin into its own formation")
    return problems


def check_onion(pair):
    problems = []
    for who, log in peer_logs(pair).items():
        text = log.read_text(encoding="utf-8", errors="replace")
        req = re.findall(r"\[coop\] onion exit request navi=1 count=(\d+)", text)
        joins1 = len(re.findall(r"\[coop\] onion exit piki joins navi=1\b", text))
        joins0 = len(re.findall(r"\[coop\] onion exit piki joins navi=0\b", text))
        if not req:
            problems.append(f"{who}: captain 2 never requested an Onion exit")
        elif joins1 != sum(int(x) for x in req) or joins0:
            problems.append(f"{who}: asked {req}, {joins1} joined navi=1, {joins0} joined navi=0")
        else:
            print(f"  {who}: {joins1} Pikmin from captain 2's Onion request joined captain 2")
    return problems


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--exe", type=Path, required=True, help="netplay nectar.exe")
    p.add_argument("--out", type=Path, required=True, help="private output dir (must not hold earlier runs)")
    p.add_argument("--port", type=int, default=49700)
    p.add_argument("--scenario", choices=("whistle", "onion", "both"), default="both")
    a = p.parse_args(argv)
    scenarios = {"whistle": (whistle_inputs, check_whistle), "onion": (onion_inputs, check_onion)}
    names = list(scenarios) if a.scenario == "both" else [a.scenario]
    failed = False
    for i, name in enumerate(names):
        run_dir = a.out / name
        run_dir.mkdir(parents=True, exist_ok=False)
        make, check = scenarios[name]
        ticks = make(run_dir)
        print(f"coop_whistle_pair: {name} ({ticks} ticks)")
        ok, pair = run(name, a.exe.resolve(), a.out, a.port + 2 * i, ticks)
        problems = [] if ok else [f"run_pair did not PASS (see {run_dir / 'run_pair.log'})"]
        if ok:
            problems += check(pair)
        for line in problems:
            print("  FAIL:", line)
        failed |= bool(problems)
        print(f"coop_whistle_pair: {name} {'FAIL' if problems else 'PASS'}")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
