"""P0 source-audit adapter for Awakening Wood (p2-overworld-forest, #149).

Concrete source-import preparation only. Reuses the existing
``stage_cave_links`` parser (no fork); never emits runtime placements.
Metadata already catalogued in docs/PIKMIN2_CONTENT_INVENTORY.json is treated
as baseline, not reimplemented. If ``user/Abe/stages.txt`` bytes are absent,
callers get the exact missing prerequisite instead of invented values.
"""

import hashlib
import json
from pathlib import Path

from experimental.pikmin2_regional_audit import stage_cave_links

SOURCE_PATH = "user/Abe/stages.txt"
COURSE = "forest"
LABEL = "Awakening Wood"
ISSUE = 149

REQUIRED_INVENTORY = (
    "terrain/collision/water",
    "generator day schedules and regrowth",
    "buried/enemy-held treasure",
    "Onions/ship/bridges/gates",
    "all cave entrances and return anchors",
)

# Runtime framework contracts that block P1/P2 (issue refs from the lane
# entry). P0 resolves none of them; they are reported, not claimed.
BLOCKERS = (
    {"issue": 128, "contract": "actor/asset source closure"},
    {"issue": 130, "contract": "actor/asset source closure"},
    {"issue": 131, "contract": "actor/asset source closure"},
    {"issue": 132, "contract": "surface days, saves and progression identity"},
    {"issue": 140, "contract": "actor/asset/species source closure"},
    {"issue": 144, "contract": "actor/asset/species source closure"},
    {"issue": 145, "contract": "actor/asset/species source closure"},
    {"issue": 146, "contract": "actor/asset/species source closure"},
)

MISSING_PREREQUISITE = (
    "Legal US Pikmin 2 disc image (GPVE01 rev 0) or an extracted "
    "'user/Abe/stages.txt' file decoded as shift_jis. Provide the file "
    "bytes to decode_forest(); nothing is staged from weighted definitions."
)


def sha256_bytes(data):
    if not isinstance(data, (bytes, bytearray)):
        raise ValueError("source bytes required")
    return hashlib.sha256(bytes(data)).hexdigest()


def decode_forest(stages_text):
    """Decode stages.txt text and return forest cave links.

    Reuses the existing parser (framing, counts, tag/filename validation).
    Raises ValueError on malformed input or when the forest course is absent.
    Returns links sorted by cave_table_index with original fields preserved.
    """
    if not isinstance(stages_text, str) or not stages_text.strip():
        raise ValueError("stages.txt text is missing or empty")
    links = stage_cave_links(stages_text)
    forest = [dict(link) for link in links if link.get("course_id") == COURSE]
    if not forest:
        raise ValueError("forest course missing from stages.txt")
    forest.sort(key=lambda link: link.get("cave_table_index", 0))
    return forest


def resource_closure(forest_links, stages_sha256=None, cave_hashes=None):
    """List every source file this entry needs, with hashes where known."""
    cave_hashes = dict(cave_hashes or {})
    closure = [dict(path=SOURCE_PATH, sha256=stages_sha256,
                    status="hashed" if stages_sha256 else "hash_unvalidated")]
    for link in forest_links:
        path = link["source_path"]
        digest = cave_hashes.get(path)
        closure.append(dict(path=path, sha256=digest,
                            status="hashed" if digest else "hash_unvalidated"))
    return closure


def build_manifest(stages_text, stages_sha256=None, cave_hashes=None):
    """Build the isolated P0 metadata packet for the forest course."""
    forest = decode_forest(stages_text)
    if stages_sha256 is not None:
        if not isinstance(stages_sha256, str) or len(stages_sha256) != 64:
            raise ValueError("stages_sha256 must be 64 hex chars")
    manifest = dict(
        schema=1,
        lane="p2-overworld-forest",
        course=COURSE,
        label=LABEL,
        issue=ISSUE,
        source=SOURCE_PATH,
        stages_sha256=stages_sha256,
        cave_count=len(forest),
        cave_links=[dict(link) for link in forest],
        required_inventory=[dict(item=item, status="baseline_catalogued")
                            for item in REQUIRED_INVENTORY],
        resource_closure=resource_closure(forest, stages_sha256, cave_hashes),
        blockers=[dict(entry) for entry in BLOCKERS],
        placement_policy=("no runtime placements emitted; weighted definitions "
                          "stay source data, never actor counts"),
        playable=False,
    )
    validate_manifest(manifest)
    return manifest


