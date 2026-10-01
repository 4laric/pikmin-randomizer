"""Co-op policy under lockstep (netplay M4 D-policy, issue #885).

Thin wrapper over run_pair.py (imported from this folder, not edited): it
swaps run_pair.write_bootstrap for the schema-9 M4d template (CHECKSET 6,
BENEFITS 30, DEATHLINK 3), runs run_pair.main(argv), then checks the policy
decisions on both peers:

* both peers' `[coop-policy]` lines are identical, in order (they are sim
  decisions, so a difference is a desync the hash may not see yet);
* both peers logged identical `[coop-policy] TEST event` lines when
  PIKMIN_NETPLAY_TEST_COOP_EVENTS is passed (gapfix C also folds the file
  into the handshake config hash, so a mismatched file is refused before
  the session starts; this stays as a second guard);
* gameplay proof: START_STAGE and `[Pikmin Randomizer]` lines on both peers,
  and the distinct (navi, piki, teki, item) hash tuples.

Always: the ANCHOR lines replay the round-robin cursor strictly (see
check_anchors); any grant off the cursor without a logged ANCHOR_SKIP fails.
With --acceptance it also requires a `HEAL captain=2`, at least one
round-robin hand-over between two grants of one kind logged while both
captains were live (`live=11`, no fallback), and a `DEATHLINK killed=3 p1=0`
line.

Gapfix C (issue #885): acceptance steps are keyed to sim frames, not wall
time. Under load a wall-clock DeathLink landed at frame 242, before the
scripted `1000 DOWN 1`, and the run failed. So:
* --acceptance without --host-state-script uses the built-in schedule
  ACCEPTANCE_STATES (run_pair `f<tick>` keys: heal 1 and four Flower
  Showers at tick 300, the DeathLink at tick 1200, after the tick-1000 down
  of P1, then a bomb trap and a fifth shower at tick 1800), written to
  <out>/acceptance-states.txt and passed to both peers; without
  PIKMIN_NETPLAY_TEST_COOP_EVENTS it also writes and passes
  ACCEPTANCE_EVENTS (`40 HP 2 0.5`, `1000 DOWN 1`);
* --acceptance with a user schedule refuses (before launching) any entry
  that raises DEATHLINK on a wall-clock key;
* --acceptance without --profile runs on impact-day2 (ACCEPTANCE_PROFILE).
  The assertions are about policy decisions, not terrain: on foh-day2 the
  slopes around the landing site make the 50-unit Flower Shower ring fail
  at random along the scripted random walk (a gapfix C run logged
  `ANCHOR_SKIP ... why=ring-height` for P1 twice, so no both-live hand-over
  happened before the tick-1000 down), and B1 measured that a foh-day2 co-op
  start loses most of its field Pikmin within ~60 s, which starves the
  DeathLink. impact-day2 keeps both captains on flat ground and the squad
  alive. Hands-off inputs are not an option: the first-nectar tutorial
  (tu_tx29) is a modal window that only an input dismisses, and while it is
  up the randomizer tick (and so the DeathLink) never runs.

Gapfix C (issue #885) HOLD check, always on: for every synchronized HOLD in
a peer's log, no grant or policy decision may appear between its
`[netplay] held at frame=` and `[netplay] resume at frame=` lines (the sim
is frozen there; a grant would mean the co-op branch ran while held). The
policy lines before and after each hold are counted and printed.

All run_pair.py options pass through unchanged (see run_pair.py --help).
"""

import argparse
import hashlib
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import run_pair  # noqa: E402

TEMPLATE = (
    "PIKMIN_RANDOMIZER 9\nSESSION {TOKEN}\nFINGERPRINT {TOKEN}\nPROFILE {PROFILE}\n"
    "CATALOG gameplay-checks-v9\nPLACEMENT identity-v1\nGOAL 25\nDAYS repeat-day29-v1\n"
    "COLOR red\nCHECKSET 6\nENEMIES 0\nSTARTING_FLARLIC 2\nBENEFITS 30\nDEATHLINK 3\nEND\n"
)


