"""Tool-only self test for the netplay harness scripts (ctest target
netplay_replay_selftest). No game is launched.

1. Generates a small PKNI file with gen_inputs.py, checks the header, the
   tick count and that Start/Y are never pressed.
2. Writes two identical synthetic hash logs, compares them (expect exit 0).
3. Mutates one sub-hash column, compares (expect exit 1 naming the column).
4. Truncates one log, compares (expect exit 1).
5. M4 lane B1: check_mirror.verify() on synthetic host/join run dirs with a
   local stand-in for the root parse_mirror_line (the real check imports the
   root reference parser; the selftest must not depend on a root worktree).
6. Gapfix C (issue #885): run_replay's refresher survives PermissionError
   on os.replace; run_pair's sim-frame keyed state scripts (parser, cursor,
   hash-log tick reader); coop_policy_pair's --acceptance defaults and its
   wall-clock DeathLink guard; b1_pairs' DeathLink apply-frame reader.
"""

import hashlib
import struct
import subprocess
import sys
import tempfile
import threading
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import check_mirror  # noqa: E402  (M4 lane B1 pure checks)
import run_pair  # noqa: E402  (gapfix C: frame-keyed state scripts)
import run_replay  # noqa: E402  (gapfix C: refresher retry)
import coop_policy_pair  # noqa: E402  (gapfix C: acceptance defaults)
import b1_pairs  # noqa: E402  (gapfix C: DeathLink apply frames)
GEN = HERE / "gen_inputs.py"
CMP = HERE / "compare_hashes.py"
PY = sys.executable

FORBIDDEN = 0x0800 | 0x1000  # Y | Start


def run_gen(ticks, seed, out, extra=()):
    r = subprocess.run(
        [PY, str(GEN), "--ticks", str(ticks), "--seed", str(seed), "--out", str(out), *extra],
        capture_output=True, text=True,
    )
    assert r.returncode == 0, f"gen_inputs failed: {r.stderr}"


def read_pkni(path, expect_version=2, expect_rec=56, expect_pad=14):
    with open(path, "rb") as f:
        blob = f.read()
    assert blob[:4] == b"PKNI", f"bad magic: {blob[:4]!r}"
    version, pads, rec = struct.unpack_from("<HHH", blob, 4)
    assert (version, pads, rec) == (expect_version, 4, expect_rec), (version, pads, rec)
    body = blob[10:]
    assert len(body) % expect_rec == 0, len(body)
    nticks = len(body) // expect_rec
    for i in range(nticks):
        for p in range(4):
            off = i * expect_rec + p * expect_pad
            (buttons,) = struct.unpack_from("<H", body, off)
            assert not buttons & FORBIDDEN, f"tick {i} pad {p}: menu button {buttons:#x}"
            if expect_version == 2:
                (flags,) = struct.unpack_from("<B", body, off + 13)
                assert flags == 0, f"tick {i} pad {p}: flags must be 0, got {flags}"
    return nticks


def stand_in_parse(line):
    """Minimal stand-in for root randomizer.netplay_mirror.parse_mirror_line:
    the same line rules (printable ASCII, single spaces, canonical numbers,
    known tags and arities). Raises ValueError like the reference."""
    if not line or len(line) > 256 or any(ord(c) < 0x20 or ord(c) > 0x7E for c in line):
        raise ValueError("bad line")
    parts = line.split(" ")
    if any(x == "" for x in parts) or len(parts) < 3 or parts[0] != "FRAME":
        raise ValueError("bad separators")

    def num(t):
        if not t.isdigit() or (len(t) > 1 and t[0] == "0"):
            raise ValueError("non-canonical number")
        return int(t)

    frame, tag, rest = num(parts[1]), parts[2], parts[3:]
    if tag == "EMPEROR" and not rest:
        return frame, tag, ()
    if tag == "CHECKED" and rest:
        return frame, tag, (" ".join(rest),)
    if tag in ("DEATHS", "DEATHLINK") and len(rest) == 1:
        return frame, tag, (num(rest[0]),)
    if tag == "RECEIVED" and len(rest) == 2:
        return frame, tag, (num(rest[0]), num(rest[1]))
    raise ValueError("unknown tag or arity")


def mirror_case(tmp, name, host_files, join_files):
    host = tmp / name / "host" / "run"
    join = tmp / name / "join" / "peer" / "run"
    host.mkdir(parents=True)
    join.mkdir(parents=True)
    for d, files in ((host, host_files), (join, join_files)):
        for fname, data in files.items():
            (d / fname).write_bytes(data.encode("ascii") if isinstance(data, str) else data)
    return host, join