def validate_manifest(manifest):
    if not isinstance(manifest, dict):
        raise ValueError("manifest must be a dict")
    if manifest.get("schema") != 1:
        raise ValueError("unsupported manifest schema")
    if manifest.get("course") != COURSE or manifest.get("source") != SOURCE_PATH:
        raise ValueError("manifest course/source mismatch")
    links = manifest.get("cave_links")
    if not isinstance(links, list) or not links:
        raise ValueError("manifest needs at least one forest cave link")
    seen = set()
    for link in links:
        if link.get("course_id") != COURSE:
            raise ValueError("non-forest link in forest manifest")
        tag = link.get("cave_tag")
        path = link.get("source_path")
        if not tag or not path:
            raise ValueError("cave link missing tag/path")
        if tag in seen:
            raise ValueError("duplicate cave tag in manifest")
        seen.add(tag)
        if not path.startswith("user/Mukki/mapunits/caveinfo/"):
            raise ValueError("unexpected cave source path: " + str(path))
    if manifest.get("cave_count") != len(links):
        raise ValueError("cave_count disagrees with cave_links")
    inventory = manifest.get("required_inventory")
    if [row.get("item") for row in inventory] != list(REQUIRED_INVENTORY):
        raise ValueError("required_inventory mismatch")
    if manifest.get("playable") is not False:
        raise ValueError("P0 manifest must not claim playability")
    return True


DEFAULT_ISO = Path("C:/Users/alari/Downloads/PIKMIN2 for GAMECUBE.iso")


def locate_source(iso_path=None):
    """Locate the legal retail ISO, or report the exact prerequisite."""
    iso = Path(iso_path) if iso_path is not None else DEFAULT_ISO
    if not iso.is_file():
        return {"available": False, "iso": None,
                "prerequisite": MISSING_PREREQUISITE}
    return {"available": True, "iso": str(iso), "prerequisite": None}


def decode_source_file(path):
    """Decode a real extracted stages.txt file into a hashed manifest.

    Reads raw bytes, records the observed input sha256, decodes shift_jis
    with the shared framing and builds the manifest. Raises ValueError on
    missing/unreadable input or malformed content.
    """
    raw = Path(path).read_bytes()
    return build_manifest(raw.decode("shift_jis"), sha256_bytes(raw))


def missing_prerequisite():
    return MISSING_PREREQUISITE


