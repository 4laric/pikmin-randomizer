"""Responsiveness probe for the netplay M5c lane A lead camera (issue #887, #965).

For each requested input delay it runs two scripted lockstep pairs through
run_pair.py with PIKMIN_NETPLAY_CAMERA_TRACE=1: one with the lead camera on
(default) and one with PIKMIN_NETPLAY_CAMERA_LEAD=0 (the opt-out, which
presents the sim camera exactly as before M5c). Both peers play probe scripts
from gen_camera_inputs.py: hands-off pads with a camera turn, a zoom, an angle
change and an attention click at known record indices (the joiner's 100
records after the host's). Record r is a peer's r-th submitted input; it
lands on GekkoNet frame r + d0 (d0 = the start delay) whatever the delay is
when it is added.

Latency is judged against the frame the input was actually SUBMITTED on
(#965 lane H; group A's finding F1), not against the record index. Every add
prints `[netplay] camlead submit f=<landing>`, in add order, before the
`[netplay] camlead f=<a>` trace line of the frame `a` that follows the add;
the r-th submit line is record r, its submit frame is a, and the delay it was
added at is d = landing - a. With a fixed delay a == r and this is the old
table; with a MOVING delay (PIKMIN_NETPLAY_TEST_DELAY_SCHEDULE, adaptive
delay) a differs from r and only the submit frame is the right reference.
PASS needs, per event and peer: the camera at rest before it, the lead run's
first view change on frame a (latency 0), the opt-out run's on frame
a + d + 1 (= landing + 1, latency d + 1), plus two cross-checks in the lead
run (the trace's lead flag turns on at a; the sim camera columns change at
landing + 1). A "view change" is a frame-to-frame step of at least 1 yaw
unit, 0.05 distance, 0.005 pitch or 0.005 fov: the camera keeps settling for
100+ frames after a zoom, angle or attention event (steps of 0.01 / 0.001 and
single 9-10 unit yaw steps; group A's F2), which an exact comparison
mistakes for a response. The exact detector is still printed per event.
A fifth event, a mouse free-camera drag injected with
PIKMIN_NETPLAY_TEST_CAMERA_DRAG at a known frame, checks the drag routing:
the drag is immediate in both modes and turns each peer's own view.

Per run and peer it also requires: START_STAGE, distinct gameplay tuples (an
all-zero hash column is vacuous), the summary counters sim_saw_lead,
view_in_auth, gaps and key_mismatch present and 0 (a missing counter fails),
and, in the lead run, `on`, lead_frames > 0 and keys_checked > 0 (an opt-out
or a run that never checked a key must not pass, review M4). The lead and
opt-out hash logs must be identical per peer (the lead camera must not change
the simulation), host and joiner logs must match, and the lead run's sim
camera must equal the opt-out run's presented camera.

Moving delay: pass the schedule to both peers, for example
  --extra-env PIKMIN_NETPLAY_TEST_DELAY_SCHEDULE=800:1,950:8,1100:2,1250:6,1350:4,1450:7,1550:5,1650:3

Offline re-analysis of stored run dirs (no game is launched):
  --analyse-only            re-judge <out>/d<delay>-{lead,optout} from a
                            previous run of this tool (same --out, --delays,
                            --host-base)
  --lead-dir D --optout-dir D --d0 N [--events-json F]
                            any lead/opt-out run dirs; F holds
                            {"host": [[kind, record]...], "join": [...]}
                            (the dense scripts of the group-A tool); without
                            F the stock probe events are judged.

Everything runs hidden and private through run_pair.py (loopback binds,
private run dirs, bounded). Only run_pair's own spawned PIDs are touched.
"""

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
GEN = HERE / "gen_camera_inputs.py"
RUN_PAIR = HERE / "run_pair.py"
COMPARE = HERE / "compare_hashes.py"

TRACE = re.compile(
    r"\[netplay\] camlead f=(\d+) lead=(\d) upd=(\d) steps=(-?\d+)(?: start_cut)? sim_yaw=(\d+) view_yaw=(\d+) "
    r"sim_dist=([-\d.]+) view_dist=([-\d.]+) sim_pitch=([-\d.]+) view_pitch=([-\d.]+) "
    r"sim_fov=([-\d.]+) view_fov=([-\d.]+) corr=([-\d.]+)")