# Gapfix C: the frame-keyed acceptance inputs (see the module docstring).
# BENEFITS order: delivery flowers heal whistle pluck bombs bombtrap progg prerelease.
ACCEPTANCE_STATES = (
    "# coop_policy_pair --acceptance built-in schedule (gapfix C, #885): sim-frame keyed\n"
    "0 PIKMIN_STATE 9 {TOKEN} 1 0 127 0 CHECKS 0 BENEFITS 0 0 0 0 0 0 0 0 0 DEATHLINK 0 END\n"
    "f300 PIKMIN_STATE 9 {TOKEN} 1 0 127 0 CHECKS 0 BENEFITS 0 4 1 0 0 0 0 0 0 DEATHLINK 0 END\n"
    "f1200 PIKMIN_STATE 9 {TOKEN} 1 0 127 0 CHECKS 0 BENEFITS 0 4 1 0 0 0 0 0 0 DEATHLINK 1 END\n"
    "f1800 PIKMIN_STATE 9 {TOKEN} 1 0 127 0 CHECKS 0 BENEFITS 0 5 1 0 0 0 1 0 0 DEATHLINK 1 END\n"
)
ACCEPTANCE_EVENTS = "# P2 hurt early, P1 knocked down at co-op tick 1000\n40 HP 2 0.5\n1000 DOWN 1\n"
ACCEPTANCE_PROFILE = "impact-day2"
DEATHLINK_RE = re.compile(r"\bDEATHLINK (\d+)\b")


def wall_clock_deathlink_steps(path):
    """Entries of a state script that raise DEATHLINK on a wall-clock key:
    [(index, key, old, new)]. Empty when every rise is frame keyed."""
    sched = run_pair.load_state_script(path, "0" * 64)
    bad, prev = [], None
    for i, (kind, value, line) in enumerate(sched):
        m = DEATHLINK_RE.search(line)
        cur = int(m.group(1)) if m else 0
        if prev is not None and cur > prev and kind != "f":
            bad.append((i, f"{value:g}s", prev, cur))
        prev = cur
    return bad


def acceptance_argv(argv, out, env_items):
    """--acceptance defaults (gapfix C): the built-in frame-keyed schedule
    and events file when the caller passed none. Returns the new argv."""
    argv = list(argv)
    out.mkdir(parents=True, exist_ok=True)
    if "--profile" not in argv:
        argv += ["--profile", ACCEPTANCE_PROFILE]
        print(f"coop_policy_pair: acceptance: profile {ACCEPTANCE_PROFILE} (flat landing site, squad survives)")
    if "--host-state-script" not in argv:
        states = out / "acceptance-states.txt"
        states.write_text(ACCEPTANCE_STATES)
        argv += ["--host-state-script", str(states)]
        if "--join-state-script" not in argv:
            argv += ["--join-state-script", str(states)]
        print(f"coop_policy_pair: acceptance: built-in frame-keyed schedule {states}")
    if not any(item.startswith("PIKMIN_NETPLAY_TEST_COOP_EVENTS=") for item in env_items):
        events = out / "acceptance-events.txt"
        events.write_text(ACCEPTANCE_EVENTS)
        item = f"PIKMIN_NETPLAY_TEST_COOP_EVENTS={events}"
        if "--env" in argv:
            argv.insert(argv.index("--env") + 1, item)
        else:
            argv += ["--env", item]
        print(f"coop_policy_pair: acceptance: built-in events {events}")
    return argv


def write_bootstrap_m4d(path, token, profile, flarlic=10):
    # STARTING_FLARLIC is fixed at 2 by the template (flarlic is ignored).
    Path(path).write_text(TEMPLATE.replace("{TOKEN}", token).replace("{PROFILE}", profile))


def policy_lines(log):
    try:
        text = Path(log).read_text(errors="replace")
    except OSError:
        return []
    return [ln[ln.index("[coop-policy]"):].strip() for ln in text.splitlines() if "[coop-policy]" in ln]


def grep_count(log, needle):
    try:
        return sum(1 for ln in Path(log).read_text(errors="replace").splitlines() if needle in ln)
    except OSError:
        return 0


def distinct_tuples(hashes):
    seen = set()
    try:
        for ln in Path(hashes).read_text(errors="replace").splitlines():
            cols = ln.split()
            if len(cols) >= 6:
                seen.add(tuple(cols[2:6]))
    except OSError:
        pass
    return len(seen)


ANCHOR_RE = re.compile(r"\[coop-policy\] ANCHOR kind=(\S+) captain=(\d) next=(\d) live=([01])([01])")
SKIP_RE = re.compile(r"\[coop-policy\] ANCHOR_SKIP kind=(\S+) captain=(\d) reason=(\S+)")


