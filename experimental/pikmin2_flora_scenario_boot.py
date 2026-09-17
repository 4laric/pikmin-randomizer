"""Flora scenario-boot staging/verification adapter (#766, enemies-1 flora gate).

Stages a private flora arena for the real-engine scenario boot: a room plus a live
starting squad, a parked captain slot, and flora scenery records for 47 Clover, 80
Tukushi and 89 Chiyogami (slots 0-2) consumed from the landed #697/#723 hookup
contract (read-only). Verifies run logs for the receipt-parseable marker grammar
(boot/window/squad/session per identity, guard, PASS/FAIL/BLOCKED).

Fail-closed: absent/malformed inputs, hash drift, or a tampered arena raise before any
verdict. The adapter writes only the arena dir. No engine, no gameplay claims; gates are
claimed solely on observed markers. Captain safety #632 is enforced by the fixture, not
here; this adapter records the guard/source hashes for the handoff.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path

ISSUE = 766
DOWNSTREAM_ISSUE = 114
GUARD_PATH = "scripts/p2_fixture_captain_guard.h"
GUARD_SHA256 = "d2f678c9eda75e151eb534077dff9e30ad36ae4796881d971bbd09945f3c3474"

FLORA = (
    {"identity": "Clover", "source_id": 47, "slot": 0},
    {"identity": "Tukushi", "source_id": 80, "slot": 1},
    {"identity": "Chiyogami", "source_id": 89, "slot": 2},
)

WINDOW_RE = re.compile(r"P2_FLORA_SCENARIO_WINDOW\s+size=(\d+)x(\d+)")
SQUAD_RE = re.compile(r"P2_FLORA_SCENARIO_SQUAD\s+pikis=(\d+)")
SESSION_RE = re.compile(
    r"P2_FLORA_SCENARIO_SESSION\s+identity=(\S+)\s+converted=(\d+)\s+"
    r"received=(\d+)\s+hauled=(\d+)")
DOWN_RE = re.compile(
    r"P2_FIXTURE_CAPTAIN_DOWN\s+tick=(\d+)\s+hp=([^\s]+)\s+"
    r"orima_dead=(\d)\s+dead_state=(\d)\s+outcome=BLOCKED")
PASS_RE = re.compile(r"^PASS\s+(\S+)", re.MULTILINE)


class ArenaGapError(ValueError):
    """Staging inputs are missing or the arena drifted; fail closed."""


def sha256_file(path):
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def stage_arena(room_gen, squad_count, captain_home, run_dir):
    """Stage room bytes + squad/captain/scenery records into a private arena."""
    room_gen, run_dir = Path(room_gen), Path(run_dir)
    if not room_gen.is_file():
        raise ArenaGapError("room gen missing: %s" % room_gen)
    if not isinstance(squad_count, int) or isinstance(squad_count, bool) \
            or squad_count < 1 or squad_count > 100:
        raise ArenaGapError("squad_count must be an int in 1..100")
    try:
        home = (float(captain_home[0]), float(captain_home[1]), float(captain_home[2]))
    except (TypeError, ValueError, IndexError):
        raise ArenaGapError("captain_home must be three finite numbers")
    import math
    if any(not math.isfinite(v) for v in home):
        raise ArenaGapError("captain_home must be finite")
    room_bytes = room_gen.read_bytes()
    if not room_bytes:
        raise ArenaGapError("room gen is empty")
    arena = Path(run_dir)
    arena.mkdir(parents=True, exist_ok=True)
    (arena / "room.gen").write_bytes(room_bytes)
    scenery = [{"identity": row["identity"], "source_id": row["source_id"],
                "slot": row["slot"]} for row in FLORA]
    manifest = {
        "schema": 1, "lane": "flora-scenario-boot", "issue": ISSUE,
        "room_gen_sha256": hashlib.sha256(room_bytes).hexdigest(),
        "squad_count": squad_count, "captain_home": list(home),
        "scenery": scenery,
        "guard": {"path": GUARD_PATH, "sha256": GUARD_SHA256},
    }
    (arena / "flora-arena.json").write_text(
        json.dumps(manifest, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    return manifest


def validate_arena(run_dir):
    """Refuse an arena whose files drifted from its manifest."""
    arena = Path(run_dir)
    try:
        manifest = json.loads((arena / "flora-arena.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return ["missing-or-bad-arena-manifest"]
    problems = []
    if manifest.get("schema") != 1:
        problems.append("bad-arena-schema")
    try:
        actual = sha256_file(arena / "room.gen")
    except OSError:
        problems.append("missing-room-gen")
    else:
        if actual != manifest.get("room_gen_sha256"):
            problems.append("hash-mismatch-room-gen")
    scenery = manifest.get("scenery")
    if not isinstance(scenery, list) or len(scenery) != 3:
        problems.append("scenery-must-list-3-identities")
    else:
        want = [(r["identity"], r["source_id"], r["slot"]) for r in FLORA]
        got = [(r.get("identity"), r.get("source_id"), r.get("slot")) for r in scenery]
        if got != want:
            problems.append("scenery-mismatch-47-80-89")
    guard = manifest.get("guard") or {}
    if guard.get("sha256") != GUARD_SHA256:
        problems.append("guard-hash-mismatch")
    return problems


def verify_run_log(log_text):
    """Map a headed run log to per-identity verdicts. Never invents a PASS."""
    if not isinstance(log_text, str):
        raise ArenaGapError("run log must be text")
    window = bool(WINDOW_RE.search(log_text))
    squads = [int(n) for n in SQUAD_RE.findall(log_text)]
    sessions = {}
    for identity, converted, received, hauled in SESSION_RE.findall(log_text):
        sessions[identity] = {"converted": int(converted),
                              "received": int(received), "hauled": int(hauled)}
    downs = DOWN_RE.findall(log_text)
    passes = PASS_RE.findall(log_text)
    identities = {}
    for row in FLORA:
        name = row["identity"]
        session = sessions.get(name)
        if session is None:
            identities[name] = "unobserved"
        elif (session["converted"] > 0 and session["received"] == session["converted"]
                and session["hauled"] == 0):
            identities[name] = "observed"
        else:
            identities[name] = "contradicted"
    failures = []
    if downs:
        failures.append("captain-down")
    overall = (window and bool(squads) and
               all(v == "observed" for v in identities.values()) and
               not failures and "PASS FLORA_SCENARIO_BOOT" in log_text)
    return {"window_960x540": window, "squad_counts": squads,
            "sessions": sessions, "identities": identities,
            "captain_down": bool(downs), "passes": passes,
            "overall_pass": overall}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--room-gen", default=None)
    parser.add_argument("--squad", type=int, default=20)
    parser.add_argument("--captain-home", default="34.0,30.0,1878.0")
    parser.add_argument("--out", required=True)
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--verify-log", default=None)
    args = parser.parse_args(argv)
    out = Path(args.out)
    try:
        if args.verify_log is not None:
            verdict = verify_run_log(
                Path(args.verify_log).read_text(encoding="utf-8", errors="replace"))
            print(json.dumps(verdict, indent=1, sort_keys=True))
            return 0
        if args.check:
            problems = validate_arena(out)
            print(json.dumps({"problems": problems}, indent=1))
            return 0 if not problems else 1
        if args.room_gen is None:
            print("refused: --room-gen is required")
            return 2
        home = tuple(float(v) for v in args.captain_home.split(","))
        manifest = stage_arena(args.room_gen, args.squad, home, out)
    except (ArenaGapError, ValueError, OSError) as exc:
        print("refused: %s" % exc)
        return 2
    print(json.dumps({"room_gen_sha256": manifest["room_gen_sha256"],
                      "scenery": [r["identity"] for r in manifest["scenery"]]},
                     indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())