def parse_trace(log: Path):
    rows = {}
    for line in log.read_text(errors="replace").splitlines():
        m = TRACE.search(line)
        if not m:
            continue
        f = int(m.group(1))
        rows[f] = {
            "lead": int(m.group(2)),
            "sim": (int(m.group(5)), m.group(7), m.group(9), m.group(11)),
            "view": (int(m.group(6)), m.group(8), m.group(10), m.group(12)),
        }
    return rows


SUBMIT = re.compile(r"\[netplay\] camlead submit f=(\d+) yaw=(\d+)")
TRACE_F = re.compile(r"\[netplay\] camlead f=(\d+) ")

# A view step counts as the camera responding only when it is at least this big
# (yaw units, distance, pitch degrees, fov). Real first responses in the group-A
# runs were >= 44 yaw units / 0.22 distance / 0.03 fov; the camera's own settling
# is 0.01 / 0.001 steps and lone 9-10 unit yaw steps (F2).
SIG = (1, 0.05, 0.005, 0.005)
MIN_TUPLES = 100
MAX_LOCAL_DELAY = 8


def parse_submits(log: Path):
    out = []
    for line in log.read_text(errors="replace").splitlines():
        m = SUBMIT.search(line)
        if m:
            out.append((int(m.group(1)), int(m.group(2))))
    return out


def submit_frames(log: Path):
    """[(landing, submit_frame a or None, previous trace frame)] in add order
    (index = record). `a` is the frame of the next camlead trace line."""
    out, pending, prev = [], [], None
    for line in log.read_text(errors="replace").splitlines():
        m = SUBMIT.search(line)
        if m:
            pending.append((int(m.group(1)), prev))
            continue
        m = TRACE_F.search(line)
        if m:
            f = int(m.group(1))
            out.extend((landing, f, p) for landing, p in pending)
            pending = []
            prev = f
    out.extend((landing, None, p) for landing, p in pending)
    return out


def yaw_follow(rows, submits, delay, turn_record):
    """Live-yaw check: each submitted yaw (landing frame L = record + delay)
    against the view yaw of the frame presented just before it was sampled
    (L - delay - 1). Returns (checked, mismatches, first record >= the turn
    whose submitted yaw differs from the one before, relative to the turn)."""
    checked = mismatches = 0
    first = None
    prev = None
    for landing, yaw in submits:
        shown = rows.get(landing - delay - 1)
        if shown is not None:
            checked += 1
            if shown["view"][0] != yaw:
                mismatches += 1
        record = landing - delay
        if first is None and prev is not None and record >= turn_record and yaw != prev:
            first = record - turn_record
        prev = yaw
    return checked, mismatches, first


def first_change(rows, event, column, window=60):
    """Exact detector: first frame >= event - 2 whose `column` tuple differs
    from the rest value at event - 1. Returns (frame, rest_ok). Reported for
    reference only; it misfires on the camera's settling tail (F2)."""
    rest = rows.get(event - 1)
    if rest is None:
        return None, False
    rest_ok = all(rows.get(event - k, {}).get(column) == rest[column] for k in (1, 2, 3))
    for f in range(event - 2, event + window):
        r = rows.get(f)
        if r is not None and r[column] != rest[column]:
            return f, rest_ok
    return None, rest_ok


def step_sig(rows, f, col):
    """True when frame f's `col` tuple moved significantly from frame f - 1."""
    a, b = rows.get(f - 1), rows.get(f)
    if a is None or b is None:
        return False
    x, y = a[col], b[col]
    d = (abs(y[0] - x[0]), abs(float(y[1]) - float(x[1])), abs(float(y[2]) - float(x[2])),
         abs(float(y[3]) - float(x[3])))
    return any(v >= t for v, t in zip(d, SIG))