def main(argv=None):
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--stages", type=Path, default=None,
                        help="path to extracted user/Abe/stages.txt")
    parser.add_argument("--output", type=Path, default=None,
                        help="write manifest JSON here (otherwise stdout)")
    parser.add_argument("--p1-run", type=Path, default=None,
                        help="stage the manifest into DIR and drive P1 boundaries")
    args = parser.parse_args(argv)
    if args.stages is None:
        raise SystemExit("missing prerequisite: " + MISSING_PREREQUISITE)
    raw = args.stages.read_bytes()
    text = raw.decode("shift_jis")
    manifest = build_manifest(text, sha256_bytes(raw))
    if args.p1_run is not None:
        staged = stage_p1_run(manifest, args.p1_run)
        report = drive_session_boundaries(args.p1_run)
        (args.p1_run / "boundary-report.json").write_text(
            json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        for name, result in report["boundaries"].items():
            print("%s: %s" % (name, result["verdict"]))
        print("contract_source=%s" % report["contract_source"])
        return 0
    payload = json.dumps(manifest, indent=2, sort_keys=True) + "\n"
    if args.output is None:
        print(payload, end="")
    else:
        args.output.write_text(payload, encoding="utf-8")
    return 0



# ---------------------------------------------------------------------------
# P1 runtime import path (lane p2-overworld-forest-p1-surface-session, #149).
#
# Consumes the integrated generic contract surface-session-provider-contract
# (#132, schema p2-surface-session-1) WITHOUT forking or vendoring it. The
# loader resolves the checker from the live checkout when integrated there,
# else byte-exact from the canonical git object store at the pinned
# content-line commit (blob hash verified). When neither source can supply
# it, callers get the exact pin gap (P1GapError), never invented semantics.
# ---------------------------------------------------------------------------

import copy
import subprocess
import types

CONTENT_PIN = "3a6b34e38075a60c7f60de5e2add768e5efdc8b4"
CONTRACT_PATH = "experimental/pikmin2_surface_session_contract.py"
CONTRACT_BLOB_SHA256 = "3ba71fe92a8989180358cbb1617cf040e3ebf9a25aac1754cec25a1e192460f1"
CONTRACT_SCHEMA = "p2-surface-session-1"
CANONICAL_ROOT = Path("C:/Users/alari/pikmin-randomizer")

P1_MISSING_CONTRACT = (
    "p2-surface-session-1 checker unavailable: not integrated in this "
    "checkout, and content pin 3a6b34e38075a60c7f60de5e2add768e5efdc8b4 "
    "cannot supply experimental/pikmin2_surface_session_contract.py "
    "(blob 3ba71fe92a8989180358cbb1617cf040e3ebf9a25aac1754cec25a1e192460f1)."
)


class P1GapError(ValueError):
    """A P1 prerequisite pin cannot be supplied; nothing is invented."""


def load_surface_contract():
    """Resolve the real p2-surface-session-1 checker module (never a fork).

    Returns (module, source) where source is "tree" or "pin:<commit>".
    Raises P1GapError with exact pins when neither source can supply it.
    """
    try:
        from experimental import pikmin2_surface_session_contract as live
    except ImportError:
        live = None
    if live is not None and getattr(live, "SCHEMA", None) == CONTRACT_SCHEMA:
        return live, "tree"
    proc = subprocess.run(
        ["git", "-C", str(CANONICAL_ROOT), "show",
         "%s:%s" % (CONTENT_PIN, CONTRACT_PATH)],
        capture_output=True)
    if proc.returncode != 0:
        raise P1GapError(P1_MISSING_CONTRACT)
    blob = proc.stdout
    if sha256_bytes(blob) != CONTRACT_BLOB_SHA256:
        raise P1GapError(
            "surface contract bytes drifted at pin %s; refusing substitute "
            "semantics." % CONTENT_PIN)
    module = types.ModuleType("pikmin2_surface_session_contract_pinned")
    exec(compile(blob, CONTRACT_PATH, "exec"), module.__dict__)
    if getattr(module, "SCHEMA", None) != CONTRACT_SCHEMA:
        raise P1GapError("pinned contract has unexpected schema")
    return module, "pin:" + CONTENT_PIN


def boundary_scripts(manifest):
    """Event scripts per boundary, grounded in manifest cave links."""
    validate_manifest(manifest)
    first_tag = manifest["cave_links"][0]["cave_tag"]
    return {
        "day_transition": [
            {"type": "begin_day", "day": 2},
            {"type": "sunset", "time_of_day": 1.0},
            {"type": "save"},
            {"type": "reload"},
            {"type": "begin_day", "day": 3},
        ],
        "receipt_replay": [
            {"type": "deliver_receipt", "identity": "cave:" + first_tag,
             "slot": "surface:1", "encounter": "surface"},
            {"type": "deliver_receipt", "identity": "cave:" + first_tag,
             "slot": "surface:1", "encounter": "surface"},
        ],
        "exit_reentry": [
            {"type": "exit_cave"},
            {"type": "enter_cave", "cave_id": first_tag, "floor": 1},
            {"type": "exit_cave", "cave_pokos": 0},
            {"type": "enter_cave", "cave_id": first_tag, "floor": 1},
        ],
    }


_EXPECTED_STEPS = {
    "day_transition": [True, True, True, True, True],
    "receipt_replay": [True, False],
    "exit_reentry": [False, True, True, True],
}


def stage_p1_run(manifest, run_dir):
    """Stage a validated P0 manifest into a private P1 run layout."""
    validate_manifest(manifest)
    checker, source = load_surface_contract()
    run = Path(run_dir)
    run.mkdir(parents=True, exist_ok=True)
    seed = checker.blank_session(course=COURSE, day=1)
    scripts = boundary_scripts(manifest)
    manifest_path = run / "manifest.json"
    manifest_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    seed_path = run / "session-seed.json"
    seed_path.write_text(
        json.dumps(seed, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    bounds_path = run / "boundaries.json"
    bounds_path.write_text(
        json.dumps(scripts, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return {
        "run_dir": str(run),
        "manifest": str(manifest_path),
        "manifest_sha256": sha256_bytes(manifest_path.read_bytes()),
        "seed": str(seed_path),
        "seed_sha256": sha256_bytes(seed_path.read_bytes()),
        "boundaries": str(bounds_path),
        "boundaries_sha256": sha256_bytes(bounds_path.read_bytes()),
        "contract_source": source,
        "contract_schema": checker.SCHEMA,
    }


def drive_session_boundaries(run_dir):
    """Drive the real checker over staged boundaries; report verdicts.

    Existing checker behavior and missing native integration are reported
    separately: a boundary passes only when every observed step matches the
    contract-expected outcome; native-backed requests are recorded missing.
    """
    checker, source = load_surface_contract()
    run = Path(run_dir)
    try:
        manifest = json.loads((run / "manifest.json").read_text(encoding="utf-8"))
        seed = json.loads((run / "session-seed.json").read_text(encoding="utf-8"))
        scripts = json.loads((run / "boundaries.json").read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise P1GapError("private run layout unreadable at %s: %s" % (run, exc))
    validate_manifest(manifest)
    report = {"contract_source": source, "contract_schema": checker.SCHEMA,
              "boundaries": {}, "missing_integration": {}, "wake": {}}
    for name, events in scripts.items():
        expected = _EXPECTED_STEPS.get(name)
        if expected is None or len(expected) != len(events):
            raise P1GapError("boundary script %r is not contract-shaped" % name)
        state = copy.deepcopy(seed)
        steps = []
        for event in events:
            ok, new_state, reason = checker.check_transition(state, event)
            steps.append({"event": event, "ok": ok, "reason": reason})
            if ok:
                state = new_state
        observed = [step["ok"] for step in steps]
        verdict = ("pass" if observed == expected
                   else "FAIL: observed %s, contract expects %s" % (observed, expected))
        report["boundaries"][name] = {"steps": steps, "verdict": verdict}
    for name in checker.MISSING_INTEGRATION:
        ok, _ignored, reason = checker.request_integration(name)
        report["missing_integration"][name] = {"ok": ok, "reason": reason}
    wake = checker.wake_criteria(COURSE)
    wake["course_record_decoded"] = True
    wake["cave_entrances_known"] = True
    report["wake"] = wake
    return report

if __name__ == "__main__":
    raise SystemExit(main())
