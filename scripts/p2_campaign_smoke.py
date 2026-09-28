"""Automated hidden-window P2 campaign smoke test (#186).

One bounded launch of the real native game (hidden, no player input) on a
generated playable-pool P2 seed, then a pure-log parse of ``native.log``.

The seed starts on Forest of Hope day 2 (profile ``foh-day2``), so the loaded
area is the ``hope_`` placement slots active on the start day. ``expected``
bindings are the seed's ``p2_layout`` bindings whose accepted slot label starts
with ``hope_`` and whose ``first_day`` is not after the start day; every one of
them must emit a bind/ready marker or the smoke exits non-zero.

The parse half (:func:`parse_native_log` / :func:`evaluate`) is pure and unit
tested from fixture text; the orchestration half only stages a private session,
launches the exe hidden, stops it after ``--seconds`` by PID, and writes JSON.

Captain safety (#632): this is an unprotected observation run (no input, no
captain-damage test), so the captain is parked at the start area and never
moved toward an enemy. The parser treats any ``P2_FIXTURE_CAPTAIN_DOWN`` /
``CAPTAIN_DOWN`` marker as BLOCKED (exit 86) and the smoke records the canonical
guard source hash. It never changes health or production behavior.

Usage:
    py -3.12 scripts/p2_campaign_smoke.py --exe C:/p2build/bin/nectar.exe \
        [--seed NAME] [--seconds 150] [--out output/reduced/rd-p2-campaign-smoke/smoke.json] \
        [--content-root output/reduced/rd-p2ap-content/p2-content]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import threading
import time
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

DEFAULT_ASSETS = Path("C:/Users/alari/bbft/dist/cohesion/pikmin/assets")
DEFAULT_ISO = Path("C:/Users/alari/Downloads/PIKMIN2 for GAMECUBE.iso")
DEFAULT_CONTENT = ROOT / "output/reduced/rd-p2ap-content/p2-content"
DEFAULT_SESSION = Path("C:/p2smoke")
DEFAULT_OUT = ROOT.parent / "smoke.json"
GUARD_SOURCE = ROOT / "scripts/p2_fixture_captain_guard.h"
PLACEMENT_DOC = ROOT / "docs/PIKMIN2_ADMITTED_PLACEMENT.json"
MINGW_BIN = "C:/msys64/mingw64/bin"
START_DAY = 2  # foh-day2 profile

# A line is a bind/ready marker when it names a generator/actor the seed bound.
ENEMY_READY_RE = re.compile(r"P2_ENEMY_READY\s+species=(\S+).*?\bgenerator=(\d+)")
MAMUTA_READY_RE = re.compile(r"P2_MAMUTA_READY\s+generator=(\d+)")
BATCH2_BIND_RE = re.compile(r"P2_BATCH2_BIND\s+generator=(\d+)\s+key=(\S+)")
GENERIC_BIND_RE = re.compile(r"P2_([A-Z0-9_]+)_BIND\b.*?\bgenerator=(\d+)")
SOURCE_ID_RE = re.compile(r"\bsource_id=(\d+)")
# P2 source id -> enum name for the bind markers that carry source_id.
SOURCE_ENUM = {
    9: "Kogane", 23: "Sarai", 44: "BlueKochappy", 45: "YellowKochappy",
    54: "Miulin", 57: "Kurage", 59: "FireOtakara", 60: "WaterOtakara",
    61: "GasOtakara", 62: "ElecOtakara", 78: "MiniHoudai", 79: "Sokkuri",
}
GENERATED_PLACEMENT_RE = re.compile(
    r"P2_GENERATED_PLACEMENT\s+source_id=(\d+)\s+target=(\d+).*?\bbound=1")
SEED_RESOLVE_RE = re.compile(r"P2_SEED_RESOLVE\s+source_id=(\d+)\s+target=(\d+)")
PLACEMENT_SLOT_RE = re.compile(r"P2_PLACEMENT_SLOT\s+generator=(\d+)\s+slot=(\d+)")
SETUP_SKIP_RE = re.compile(r"P2_SETUP_SKIP\s+(\S+)\s+(\S+)")
SETUP_ABORT_RE = re.compile(r"P2_SETUP_ABORT\s+(\S+)\s+(\S+)")
MISSING_FILE_RE = re.compile(
    r"(?i)(no such file|file not found|cannot open|failed to open|missing .*file|"
    r"->\s*FAIL|DVDOpen.*FAIL)")
ABORT_TEXT_MARKERS = ("P2_SETUP_ABORT", "Assertion failed", "terminate called",
                      "std::bad_alloc", "Unhandled exception")
CAPTAIN_DOWN_MARKERS = ("P2_FIXTURE_CAPTAIN_DOWN", "CAPTAIN_DOWN")

WORLD_RENDERED_MARKER = "PIKMIN_WORLD_RENDERED"


def _sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def parse_native_log(text):
    """Pure native.log parser: boot/abort markers, binds, skips, missing files.

    Returns a dict with ``booted``, ``aborted``, ``abort_markers``,
    ``captain_down``, ``bound`` (uid -> species), ``resolved`` (uids seen only in
    resolution/placement evidence), ``species_counts``, ``setup_skips`` and
    ``missing_files``. It never touches the filesystem.
    """
    text = text or ""
    booted = WORLD_RENDERED_MARKER in text
    captain_down = any(marker in text for marker in CAPTAIN_DOWN_MARKERS)
    abort_markers = [marker for marker in ABORT_TEXT_MARKERS if marker in text]
    for line in text.splitlines():
        match = SETUP_ABORT_RE.search(line)
        if match:
            abort_markers.append(f"P2_SETUP_ABORT {match.group(1)} {match.group(2)}")

    bound = {}
    resolved = set()
    species_counts = Counter()
    setup_skips = []
    missing_files = []

    def mark(uid, species):
        # A real bind/ready marker outranks an earlier unresolved uid; each
        # distinct bound uid counts once even when several markers name it.
        if not uid or (uid in bound and bound[uid] is not None):
            return
        bound[uid] = species
        if species:
            species_counts[species] += 1

    for line in text.splitlines():
        skip = SETUP_SKIP_RE.search(line)
        if skip:
            setup_skips.append({"species": skip.group(1), "reason": skip.group(2)})
        if MISSING_FILE_RE.search(line):
            missing_files.append(line.strip())

        ready = ENEMY_READY_RE.search(line)
        if ready:
            mark(int(ready.group(2)), ready.group(1))
            continue
        mamuta = MAMUTA_READY_RE.search(line)
        if mamuta:
            mark(int(mamuta.group(1)), "Miulin")
            continue
        batch2 = BATCH2_BIND_RE.search(line)
        if batch2:
            mark(int(batch2.group(1)), batch2.group(2).rsplit("|", 1)[-1])
            continue
        generic = GENERIC_BIND_RE.search(line)
        if generic:
            source = SOURCE_ID_RE.search(line)
            species = SOURCE_ENUM.get(int(source.group(1))) if source else None
            mark(int(generic.group(2)), species)
            continue
        generated = GENERATED_PLACEMENT_RE.search(line)
        if generated:
            mark(int(generated.group(2)), None)
            continue
        # Resolution/placement evidence alone is not a bind.
        resolve = SEED_RESOLVE_RE.search(line)
        if resolve and int(resolve.group(2)):
            resolved.add(int(resolve.group(2)))
        slot = PLACEMENT_SLOT_RE.search(line)
        if slot and int(slot.group(2)):
            resolved.add(int(slot.group(2)))

    return {
        "booted": booted,
        "aborted": bool(abort_markers),
        "abort_markers": abort_markers,
        "captain_down": captain_down,
        "bound": bound,
        "resolved": resolved,
        "species_counts": dict(species_counts),
        "setup_skips": setup_skips,
        "missing_files": missing_files,
    }


def load_placement_slots(path=PLACEMENT_DOC):
    """Return ``{uid_str: slot_record}`` from the accepted-placement document."""
    document = json.loads(Path(path).read_text(encoding="utf-8"))
    return {str(slot["uid"]): slot for slot in document["slots"]}


def expected_bindings(manifest, slots, start_day=START_DAY):
    """Seed bindings loaded at the start day: ``hope_`` slots active by then."""
    expected = []
    for binding in manifest.get("p2_layout", {}).get("bindings", []):
        slot = slots.get(str(binding["target"]))
        if slot is None:
            continue
        if not str(slot.get("label", "")).startswith("hope_"):
            continue
        if int(slot.get("first_day", 1)) > start_day:
            continue
        expected.append({
            "target": str(binding["target"]),
            "label": slot.get("label"),
            "source_id": binding["source_id"],
            "enum_name": binding["enum_name"],
            "first_day": int(slot.get("first_day", 1)),
        })
    return expected


def evaluate(parsed, expected):
    """Combine a parsed log with the expected loaded-area bindings.

    A binding counts as bound when any bind/ready marker names its target uid.
    ``ok`` is False on an abort, a missing boot, a captain-down marker, or a
    loaded-area binding with no marker.
    """
    rows = []
    missing = []
    species_binds = Counter()
    by_uid = parsed.get("bound", {})
    for binding in expected:
        uid = int(binding["target"])
        is_bound = uid in by_uid
        species = by_uid.get(uid) or binding["enum_name"]
        if is_bound:
            species_binds[species] += 1
        else:
            missing.append(binding)
        rows.append(dict(binding, bound=is_bound, bound_species=by_uid.get(uid)))
    ok = (parsed["booted"] and not parsed["aborted"] and not parsed["captain_down"]
          and not missing)
    return {
        "ok": ok,
        "expected": rows,
        "missing_binds": missing,
        "species_binds": dict(species_binds),
    }


def _stage_content(args, work, manifest_path):
    """Reuse ``--content-root`` or build it with scripts/p2_prepare_content.py."""
    if args.content_root is not None:
        root = Path(args.content_root).resolve()
        if not (root / "prepared.json").is_file():
            raise SystemExit(f"--content-root has no prepared.json: {root}")
        return root
    out = work / "p2-content"
    if (out / "prepared.json").is_file():
        return out
    command = [sys.executable, str(ROOT / "scripts/p2_prepare_content.py"),
               "--iso", str(args.iso), "--out", str(out),
               "--seed-manifest", str(manifest_path),
               "--actors-out", str(work / "p2-actors.json"),
               "--species", "playable"]
    if args.research is not None:
        command += ["--research", str(args.research)]
    subprocess.run(command, check=True, cwd=str(ROOT))
    return out


def run_smoke(args):
    """Generate, stage, launch hidden, stop by PID, parse and return the report."""
    from randomizer.seed import generate
    from randomizer.runner import NativeRun
    from randomizer.session import Session
    from experimental.pikmin2_family_install import install_layout
    from scripts.p2_prepare_content import actor_bindings_for_manifest

    exe = Path(args.exe).resolve(strict=True)
    assets = Path(args.assets).resolve()
    if not (assets / "dataDir/stages").is_dir():
        raise SystemExit(f"--assets must contain dataDir/stages: {assets}")
    work = Path(args.work_dir).resolve()
    work.mkdir(parents=True, exist_ok=True)
    out = Path(args.out).resolve()

    manifest = generate(args.seed, p2_enemies=True, p2_species="playable")
    manifest_path = work / "seed-manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    actors = actor_bindings_for_manifest(manifest)
    (work / "p2-actors.json").write_text(
        json.dumps(actors, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    content_root = _stage_content(args, work, manifest_path)

    session_dir = Path(args.session_dir).resolve()
    if session_dir.exists():
        shutil.rmtree(session_dir, ignore_errors=True)
    session = Session(manifest, session_dir)
    run = NativeRun(session)
    install_layout(run.directory, manifest["p2_layout"], content_root,
                   actor_bindings=actors, retail_assets=assets,
                   cache_dir=session.directory / "p2-content-cache")

    env = dict(os.environ)
    env["PIKMIN_RANDOMIZER_TEST_BACKGROUND"] = "1"
    env["SDL_AUDIODRIVER"] = "dummy"
    env["PYTHONUTF8"] = "1"
    env["PATH"] = MINGW_BIN + os.pathsep + env.get("PATH", "")
    startup = subprocess.STARTUPINFO()
    startup.dwFlags |= subprocess.STARTF_USESHOWWINDOW
    startup.wShowWindow = 0
    log_path = run.directory / "native.log"

    stop = threading.Event()

    def keepalive():
        while not stop.is_set():
            try:
                run.poll()
                run.write_state(run.handshaken)
            except Exception:
                return
            time.sleep(0.1)

    timed_out = False
    with log_path.open("w", encoding="utf-8") as log:
        process = subprocess.Popen(
            [str(exe), "--randomizer-seed", str(run.bootstrap.resolve())],
            cwd=str(run.directory), env=env, stdout=log, stderr=subprocess.STDOUT,
            startupinfo=startup)
        thread = threading.Thread(target=keepalive, daemon=True)
        thread.start()
        deadline = time.monotonic() + args.seconds
        while time.monotonic() < deadline and process.poll() is None:
            time.sleep(0.2)
        timed_out = process.poll() is None
        if timed_out:
            process.terminate()
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=5)
        stop.set()

    text = log_path.read_text(encoding="utf-8", errors="replace")
    parsed = parse_native_log(text)
    if process.returncode not in (0, None) and not parsed["aborted"] and not timed_out:
        parsed["aborted"] = True
        parsed["abort_markers"].append(f"early exit {process.returncode}")
    slots = load_placement_slots()
    expected = expected_bindings(manifest, slots)
    result = evaluate(parsed, expected)
    if parsed["captain_down"]:
        outcome = "BLOCKED"
    elif result["ok"]:
        outcome = "PASS"
    else:
        outcome = "FAIL"

    report = {
        "schema": 1,
        "seed": args.seed,
        "exe": str(exe),
        "exe_sha256": _sha256(exe),
        "assets": str(assets),
        "content_root": str(content_root),
        "content_prepared_sha256": _sha256(content_root / "prepared.json"),
        "session_dir": str(session_dir),
        "run_dir": str(run.directory),
        "native_log": str(log_path),
        "native_log_sha256": _sha256(log_path),
        "seconds": args.seconds,
        "timed_out": timed_out,
        "exit_code": process.returncode,
        "booted": parsed["booted"],
        "aborted": parsed["aborted"],
        "abort_markers": parsed["abort_markers"],
        "outcome": outcome,
        "species_binds": result["species_binds"],
        "expected_bindings": result["expected"],
        "missing_binds": result["missing_binds"],
        "marker_species": parsed["species_counts"],
        "setup_skips": parsed["setup_skips"],
        "missing_files": parsed["missing_files"][:20],
        "captain_safety": {
            "policy": "unprotected",
            "guard_source": str(GUARD_SOURCE),
            "guard_source_sha256": _sha256(GUARD_SOURCE) if GUARD_SOURCE.is_file() else None,
            "captain_down": parsed["captain_down"],
            "note": ("no input, no captain-damage test; captain parked at the start "
                     "area. Any captain-down marker blocks the run."),
        },
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
    }
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--exe", type=Path, required=True,
                        help="native nectar.exe (read-only; never rebuilt here)")
    parser.add_argument("--seed", default="p2-campaign-smoke",
                        help="seed name (deterministic; default %(default)s)")
    parser.add_argument("--seconds", type=float, default=150.0,
                        help="bounded launch seconds before stop-by-PID (default %(default)s)")
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT,
                        help="JSON report path (default %(default)s)")
    parser.add_argument("--work-dir", type=Path, default=ROOT.parent / "run",
                        help="private staging directory (default %(default)s)")
    parser.add_argument("--session-dir", type=Path, default=DEFAULT_SESSION,
                        help="short session path; Windows 260-char limit (default %(default)s)")
    parser.add_argument("--assets", type=Path, default=DEFAULT_ASSETS,
                        help="P1 assets root with dataDir/stages (default %(default)s)")
    parser.add_argument("--content-root", type=Path, default=None,
                        help="reuse a prepared identity-keyed content root")
    parser.add_argument("--iso", type=Path, default=DEFAULT_ISO,
                        help="P2 retail ISO when staging content (default %(default)s)")
    parser.add_argument("--research", type=Path, default=None,
                        help="native/pikmin2-research checkout when staging content")
    args = parser.parse_args(argv)

    report = run_smoke(args)
    print(json.dumps({key: report[key] for key in
                      ("outcome", "booted", "aborted", "species_binds",
                       "missing_binds", "setup_skips")}, indent=2))
    if report["outcome"] == "BLOCKED":
        return 86
    return 0 if report["outcome"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