def first_sig(rows, a, col, window=60):
    """(first frame >= a - 2 with a significant step, rest_ok: frames a-3..a-1
    traced with no significant step in a-2..a-1)."""
    traced = all(rows.get(f) is not None for f in range(a - 3, a))
    rest_ok = traced and not any(step_sig(rows, f, col) for f in range(a - 2, a))
    for f in range(a - 2, a + window):
        if step_sig(rows, f, col):
            return f, rest_ok
    return None, rest_ok


def lead_onset(rows, a, window=60):
    for f in range(a - 2, a + window):
        r = rows.get(f)
        if r is not None and r["lead"] == 1:
            return f
    return None


def peer_log(out: Path, peer: str) -> Path:
    return out / "host" / "run" / "native.log" if peer == "host" else out / "join" / "peer" / "run" / "native.log"


def peer_dir(out: Path, peer: str) -> Path:
    return peer_log(out, peer).parent


def summary_counters(log: Path):
    """(summary text, {counter: int-string}) of the last `camera lead summary`."""
    lines = [ln for ln in log.read_text(errors="replace").splitlines() if "camera lead summary" in ln]
    if not lines:
        return None, None
    text = lines[-1].split("] ", 1)[-1]
    return text, dict(re.findall(r"(\w+)=(\d+)(?:\s|$)", text))


def gameplay(out: Path, peer: str):
    d = peer_dir(out, peer)
    starts = (d / "native.log").read_text(errors="replace").count("START_STAGE")
    tuples, lines = set(), 0
    for ln in (d / "hashes.txt").read_text(errors="replace").splitlines():
        f = ln.split()
        lines += 1
        if len(f) >= 6:
            tuples.add(tuple(f[2:6]))
    return starts, len(tuples), lines


def check_summary(mode, peer, text, counters, tag):
    """Contract counters. Returns a list of problem strings."""
    problems = []
    if text is None or counters is None:
        return [f"{tag} {mode} {peer}: no camera lead summary"]
    # Integration N2: a missing counter fails too, so a renamed or dropped
    # field cannot pass vacuously. I1 adds key_mismatch.
    for key in ("sim_saw_lead", "view_in_auth", "gaps", "key_mismatch"):
        if key not in counters:
            problems.append(f"{tag} {mode} {peer}: {key} missing from the summary")
        elif counters[key] != "0":
            problems.append(f"{tag} {mode} {peer}: {key}={counters[key]} (must be 0)")
    if mode == "lead":
        # Review M4: an opt-out (or a run that never noted a key) must not pass.
        if not re.search(r"summary: on\b", text):
            problems.append(f"{tag} {mode} {peer}: the lead run's summary does not say `on` "
                            f"(CAMERA_LEAD opt-out inherited?)")
        if int(counters.get("lead_frames", "0")) == 0:
            problems.append(f"{tag} {mode} {peer}: lead_frames=0 (no frame presented with the lead)")
        if "keys_checked" not in counters:
            problems.append(f"{tag} {mode} {peer}: keys_checked missing from the summary")
        elif int(counters["keys_checked"]) == 0:
            problems.append(f"{tag} {mode} {peer}: keys_checked=0 (the key check ran on nothing; vacuous)")
    return problems


def compare_hashes(a: Path, b: Path):
    r = subprocess.run([sys.executable, str(COMPARE), str(a), str(b)], capture_output=True, text=True)
    return r.returncode, r.stdout.strip()