def check_anchors(lines):
    """Strict round-robin check over one peer's [coop-policy] lines.

    Replays the cursor: every kind starts on captain 1 (and again after a
    `RESET` line). Each ANCHOR grant must land on the cursor captain, unless
    an ANCHOR_SKIP for that captain was logged right before it (then it is a
    fallback, marked `*`). The skip reason must agree with the grant's live
    flags, the grant must go to a live captain, and `next=` must be the other
    captain. A round-robin hand-over is two consecutive grants of one kind,
    both logged with `live=11`, the second on the cursor (not a fallback).

    Returns (errors, sequences per kind, hand-overs per kind)."""
    expected, skips, last = {}, {}, {}
    errors, seqs, handovers = [], {}, {}
    for ln in lines:
        if ln.startswith("[coop-policy] RESET "):
            expected.clear()
            skips.clear()
            last.clear()
            for kind in seqs:
                seqs[kind].append("|")
            continue
        m = SKIP_RE.match(ln)
        if m:
            skips.setdefault(m.group(1), []).append((int(m.group(2)), m.group(3)))
            continue
        m = ANCHOR_RE.match(ln)
        if not m:
            if "] ANCHOR " in ln:
                errors.append(f"unparsed ANCHOR line: {ln}")
            continue
        kind, cap, nxt = m.group(1), int(m.group(2)), int(m.group(3))
        live = (m.group(4) == "1", m.group(5) == "1")
        cursor = expected.get(kind, 1)
        skipped = skips.pop(kind, [])
        fallback = cap != cursor
        if fallback and cursor not in [c for c, _ in skipped]:
            errors.append(f"{kind}: grant on captain {cap} but the cursor was {cursor} and no ANCHOR_SKIP for {cursor}: {ln}")
        if not fallback and skipped:
            errors.append(f"{kind}: ANCHOR_SKIP logged for a grant on the cursor captain: {ln}")
        for c, reason in skipped:
            if c == cap:
                errors.append(f"{kind}: captain {c} skipped and granted in one attempt: {ln}")
            if reason == "not-live" and live[c - 1]:
                errors.append(f"{kind}: captain {c} skipped as not-live but live={m.group(4)}{m.group(5)}: {ln}")
            if reason == "placement" and not live[c - 1]:
                errors.append(f"{kind}: captain {c} placement skip while not live: {ln}")
        if not live[cap - 1]:
            errors.append(f"{kind}: grant on a captain that is not live: {ln}")
        if nxt != 3 - cap:
            errors.append(f"{kind}: next={nxt} is not the captain after {cap}: {ln}")
        prev = last.get(kind)
        if prev and prev[1] == (True, True) and live == (True, True) and not fallback and prev[0] != cap:
            handovers[kind] = handovers.get(kind, 0) + 1
        last[kind] = (cap, live)
        expected[kind] = nxt
        seqs.setdefault(kind, []).append(f"{cap}{'*' if fallback else ''}")
    return errors, {k: ",".join(v) for k, v in seqs.items()}, handovers


GRANT_NEEDLES = ("[coop-policy]", "BENEFIT_USED", "FLOWER_SHOWER", "BOMB_AMBUSH", "PROGG_AMBUSH",
                 "BOMB_DELIVERY", "PIKMIN_DELIVERY", "DEATHLINK_APPLIED", "PRERELEASE_BEGIN")


def hold_windows(log):
    """Per synchronized HOLD in one native log: (held line, resume line,
    grant lines before the held line, grant lines between held and resume,
    grant lines after the resume line)."""
    try:
        text = Path(log).read_text(errors="replace").splitlines()
    except OSError:
        return []
    grants = [(i, ln.strip()) for i, ln in enumerate(text) if any(n in ln for n in GRANT_NEEDLES)]
    helds = [i for i, ln in enumerate(text) if "[netplay] held at frame=" in ln]
    resumes = [i for i, ln in enumerate(text) if "[netplay] resume at frame=" in ln]
    out = []
    for h, r in zip(helds, resumes):
        before = [g for i, g in grants if i < h]
        during = [g for i, g in grants if h < i < r]
        after = [g for i, g in grants if i > r]
        out.append((text[h].strip(), text[r].strip(), before, during, after))
    return out