def run_cmp(a, b):
    return subprocess.run([PY, str(CMP), str(a), str(b)], capture_output=True, text=True)


def synth_probe_run(root, d0, mode, events, schedule, late=0, summary_edit=None, frames=420):
    """Write a synthetic host+joiner run dir pair for camera_lead_probe.

    schedule: {frame: new_delay}: a growth adds k extra records that frame, a
    shrink skips k submit frames. events: [(kind, record)] (same on both peers).
    late: the lead run's view responds this many frames after its submit frame.
    summary_edit: callable(text) -> text, applied to the lead summary."""
    import os
    # 1. submit frames per record, mirroring the session's growth/shrink turns.
    recs = []  # (landing, submit frame)
    delay, skip, nxt = d0, 0, 0
    for f in range(1, frames + 1):
        target = schedule.get(f, delay)
        if target < delay:
            skip = delay - target
            delay = target
        if skip > 0:
            skip -= 1
            continue
        n = 1 + (target - delay if target > delay else 0)
        for _j in range(n):
            recs.append((nxt + d0, f))
            nxt += 1
        delay = max(delay, target)
    sub_at = {}
    for landing, f in recs:
        sub_at.setdefault(f, []).append(landing)
    ev = [(recs[r][1] + late, recs[r][0] + 1) for _k, r in events]  # (view frame, sim frame)
    base = 1000
    lines = ["[Pikmin Randomizer] START_STAGE day=2 color=1"]
    lead_frames = 0
    for f in range(1, frames + 1):
        for landing in sub_at.get(f, []):
            lines.append(f"[netplay] camlead submit f={landing} yaw=0")
        sim = base + 50 * sum(1 for _v, s in ev if s <= f)
        if mode == "lead":
            view = base + 50 * sum(1 for v, _s in ev if v <= f)
            lead = 1 if any(v <= f < s for v, s in ev) else 0
        else:
            view, lead = sim, 0
        lead_frames += lead
        lines.append(f"[netplay] camlead f={f} lead={lead} upd=1 steps=1 sim_yaw={sim} view_yaw={view} "
                     f"sim_dist=5.00 view_dist=5.00 sim_pitch=1.000 view_pitch=1.000 sim_fov=0.500 "
                     f"view_fov=0.500 corr=0.00")
    checked = len(recs) - 3 if mode == "lead" else 0
    text = (f"[netplay] camera lead summary: {'on' if mode == 'lead' else 'off'} views={frames} "
            f"lead_frames={lead_frames} sim_saw_lead=0 view_in_auth=0 gaps=0 keys_checked={checked} key_mismatch=0")
    if mode == "lead" and summary_edit is not None:
        text = summary_edit(text)
    lines.append(text)
    hashes = "".join(" ".join(f"{(i * 7 + c * 13):016x}" for c in range(8)).join([f"{i} ", "\n"]) for i in range(1, frames + 1))
    for rel in ("host/run", "join/peer/run"):
        d = root / f"d{d0}-{mode}" / rel
        os.makedirs(d, exist_ok=True)
        (d / "native.log").write_text("\n".join(lines) + "\n")
        (d / "hashes.txt").write_text(hashes)