def judge_events(lead: Path, optout: Path, d0: int, events, drags, tag):
    """Judge every event of both peers against its own submit frame.

    events: {"host": [(kind, record)], "join": [...]}; drags: {"host": frame,
    "join": frame} (immediate view change expected in both modes).
    Returns (problems, table rows, notes)."""
    problems, table, notes = [], [], []
    rows, subs = {}, {}
    for mode, run in (("lead", lead), ("optout", optout)):
        for peer in ("host", "join"):
            log = peer_log(run, peer)
            rows[(mode, peer)] = parse_trace(log)
            subs[(mode, peer)] = submit_frames(log)
            # Every add lands on record + d0 (no skipped or doubled record).
            bad = [(r, L) for r, (L, _a, _p) in enumerate(subs[(mode, peer)]) if L != r + d0]
            if not subs[(mode, peer)]:
                problems.append(f"{tag} {mode} {peer}: no `camlead submit` lines (trace off, or an exe without them)")
            elif bad:
                problems.append(f"{tag} {mode} {peer}: {len(bad)} adds not on record + d0, first {bad[:3]}")
    for peer in ("host", "join"):
        lr, orr = rows[("lead", peer)], rows[("optout", peer)]
        common = sorted(set(lr) & set(orr))
        diff = [g for g in common if lr[g]["sim"] != orr[g]["view"]]
        notes.append(f"{tag} {peer}: lead-run sim camera == opt-out presented camera on "
                     f"{len(common) - len(diff)}/{len(common)} traced frames")
        if not common:
            problems.append(f"{tag} {peer}: no traced frames in common")
        elif diff:
            problems.append(f"{tag} {peer}: lead-run sim camera differs from the opt-out view on "
                            f"{len(diff)} frames, first {diff[:3]}")
    for peer in ("host", "join"):
        for kind, r in events[peer]:
            entry = {"tag": tag, "peer": peer, "kind": kind, "record": r}
            for mode in ("lead", "optout"):
                sl = subs[(mode, peer)]
                if r >= len(sl) or sl[r][1] is None:
                    problems.append(f"{tag} {mode} {peer} {kind}@{r}: no submit/trace for the record")
                    entry[mode] = None
                    continue
                landing, a, prev = sl[r]
                d = landing - a
                rws = rows[(mode, peer)]
                f, rest_ok = first_sig(rws, a, "view")
                fx, _ = first_change(rws, a, "view")
                excluded = False
                if not rest_ok:
                    # The camera was not at rest. Only when every frame of the
                    # rest window is the sim camera's own motion (lead flag off,
                    # view == sim, and the opt-out run presents that same
                    # camera) is the event evaluated from frame a on; it is
                    # listed, never silently passed.
                    lr, orr = rows[("lead", peer)], rows[("optout", peer)]
                    sim_only = all(lr.get(g) is not None and lr[g]["lead"] == 0 and lr[g]["view"] == lr[g]["sim"]
                                   and orr.get(g) is not None and orr[g]["view"] == lr[g]["sim"]
                                   for g in range(a - 3, a))
                    if sim_only:
                        excluded = True
                        f = next((g for g in range(a, a + 60) if step_sig(rws, g, "view")), None)
                        notes.append(f"{tag} {mode} {peer} {kind}@{r}: rest-excluded (sim-camera homing step "
                                     f"before a={a}); first step from a at {f}")
                lat = None if f is None else f - a
                want = 0 if mode == "lead" else d + 1
                ok = lat == want and (rest_ok or excluded) and prev == a - 1 and 1 <= d <= MAX_LOCAL_DELAY
                entry[mode] = {"a": a, "d": d, "lat": lat, "want": want, "rest": rest_ok or excluded,
                               "exact": None if fx is None else fx - a}
                if not ok:
                    problems.append(f"{tag} {mode} {peer} {kind}@{r}: submit frame a={a} d={d} first change "
                                    f"{f} -> latency {lat}, want {want} (rest={rest_ok}, prev trace {prev})")
                if mode == "lead":
                    on = lead_onset(rws, a)
                    fs, _ = first_sig(rws, a, "sim")
                    if excluded:
                        fs = next((g for g in range(a, a + 60) if step_sig(rws, g, "sim")), None)
                    if not (on == a and fs == landing + 1):
                        problems.append(f"{tag} lead {peer} {kind}@{r}: lead flag on at {on} (want a={a}), "
                                        f"sim camera change at {fs} (want landing+1={landing + 1})")
            table.append(entry)
    for peer in ("host", "join"):
        if drags.get(peer) is None:
            continue
        ev = drags[peer]
        entry = {"tag": tag, "peer": peer, "kind": "drag", "record": ev}
        for mode in ("lead", "optout"):
            rws = rows[(mode, peer)]
            f, rest_ok = first_sig(rws, ev, "view")
            lat = None if f is None else f - ev
            entry[mode] = {"a": ev, "d": 0, "lat": lat, "want": 0, "rest": rest_ok, "exact": None}
            # Immediate in both modes (the drag goes straight into the sim camera).
            if lat != 0 or not rest_ok:
                problems.append(f"{tag} {mode} {peer} drag@{ev}: latency {lat}, want 0 (rest={rest_ok})")
        table.append(entry)
    return problems, table, notes