def exe_identity(argv):
    """`path sha256` of the --exe argument, so the log ties the run to a build."""
    pre = argparse.ArgumentParser(add_help=False)
    pre.add_argument("--exe", type=Path)
    got, _ = pre.parse_known_args(argv)
    if got.exe is None or not got.exe.is_file():
        return "exe=? sha256=?"
    return f"exe={got.exe.resolve()} sha256={hashlib.sha256(got.exe.read_bytes()).hexdigest()}"


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    pre = argparse.ArgumentParser(add_help=False)
    pre.add_argument("--acceptance", action="store_true")
    pre.add_argument("--out", type=Path)
    pre.add_argument("--env", nargs="*", default=[])
    pre.add_argument("--host-state-script", type=Path, default=None)
    pre.add_argument("--join-state-script", type=Path, default=None)
    mine, _ = pre.parse_known_args(argv)
    pass_argv = [x for x in argv if x != "--acceptance"]
    if "-h" in argv or "--help" in argv:
        print(__doc__)
    if mine.acceptance and mine.out is not None:
        for script in (mine.host_state_script, mine.join_state_script):
            if script is None:
                continue
            bad = wall_clock_deathlink_steps(script)
            for i, key, old, new in bad:
                print(f"coop_policy_pair: FAIL: {script} entry {i} raises DEATHLINK {old}->{new} on the "
                      f"wall-clock key {key}; acceptance steps must be frame keyed (f<tick>)")
            if bad:
                return 2
        pass_argv = acceptance_argv(pass_argv, mine.out.resolve(), mine.env)
        pre2 = argparse.ArgumentParser(add_help=False)
        pre2.add_argument("--env", nargs="*", default=[])
        mine.env = pre2.parse_known_args(pass_argv)[0].env
    knob = any(item.startswith("PIKMIN_NETPLAY_TEST_COOP_EVENTS=") for item in mine.env)

    run_pair.write_bootstrap = write_bootstrap_m4d
    identity = exe_identity(pass_argv)
    print(f"coop_policy_pair: {identity}")
    rc = run_pair.main(pass_argv)
    if mine.out is None:
        return rc

    out = mine.out.resolve()
    peers = {"host": out / "host" / "run", "join": out / "join" / "peer" / "run"}
    lines = {name: policy_lines(run / "native.log") for name, run in peers.items()}
    ok = rc == 0
    print(f"coop_policy_pair: run_pair exit={rc}")
    for name, run in peers.items():
        log = run / "native.log"
        stage = grep_count(log, "START_STAGE")
        rand = grep_count(log, "[Pikmin Randomizer]")
        tuples = distinct_tuples(run / "hashes.txt")
        print(f"coop_policy_pair: {name} START_STAGE={stage} randomizer_lines={rand} "
              f"distinct_navi_piki_teki_item={tuples} coop_policy_lines={len(lines[name])}")
        if stage < 1 or rand < 1 or tuples < 2:
            print(f"coop_policy_pair: FAIL: {name} shows no gameplay")
            ok = False
    if lines["host"] != lines["join"]:
        print("coop_policy_pair: FAIL: [coop-policy] lines differ between peers")
        for i, (h, j) in enumerate(zip(lines["host"], lines["join"])):
            if h != j:
                print(f"  first difference at #{i}: host={h!r} join={j!r}")
                break
        else:
            print(f"  lengths host={len(lines['host'])} join={len(lines['join'])}")
        ok = False
    events = {name: [ln for ln in ls if ln.startswith("[coop-policy] TEST ")] for name, ls in lines.items()}
    if knob and (not events["host"] or events["host"] != events["join"]):
        print("coop_policy_pair: FAIL: TEST event lines missing or different between peers")
        ok = False
    for ln in lines["host"]:
        print(f"coop_policy_pair: host {ln}")
    errors, seqs, handovers = check_anchors(lines["host"])
    print(f"coop_policy_pair: anchors {seqs} (* = logged fallback) round_robin_handovers_both_live={handovers}")
    for err in errors:
        print(f"coop_policy_pair: FAIL: anchor {err}")
    if errors:
        ok = False
    for name, run in peers.items():
        for held, resume, before, during, after in hold_windows(run / "native.log"):
            print(f"coop_policy_pair: {name} hold window [{held}] .. [{resume}]: grant/policy lines "
                  f"before={len(before)} during={len(during)} after={len(after)}")
            if before:
                print(f"coop_policy_pair: {name}   last before: {before[-1]}")
            if after:
                print(f"coop_policy_pair: {name}   first after: {after[0]}")
            for ln in during:
                print(f"coop_policy_pair: FAIL: {name} grant while held: {ln}")
            if during:
                ok = False
    if mine.acceptance:
        heal = [ln for ln in lines["host"] if ln.startswith("[coop-policy] HEAL captain=2 ")]
        dl = [ln for ln in lines["host"] if re.match(r"\[coop-policy\] DEATHLINK killed=3 p1=0 ", ln)]
        rr = sum(handovers.values())
        print(f"coop_policy_pair: acceptance heal_captain2={len(heal)} round_robin_handovers_both_live={rr} "
              f"deathlink_killed3_p1down={len(dl)}")
        if not heal or not rr or not dl:
            print("coop_policy_pair: FAIL: acceptance lines missing")
            ok = False
    print(f"coop_policy_pair: {identity}")
    print(f"coop_policy_pair: {'PASS' if ok else 'FAIL'}")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