def main():
    failures = 0

    def check(cond, what):
        nonlocal failures
        print(("PASS " if cond else "FAIL ") + what)
        if not cond:
            failures += 1

    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        gen_file = tmp / "inputs.pkni"
        run_gen(200, 7, gen_file)
        check(read_pkni(gen_file) == 200, "gen_inputs writes 200 parseable v2 ticks, no Start/Y")

        # Deterministic: same seed regenerates byte-identical output.
        gen_file2 = tmp / "inputs2.pkni"
        run_gen(200, 7, gen_file2)
        check(gen_file.read_bytes() == gen_file2.read_bytes(), "gen_inputs is seed-deterministic")

        # v2 yaw varies slowly and pads disagree; --v1 keeps the M1 format.
        with open(gen_file, "rb") as f:
            blob = f.read()
        yaws0 = [struct.unpack_from("<H", blob, 10 + p * 14 + 11)[0] for p in range(4)]
        check(any(y != 0 for y in yaws0), "v2 carries nonzero yaw")
        gen_v1 = tmp / "inputs_v1.pkni"
        run_gen(200, 7, gen_v1, extra=("--v1",))
        check(read_pkni(gen_v1, expect_version=1, expect_rec=44, expect_pad=11) == 200,
              "--v1 writes 200 parseable v1 ticks")
        # M2c review M4: --v1 must reproduce the M1 input stream, not just the
        # format. Golden SHA-256 of the M1 generator's output for
        # --ticks 200 --seed 7 (base 7b21c90d2 tools/netplay/gen_inputs.py).
        M1_GOLDEN_200_S7 = "8796ad2372d53ddd3236105cd09b02a8bdb52f3d10039e787394fd7788bf0cfe"
        check(hashlib.sha256(gen_v1.read_bytes()).hexdigest() == M1_GOLDEN_200_S7,
              "--v1 output is byte-identical to the M1 stream (M4)")

        base = []
        for t in range(1, 51):
            base.append(
                f"{t} {'ab' * 8} {'11' * 8} {'22' * 8} {'33' * 8} "
                f"{'44' * 8} {'55' * 8} {'66' * 8}"
            )
        ha = tmp / "a.hash"
        hb = tmp / "b.hash"
        ha.write_text("\n".join(base) + "\n")
        hb.write_text("\n".join(base) + "\n")
        r = run_cmp(ha, hb)
        check(r.returncode == 0 and "identical: 50 ticks" in r.stdout, "compare identical logs exits 0")

        mutated = list(base)
        row = mutated[29].split()
        row[3] = "99" * 8  # piki column at tick 30
        mutated[29] = " ".join(row)
        hc = tmp / "c.hash"
        hc.write_text("\n".join(mutated) + "\n")
        r = run_cmp(ha, hc)
        check(
            r.returncode == 1 and "tick 30" in r.stdout and "piki" in r.stdout,
            "compare reports first divergent tick and column",
        )

        hd = tmp / "d.hash"
        hd.write_text("\n".join(base[:40]) + "\n")
        r = run_cmp(ha, hd)
        check(r.returncode == 1 and "mismatch" in r.stdout, "compare reports length mismatch")

        # m6: 9-column (with rand) logs compare, and a mid-file width change
        # is an error rather than a misaligned compare.
        base9 = [ln + f" {'77' * 8}" for ln in base]
        h9a = tmp / "e.hash"
        h9b = tmp / "f.hash"
        h9a.write_text("\n".join(base9) + "\n")
        h9b.write_text("\n".join(base9) + "\n")
        r = run_cmp(h9a, h9b)
        check(r.returncode == 0 and "identical: 50 ticks" in r.stdout,
              "compare identical 9-column logs exits 0")
        mut9 = list(base9)
        row9 = mut9[10].split()
        row9[8] = "88" * 8  # rand column at tick 11
        mut9[10] = " ".join(row9)
        h9c = tmp / "g.hash"
        h9c.write_text("\n".join(mut9) + "\n")
        r = run_cmp(h9a, h9c)
        check(r.returncode == 1 and "tick 11" in r.stdout and "rand" in r.stdout,
              "compare reports divergent rand column")
        ragged = list(base9)
        ragged[20] = " ".join(ragged[20].split()[:8])  # 8-col row mid-file
        h9d = tmp / "h.hash"
        h9d.write_text("\n".join(ragged) + "\n")
        r = run_cmp(h9a, h9d)
        check(r.returncode == 1 and "expected 9 columns" in r.stdout,
              "compare rejects mid-file width change")

        # M4 lane B1: check_mirror pure checks.
        good_log = (
            "[Pikmin Randomizer] START_STAGE 1 day=2\n"
            "[Pikmin Randomizer] CHECK 47 Pikmin: Forest of Hope Landing\n"
            "[Pikmin Randomizer] CHECK_APPLIED 57 Some Streamed Check\n"
            "[Pikmin Randomizer] DEATHLINK_TOTAL 2\n"
            "[Pikmin Randomizer] CHECK 30 Population: 20 total Pikmin\n"
        )
        good_mirror = (
            "FRAME 40 RECEIVED 0 8\nFRAME 40 RECEIVED 1 1\n"
            "FRAME 120 CHECKED Pikmin: Forest of Hope Landing\n"
            "FRAME 300 CHECKED Some Streamed Check\n"
            "FRAME 300 DEATHLINK 2\nFRAME 310 DEATHS 3\n"
            "FRAME 400 CHECKED Population: 20 total Pikmin\nFRAME 500 DEATHS 4\n"
        )
        session = {"received": [8, 1], "pikmin_deaths": 2}
        host_files = {
            "native.log": good_log,
            "checks.txt": "47\n30\n",
            "deaths.txt": "1\n2\n",
            "state.txt": "PIKMIN_STATE 9 tok 1 0 127 0 CHECKS 0 DEATHLINK 2 END\n",
        }
        h, j = mirror_case(tmp, "m_ok", host_files, {"mirror-events.txt": good_mirror})
        errs, tags = check_mirror.verify(h, j, stand_in_parse, session)
        check(errs == [] and tags["CHECKED"] == 3 and tags["RECEIVED"] == 2,
              f"check_mirror accepts a consistent pair ({errs})")

        def bad_case(name, what, host_over=None, join_over=None, sess=session):
            hf = dict(host_files)
            hf.update(host_over or {})
            jf = {"mirror-events.txt": good_mirror}
            jf.update(join_over or {})
            for k in [k for k, v in hf.items() if v is None]:
                del hf[k]
            for k in [k for k, v in jf.items() if v is None]:
                del jf[k]
            hh, jj = mirror_case(tmp, name, hf, jf)
            e, _t = check_mirror.verify(hh, jj, stand_in_parse, sess)
            check(bool(e), f"check_mirror rejects: {what}")

        bad_case("m_crlf", "CRLF line (the parser rejects a carriage return)",
                 join_over={"mirror-events.txt": good_mirror.replace("\n", "\r\n")})
        bad_case("m_frames", "decreasing frames",
                 join_over={"mirror-events.txt": good_mirror.replace("FRAME 500", "FRAME 5")})
        bad_case("m_hostmirror", "a host mirror-events.txt",
                 host_over={"mirror-events.txt": "FRAME 1 EMPEROR\n"})
        bad_case("m_joinchecks", "a join checks.txt", join_over={"checks.txt": "47\n"})
        bad_case("m_dupcheck", "duplicate checks.txt lines", host_over={"checks.txt": "47\n30\n47\n"})
        bad_case("m_missingcheck", "checks.txt missing a CHECK slot", host_over={"checks.txt": "47\n"})
        bad_case("m_dupchecked", "a CHECKED name twice",
                 join_over={"mirror-events.txt": good_mirror + "FRAME 600 CHECKED Some Streamed Check\n"})
        bad_case("m_deaths", "DEATHS not base + deaths.txt lines", host_over={"deaths.txt": "1\n"})
        bad_case("m_deathlink", "DEATHLINK != the host's applied DEATHLINK_TOTAL",
                 host_over={"native.log": good_log.replace("DEATHLINK_TOTAL 2", "DEATHLINK_TOTAL 3")})
        bad_case("m_deathlink_none", "DEATHLINK lines with no applied total on the host",
                 host_over={"native.log": good_log.replace("[Pikmin Randomizer] DEATHLINK_TOTAL 2\n", "")})
        bad_case("m_deaths_retract", "a DEATHS total that decreases (fatal for the M4c ingest)",
                 join_over={"mirror-events.txt": good_mirror.replace("FRAME 310 DEATHS 3", "FRAME 310 DEATHS 5")})
        bad_case("m_deathlink_retract", "a DEATHLINK total that decreases",
                 host_over={"native.log": good_log.replace("DEATHLINK_TOTAL 2\n",
                                                           "DEATHLINK_TOTAL 2\n[Pikmin Randomizer] DEATHLINK_TOTAL 1\n")},
                 join_over={"mirror-events.txt": good_mirror.replace("FRAME 300 DEATHLINK 2\n",
                                                                     "FRAME 300 DEATHLINK 2\nFRAME 305 DEATHLINK 1\n")})
        bad_case("m_received_gap", "RECEIVED indices out of order",
                 join_over={"mirror-events.txt": good_mirror.replace("FRAME 40 RECEIVED 0 8\nFRAME 40 RECEIVED 1 1\n",
                                                                     "FRAME 40 RECEIVED 1 1\nFRAME 40 RECEIVED 0 8\n")})
        bad_case("m_emperor", "emperor.txt without EMPEROR", host_over={"emperor.txt": "EMPEROR_DEFEATED a b\n"})
        bad_case("m_received", "RECEIVED not the session list", sess={"received": [8, 2], "pikmin_deaths": 2})
        bad_case("m_nosession", "RECEIVED lines without a session.json", sess=None)

        # Gapfix C: run_replay's refresher never dies on PermissionError.
        rr = tmp / "refresh"
        rr.mkdir()
        fails = {"left": 3}

        def flaky_replace(src, dst):
            if fails["left"] > 0:
                fails["left"] -= 1
                raise PermissionError(13, "Access is denied (simulated WinError 5)")
            Path(src).replace(dst)

        done = threading.Event()
        errs = {"n": 0, "last": ""}
        th = threading.Thread(target=run_replay.refresh_loop, args=(rr, "STATE\n", done, errs, flaky_replace, 0.01))
        th.start()
        deadline = time.time() + 5
        while time.time() < deadline and not (rr / "state.txt").exists():
            time.sleep(0.01)
        alive = th.is_alive()
        done.set()
        th.join(5)
        check(alive and errs["n"] == 3 and "PermissionError" in errs["last"]
              and (rr / "state.txt").read_text() == "STATE\n",
              f"run_replay refresher retries PermissionError and keeps state.txt fresh ({errs})")

        # Gapfix C: run_pair sim-frame keyed state scripts.
        ss = tmp / "states-frames.txt"
        ss.write_text("# comment\n0 PIKMIN_STATE a {TOKEN} END\nf600 PIKMIN_STATE b END\n"
                      "30 PIKMIN_STATE c END\nf1200 PIKMIN_STATE d END\n")
        sched = run_pair.load_state_script(ss, "tok")
        check([(k, v) for k, v, _l in sched] == [("t", 0.0), ("f", 600), ("t", 30.0), ("f", 1200)]
              and sched[0][2] == "PIKMIN_STATE a tok END\n",
              "run_pair loads f<tick> keys in file order")
        step = run_pair.sched_step
        check(step(sched, 0, 100.0, None) == 0, "frame key waits while the hash log is empty")
        check(step(sched, 0, 100.0, 599) == 0, "frame key waits below its tick, however long")
        check(step(sched, 0, 10.0, 600) == 1, "frame key fires at its tick; the next time key still waits")
        check(step(sched, 0, 31.0, 600) == 2 and step(sched, 0, 31.0, 5000) == 3,
              "entries apply in file order once each key is reached")
        check(step(sched, 0, 1000.0, 300) == 0, "a later time key never jumps a pending frame key")
        legacy = tmp / "states-legacy.txt"
        legacy.write_text("20 PIKMIN_STATE b END\n0 PIKMIN_STATE a END\n5 PIKMIN_STATE c END\n")
        ls = run_pair.load_state_script(legacy, "tok")
        check([v for _k, v, _l in ls] == [0.0, 5.0, 20.0] and step(ls, 0, 6.0, None) == 1
              and step(ls, 0, 25.0, None) == 2,
              "time-only scripts are sorted and step as before")
        for name, text in (("bad-order", "0 PIKMIN_STATE a END\nf900 PIKMIN_STATE b END\nf600 PIKMIN_STATE c END\n"),
                           ("bad-key", "0 PIKMIN_STATE a END\nfx PIKMIN_STATE b END\n"),
                           ("bad-first", "f0 PIKMIN_STATE a END\n")):
            bad = tmp / f"states-{name}.txt"
            bad.write_text(text)
            try:
                run_pair.load_state_script(bad, "tok")
                rejected = False
            except SystemExit:
                rejected = True
            check(rejected, f"run_pair rejects a {name} frame-keyed script")
        hl = tmp / "hashes-tail.txt"
        check(run_pair.hash_log_tick(hl) is None, "hash_log_tick: missing log -> None")
        rows = "".join(f"{i} {'ab' * 8} {'11' * 8}\n" for i in range(1, 301))
        hl.write_text(rows + "301 abab")  # a torn last line is ignored
        cache = {}
        check(run_pair.hash_log_tick(hl, cache) == 300 and run_pair.hash_log_tick(hl, cache) == 300,
              "hash_log_tick reads the last complete line")

        # Gapfix C: coop_policy_pair --acceptance defaults and guard.
        acc = tmp / "acc"
        argv = coop_policy_pair.acceptance_argv(["--exe", "x", "--env", "A=1"], acc, ["A=1"])
        st = acc / "acceptance-states.txt"
        ev = acc / "acceptance-events.txt"
        check(argv[argv.index("--host-state-script") + 1] == str(st)
              and argv[argv.index("--join-state-script") + 1] == str(st)
              and argv[argv.index("--env") + 1] == f"PIKMIN_NETPLAY_TEST_COOP_EVENTS={ev}"
              and "A=1" in argv and ev.read_text().splitlines()[1:] == ["40 HP 2 0.5", "1000 DOWN 1"]
              and argv[argv.index("--profile") + 1] == "impact-day2",
              "coop_policy_pair --acceptance passes the built-in schedule, events and profile")
        argv2 = coop_policy_pair.acceptance_argv(["--profile", "navel-day2"], tmp / "acc2", [])
        check(argv2.count("--profile") == 1 and argv2[1] == "navel-day2",
              "coop_policy_pair --acceptance keeps an explicit --profile")
        check(coop_policy_pair.wall_clock_deathlink_steps(st) == [],
              "the built-in acceptance schedule keys every DeathLink rise to a frame")
        wall = tmp / "states-wall.txt"
        wall.write_text("0 PIKMIN_STATE 9 t 1 0 127 0 CHECKS 0 DEATHLINK 0 END\n"
                        "40 PIKMIN_STATE 9 t 1 0 127 0 CHECKS 0 DEATHLINK 1 END\n")
        check(coop_policy_pair.wall_clock_deathlink_steps(wall) == [(1, "40s", 0, 1)],
              "coop_policy_pair flags a wall-clock DeathLink step")
        mixed = tmp / "states-mixed.txt"
        mixed.write_text("0 PIKMIN_STATE 9 t 1 0 127 0 CHECKS 0 BENEFITS 0 0 0 0 0 0 0 0 0 DEATHLINK 0 END\n"
                         "5 PIKMIN_STATE 9 t 1 0 127 0 CHECKS 0 BENEFITS 0 1 0 0 0 0 0 0 0 DEATHLINK 0 END\n"
                         "f1200 PIKMIN_STATE 9 t 1 0 127 0 CHECKS 0 BENEFITS 0 1 0 0 0 0 0 0 0 DEATHLINK 1 END\n")
        check(coop_policy_pair.wall_clock_deathlink_steps(mixed) == [],
              "wall-clock grants are allowed when the DeathLink rise is frame keyed")

        # Gapfix C: b1_pairs pairs each DEATHLINK_TOTAL with the next apply frame.
        dlog = tmp / "dl-native.log"
        dlog.write_text("[netplay] randstate gen=1 applied at frame=32\n"
                        "[Pikmin Randomizer] DEATHLINK_TOTAL 2\n"
                        "[netplay] randstate gen=2 applied at frame=640\n"
                        "[netplay] randstate gen=3 applied at frame=700\n"
                        "[Pikmin Randomizer] DEATHLINK_TOTAL 3\n"
                        "[netplay] randstate gen=4 applied at frame=1230\n")
        check(b1_pairs.deathlink_apply_frames(dlog) == [640, 1230],
              "b1_pairs reads the DeathLink apply frames")

        # Gapfix C: coop_policy_pair finds grants inside a HOLD window.
        hlog = tmp / "hold-native.log"
        body = ("[coop-policy] ANCHOR kind=FLOWERS captain=1 next=2 live=11\n"
                "[netplay] hold at frame=100 freeze-after=111\n"
                "[Pikmin Randomizer] FLOWER_SHOWER nectar=5\n"
                "[netplay] held at frame=111\n"
                "{during}"
                "[netplay] resume at frame=112 gen=2 held_ms=22000\n"
                "[coop-policy] ANCHOR kind=FLOWERS captain=2 next=1 live=11\n")
        hlog.write_text(body.format(during=""))
        w = coop_policy_pair.hold_windows(hlog)
        check(len(w) == 1 and len(w[0][2]) == 2 and w[0][3] == [] and len(w[0][4]) == 1,
              "coop_policy_pair: grants before the freeze and after the resume are not in the hold")
        hlog.write_text(body.format(during="[coop-policy] HEAL captain=2 reason=lowest hp=50.0->100.0\n"))
        w = coop_policy_pair.hold_windows(hlog)
        check(len(w) == 1 and len(w[0][3]) == 1, "coop_policy_pair flags a grant between held at and resume")

    # #965 lane H: the harness env scrub covers every knob the native tree reads.
    import re as _re
    import launch_pair  # noqa: E402
    repo = HERE.parent.parent
    names = set()
    for sub in ("pc_port", "src", "include"):
        for f in (repo / sub).rglob("*"):
            if f.suffix in (".cpp", ".h", ".hpp", ".c") and f.is_file():
                try:
                    names.update(_re.findall(r'getenv\("(PIKMIN_(?:NETPLAY|TEST)_[A-Z0-9_]+)"\)',
                                             f.read_text(encoding="utf-8", errors="replace")))
                except OSError:
                    pass
    missing = sorted(n for n in names if n not in run_pair.SCRUB_KEYS and n not in launch_pair.SCRUB_KEYS
                     and not n.startswith(run_pair.SCRUB_PREFIXES))
    check(not missing, f"every getenv(PIKMIN_NETPLAY_*/PIKMIN_TEST_*) knob is in run_pair.SCRUB_KEYS ({len(names)} scanned; missing {missing})")
    leaky = {"PIKMIN_NETPLAY_CAMERA_LEAD": "0", "PIKMIN_NETPLAY_FUTURE_KNOB": "1", "PIKMIN_INPUT_RECORD": "x",
             "pikmin_netplay_hud": "1", "PATH": "keep", "PIKMIN_RANDOMIZER_TEST_BACKGROUND": "keep"}
    kept = run_pair.scrub_env(dict(leaky))
    check(set(kept) == {"PATH", "PIKMIN_RANDOMIZER_TEST_BACKGROUND"},
          f"scrub_env drops every PIKMIN_NETPLAY_*/PIKMIN_INPUT_* name incl. unknown and lower-case ({sorted(kept)})")
    kept = run_pair.scrub_env({"PIKMIN_TEST_CLOCK_TOD": "1", "PIKMIN_TEST_ONLY_PELLET_BONUS": "1",
                               "PIKMIN_TEST_ONLY_FUTURE_KNOB": "1", "PATH": "keep"})
    check(set(kept) == {"PATH"}, f"scrub_env drops PIKMIN_TEST_CLOCK_TOD and every PIKMIN_TEST_ONLY_* name ({sorted(kept)})")

    # #1028 review minor: run_pair refuses a scripted input file shorter than --ticks + 50 records.
    with tempfile.TemporaryDirectory() as tmp3:
        short = Path(tmp3) / "short.pkni"
        run_gen(100, 1, short)
        recs = (short.stat().st_size - 10) // 56
        check(run_pair.check_script_length(short, "host", recs - 50) == recs,
              "check_script_length accepts exactly ticks + 50 records")
        try:
            run_pair.check_script_length(short, "host", recs - 49)
            check(False, "check_script_length refuses a file one record short")
        except SystemExit as e:
            check("needs at least" in str(e), "check_script_length refuses a file one record short")

        # Every scripted scenario in coop_whistle_pair must pass run_pair's own length check
        # at the tick count its generator returns (the Onion scenario shipped 1700 records for 1700 ticks).
        import coop_whistle_pair  # noqa: E402
        for name, fn in (("whistle", coop_whistle_pair.whistle_inputs), ("onion", coop_whistle_pair.onion_inputs)):
            sd = Path(tmp3) / name
            sd.mkdir()
            ticks = fn(sd)
            for who in ("host", "join"):
                try:
                    run_pair.check_script_length(sd / f"{who}.pkni", who, ticks)
                    check(True, f"coop_whistle_pair {name} {who}.pkni satisfies check_script_length at {ticks} ticks")
                except SystemExit as e:
                    check(False, f"coop_whistle_pair {name} {who}.pkni satisfies check_script_length ({e})")


    # #965 lane H: camera_lead_probe judges latency on the submit frame (moving delay),
    # requires keys_checked > 0 in lead mode and fails a missing or non-zero counter.
    import contextlib
    import io
    import camera_lead_probe as clp
    d0 = 3
    sched = {100: 7, 200: 4}  # growth 3 -> 7 at frame 100, shrink 7 -> 4 at frame 200
    evs = [("turn", 60), ("zoom", 110), ("angle", 160), ("attention", 250), ("turn", 300)]

    def probe_case(name, **kw):
        root = tmp / f"probe-{name}"
        for mode in ("lead", "optout"):
            synth_probe_run(root, d0, mode, evs, sched, **(kw if mode == "lead" else {}))
        with contextlib.redirect_stdout(io.StringIO()):
            problems, _table = clp.check_pair({m: root / f"d{d0}-{m}" for m in ("lead", "optout")}, d0,
                                              {"host": evs, "join": evs}, {}, f"d{d0}")
        return problems

    with tempfile.TemporaryDirectory() as tmp2:
        tmp = Path(tmp2)
        base = probe_case("ok")
        check(base == [], f"probe: a moving delay (3 -> 7 -> 4) passes when the camera is right ({base[:2]})")
        # The same trace judged by record index (the old rule) would be wrong: the events sit on
        # submit frames that differ from their record index once the delay has moved.
        root = tmp / "probe-ok"
        subs = clp.submit_frames(clp.peer_log(root / "d3-lead", "host"))
        check(any(a != r for r, (_l, a, _p) in enumerate(subs)),
              "probe: the synthetic run really moves the delay (submit frame != record index)")
        check(probe_case("late", late=1) != [], "probe: a lead camera one frame late fails")
        check(any("key_mismatch=2" in x for x in probe_case("km", summary_edit=lambda t: t.replace("key_mismatch=0", "key_mismatch=2"))),
              "probe: key_mismatch > 0 fails")
        check(any("keys_checked=0" in x for x in probe_case("kc0", summary_edit=lambda t: __import__("re").sub(r"keys_checked=\d+", "keys_checked=0", t))),
              "probe: keys_checked=0 in the lead run fails (M4)")
        check(any("key_mismatch missing" in x for x in probe_case("miss", summary_edit=lambda t: t.replace(" key_mismatch=0", ""))),
              "probe: a missing counter fails (N2)")
        check(any("keys_checked missing" in x for x in probe_case("miss2", summary_edit=lambda t: __import__("re").sub(r" keys_checked=\d+", "", t))),
              "probe: a missing keys_checked fails")
        check(any("does not say `on`" in x for x in probe_case("off", summary_edit=lambda t: t.replace("summary: on", "summary: off"))),
              "probe: a lead run whose summary says off fails")

    # #1037: the PKNL session input log reader and the desync dump differ.
    import pknl  # noqa: E402
    import diff_desync  # noqa: E402
    meta = b"role host\ncheckpoint_gen 13\n"
    blob = b"PKNL" + struct.pack("<HHI", 1, 0, len(meta)) + meta
    blob += bytes([0x08]) + struct.pack("<I", 0) + struct.pack("<Q", 7)  # frame 0: neutral inputs, total only
    f1 = bytes(range(16))
    blob += bytes([0x09]) + struct.pack("<I", 1) + f1 + struct.pack("<Q", 8)               # frame 1: p0 changed
    blob += bytes([0x08]) + struct.pack("<I", 2) + struct.pack("<Q", 9)                    # frame 2: unchanged
    blob += bytes([0x40]) + struct.pack("<IBH", 2, 1, 3) + b"abc"                          # event
    lg = pknl.parse(blob)
    check(lg.get("role") == "host" and lg.get("checkpoint_gen") == "13", "pknl: meta read back")
    check(len(lg.frames) == 3 and lg.frames[2]["in0"] == f1 and lg.frames[2]["total"] == 9 and lg.frames[0]["in0"] == bytes(16),
          "pknl: frames decode with delta inputs")
    check(len(lg.events) == 1 and lg.events[0]["data"] == b"abc", "pknl: event decodes")
    cut = pknl.parse(blob[:-2])
    check(len(cut.frames) == 3 and cut.truncated > 0 and not cut.events, "pknl: a cut record is reported, earlier ones kept")
    try:
        pknl.parse(b"XXXX" + blob[4:])
        check(False, "pknl: bad magic refused")
    except ValueError:
        check(True, "pknl: bad magic refused")
    with tempfile.TemporaryDirectory() as dd:
        da, db = Path(dd) / "a.txt", Path(dd) / "b.txt"
        base = ("# tick 5: 2 records\n"
                "piki ord=0 type=1 state=2 hp=1 pos=(1,2,3) rot=(0,0,0) vel=(0,0,0) drv=(0,0,0) face=0 aux=[0,0,0,0] hash=aa xhash=bb\n"
                "teki ord=0 type=3 state=2 hp=9 pos=(5,5,5) rot=(0,0,0) vel=(0,0,0) drv=(0,0,0) face=0 aux=[0,0,0,0] hash=cc xhash=dd\n")
        da.write_text(base)
        db.write_text(base.replace("pos=(1,2,3)", "pos=(2,2,3)").replace("hash=aa", "hash=ab"))
        lines = []
        n, first, differing = diff_desync.diff(da, db, out=lines.append)
        check(n == 1 and first == 5 and differing == [(5, ("piki", 0))], "diff_desync: names the one differing object")
        check(any("pos: (1,2,3)  vs  (2,2,3)" in x for x in lines), "diff_desync: names the differing field")
        db.write_text(base)
        check(diff_desync.diff(da, db, out=lambda s: None)[0] == 0, "diff_desync: identical dumps -> 0")

    if failures:
        print(f"selftest: {failures} failure(s)")
        return 1
    print("selftest: all checks passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