def print_table(table):
    print()
    print("run        peer kind       record |  lead: a     d  lat | optout: a     d  lat want | exact(l/o) rest")
    for e in table:
        l, o = e["lead"], e["optout"]
        if l is None or o is None:
            print(f"{e['tag']:10s} {e['peer']:4s} {e['kind']:10s} {e['record']:6d} | (missing)")
            continue
        print(f"{e['tag']:10s} {e['peer']:4s} {e['kind']:10s} {e['record']:6d} | {l['a']:6d} {l['d']:2d} "
              f"{str(l['lat']):>4s} | {o['a']:6d} {o['d']:2d} {str(o['lat']):>4s} {o['want']:4d} | "
              f"{str(l['exact']):>4s}/{str(o['exact']):<4s} {'yes' if l['rest'] and o['rest'] else 'NO'}")


def check_pair(runs, d0, events, drags, tag, live_yaw_turns=None):
    """All per-delay checks on an existing lead/opt-out pair of run dirs.
    Returns (problem strings, table rows)."""
    problems, table = [], []
    for mode, out in runs.items():
        for peer in ("host", "join"):
            starts, ntuples, nlines = gameplay(out, peer)
            text, counters = summary_counters(peer_log(out, peer))
            print(f"camera_lead_probe: {tag} {mode} {peer}: START_STAGE={starts} tuples={ntuples} hash_lines={nlines} "
                  f"{text.split('summary: ', 1)[-1] if text else 'no summary'}")
            if starts < 1:
                problems.append(f"{tag} {mode} {peer}: no START_STAGE")
            if ntuples < min(MIN_TUPLES, max(2, nlines // 2)):
                problems.append(f"{tag} {mode} {peer}: only {ntuples} distinct gameplay tuples in {nlines} hash "
                                f"lines (vacuous)")
            problems += check_summary(mode, peer, text, counters, tag)
    # Hash logs: host vs joiner per run; lead vs opt-out per peer (the same
    # inputs) unless the run submits live yaw, when the two runs differ by design.
    for mode, out in runs.items():
        rc, txt = compare_hashes(peer_dir(out, "host") / "hashes.txt", peer_dir(out, "join") / "hashes.txt")
        print(f"camera_lead_probe: {tag} {mode} hashes host vs joiner: {txt} (exit {rc})")
        if rc != 0:
            problems.append(f"{tag} {mode}: host and joiner hash logs differ: {txt}")
    if live_yaw_turns is not None:
        rc, txt = compare_hashes(peer_dir(runs["lead"], "host") / "hashes.txt",
                                 peer_dir(runs["optout"], "host") / "hashes.txt")
        print(f"camera_lead_probe: {tag} hashes lead vs opt-out (expected to differ): {txt}")
        for mode, out in runs.items():
            for peer, turn in live_yaw_turns.items():
                checked, bad, first = yaw_follow(parse_trace(peer_log(out, peer)), parse_submits(peer_log(out, peer)),
                                                 d0, turn)
                print(f"camera_lead_probe: {tag} {mode} {peer}: submitted yaw == presented view yaw for "
                      f"{checked - bad}/{checked} submits; first yaw change {first} records after the turn")
                want = 1 if mode == "lead" else d0 + 2
                if bad != 0 or checked == 0 or first != want:
                    problems.append(f"{tag} {mode} {peer}: live-yaw follow failed (bad={bad} checked={checked} "
                                    f"first={first} want {want})")
        return problems, table
    for peer in ("host", "join"):
        rc, txt = compare_hashes(peer_dir(runs["lead"], peer) / "hashes.txt",
                                 peer_dir(runs["optout"], peer) / "hashes.txt")
        print(f"camera_lead_probe: {tag} {peer} hashes lead vs opt-out: {txt} (exit {rc})")
        if rc != 0:
            problems.append(f"{tag} {peer}: lead and opt-out hash logs differ: {txt}")
    jp, table, notes = judge_events(runs["lead"], runs["optout"], d0, events, drags, tag)
    for n in notes:
        print(f"camera_lead_probe: {n}")
    return problems + jp, table


def gen_probe(path: Path, ticks: int, base: int):
    subprocess.run([sys.executable, str(GEN), "probe", "--ticks", str(ticks), "--out", str(path),
                    "--turn-at", str(base), "--zoom-at", str(base + 300), "--angle-at", str(base + 500),
                    "--attention-at", str(base + 700)], check=True)
    return {"turn": base, "zoom": base + 300, "angle": base + 500, "attention": base + 700, "drag": base + 800}


def stock_events(host_base):
    ev_host = {"turn": host_base, "zoom": host_base + 300, "angle": host_base + 500, "attention": host_base + 700,
               "drag": host_base + 800}
    b = host_base + 100
    ev_join = {"turn": b, "zoom": b + 300, "angle": b + 500, "attention": b + 700, "drag": b + 800}
    return ev_host, ev_join


def split_events(ev_host, ev_join):
    events = {"host": [(k, v) for k, v in ev_host.items() if k != "drag"],
              "join": [(k, v) for k, v in ev_join.items() if k != "drag"]}
    drags = {"host": ev_host.get("drag"), "join": ev_join.get("drag")}
    return events, drags


def finish(problems, table):
    print_table(table)
    print()
    for pr in problems:
        print(f"camera_lead_probe: problem: {pr}")
    print(f"camera_lead_probe: {'PASS' if not problems else 'FAIL'} ({len(problems)} problem(s))")
    return 0 if not problems else 1


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--exe", type=Path, help="required unless an offline analysis flag is used")
    p.add_argument("--out", type=Path, help="private output dir")
    p.add_argument("--delays", default="3,4")
    p.add_argument("--port", type=int, help="first host UDP port (one per run)")
    p.add_argument("--ticks", type=int, default=2100)
    p.add_argument("--host-base", type=int, default=900, help="host turn record index")
    p.add_argument("--shot-frames", default="", help="PIKMIN_NETPLAY_CAMERA_SHOT frames for the host (a,b,c)")
    p.add_argument("--extra-env", nargs="*", default=[],
                   help="K=V for both peers, e.g. PIKMIN_NETPLAY_TEST_DELAY_SCHEDULE=800:1,950:8 for a moving delay")
    p.add_argument("--live-yaw", action="store_true",
                   help="PIKMIN_NETPLAY_TEST_SCRIPT_LIVE_YAW=1 on both peers: scripted pads, live control yaw. "
                        "Checks that every submitted yaw is the view yaw the peer presented when it was sampled; "
                        "lead and opt-out then submit different yaws, so their hash logs differ by design and only "
                        "host vs joiner is compared (fixed delay only)")
    p.add_argument("--analyse-only", action="store_true",
                   help="offline: re-judge the d<delay>-{lead,optout} run dirs already under --out "
                        "(add --live-yaw for runs made with it)")
    p.add_argument("--lead-dir", type=Path, help="offline: a lead-run dir (with --optout-dir --d0)")
    p.add_argument("--optout-dir", type=Path)
    p.add_argument("--d0", type=int, help="offline: the run's start delay")
    p.add_argument("--events-json", type=Path,
                   help='offline: {"host": [[kind, record]...], "join": [...]}; no drag events are judged')
    a = p.parse_args(argv)

    if a.lead_dir is not None:
        if a.optout_dir is None or a.d0 is None:
            p.error("--lead-dir needs --optout-dir and --d0")
        if a.events_json is not None:
            raw = json.loads(a.events_json.read_text())
            events = {peer: [(k, int(r)) for k, r in raw[peer]] for peer in ("host", "join")}
            drags = {}
        else:
            events, drags = split_events(*stock_events(a.host_base))
        problems, table = check_pair({"lead": a.lead_dir, "optout": a.optout_dir}, a.d0, events, drags,
                                     f"d{a.d0}")
        return finish(problems, table)

    if a.analyse_only:
        if a.out is None:
            p.error("--analyse-only needs --out")
        problems, table = [], []
        ev_host, ev_join = stock_events(a.host_base)
        events, drags = split_events(ev_host, ev_join)
        turns = {"host": ev_host["turn"], "join": ev_join["turn"]}
        for delay in [int(x) for x in a.delays.split(",") if x]:
            runs = {m: a.out / f"d{delay}-{m}" for m in ("lead", "optout")}
            pr, tb = check_pair(runs, delay, events, drags, f"d{delay}",
                                live_yaw_turns=turns if a.live_yaw else None)
            problems += pr
            table += tb
        return finish(problems, table)

    if a.exe is None or a.out is None or a.port is None:
        p.error("--exe, --out and --port are required for a live run")
    a.out.mkdir(parents=True, exist_ok=True)
    inputs = a.out / "inputs"
    inputs.mkdir(exist_ok=True)
    ev_host = gen_probe(inputs / "probe-host.pkni", a.ticks + 50, a.host_base)
    ev_join = gen_probe(inputs / "probe-join.pkni", a.ticks + 50, a.host_base + 100)
    events, drags = split_events(ev_host, ev_join)

    port = a.port
    problems = []
    table = []
    for delay in [int(x) for x in a.delays.split(",") if x]:
        runs = {}
        for mode in ("lead", "optout"):
            out = a.out / f"d{delay}-{mode}"
            env = ["PIKMIN_NETPLAY_CAMERA_TRACE=1"] + list(a.extra_env)
            if a.live_yaw:
                env.append("PIKMIN_NETPLAY_TEST_SCRIPT_LIVE_YAW=1")
            if mode == "optout":
                env.append("PIKMIN_NETPLAY_CAMERA_LEAD=0")
            env_host = [f"PIKMIN_NETPLAY_LOCAL_INPUT_FILE={(inputs / 'probe-host.pkni').resolve()}",
                        f"PIKMIN_NETPLAY_TEST_CAMERA_DRAG={ev_host['drag']}:0.2"]
            if a.shot_frames:
                shots = a.out / "shots"
                shots.mkdir(exist_ok=True)
                env_host.append(f"PIKMIN_NETPLAY_CAMERA_SHOT={shots.resolve()}/d{delay}:{a.shot_frames}")
                (shots / f"d{delay}").mkdir(exist_ok=True)
            cmd = [sys.executable, str(RUN_PAIR), "--exe", str(a.exe), "--ticks", str(a.ticks), "--out", str(out),
                   "--host-port", str(port), "--delay", str(delay), "--env", *env, "--env-host", *env_host,
                   "--env-join", f"PIKMIN_NETPLAY_LOCAL_INPUT_FILE={(inputs / 'probe-join.pkni').resolve()}",
                   f"PIKMIN_NETPLAY_TEST_CAMERA_DRAG={ev_join['drag']}:0.2"]
            port += 1
            log = a.out / f"d{delay}-{mode}.log"
            with open(log, "w") as fh:
                fh.write("CMD: " + " ".join(cmd) + "\n")
                fh.flush()
                rc = subprocess.run(cmd, stdout=fh, stderr=subprocess.STDOUT).returncode
                fh.write(f"EXIT: {rc}\n")
            print(f"camera_lead_probe: delay {delay} {mode}: run_pair exit {rc} ({log})")
            if rc != 0:
                problems.append(f"d{delay} {mode}: run_pair exit {rc}")
            runs[mode] = out
        try:
            pr, tb = check_pair(runs, delay, events, drags, f"d{delay}",
                                live_yaw_turns={"host": ev_host["turn"], "join": ev_join["turn"]} if a.live_yaw else None)
        except (OSError, ValueError) as exc:
            pr, tb = [f"d{delay}: cannot analyse the run dirs: {exc}"], []
        problems += pr
        table += tb
    return finish(problems, table)


if __name__ == "__main__":
    raise SystemExit(main())
