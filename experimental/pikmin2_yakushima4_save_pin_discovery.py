"""Yakushima4 save/persistence pin-discovery adapter (issue #779).

Machine-readable pin record naming the exact #132 save/persistence
artifacts yakushima4 floor-1+ needs, with file/commit citations from the
#161 floor-1 evidence and the landed #132 contracts, plus the concrete
owner and first bounded slice with downstream consumer #161.

Usage:
  python pikmin2_yakushima4_save_pin_discovery.py --emit
  python pikmin2_yakushima4_save_pin_discovery.py --check [record.json]

Markers:
  P2_YAKUSHIMA4_SAVEPIN_OK sections=<n>
  P2_YAKUSHIMA4_SAVEPIN_REFUSED reason=<code>

Exit 0 on valid, 2 on refusal. Read-only; stdlib only.
"""
import json
import re
import sys

HEX40 = re.compile(r"^[0-9a-f]{40}$")
HEX64 = re.compile(r"^[0-9a-f]{64}$")

REQUIRED_TOP = (
    "schema", "consumer", "floor1_evidence", "contracts",
    "needed_slice", "owner", "first_slice",
)
REQUIRED_CONTRACTS = ("cave_save", "dayclock_anchors", "surface_session")
OWNED_PREFIXES = ("experimental/", "tests/", "docs/", "native/tools/")
PROVIDER_CATALOG_KEYS = ("save-progression",)


def pin_record():
    """The verified pin record. Every citation was read, never invented."""
    return {
        "schema": "p2-yakushima4-savepin-1",
        "consumer": 161,
        "floor1_evidence": {
            "lane": "shard-caves-yakushima-yakushima4-p1",
            "state": "blocked",
            "validation_log": "output/workflow/autofill/planning-shards/caves-yakushima/prepared/yakushima4-p1/out/validation-gen12.log",
            "validation_sha256": "43675548da11239f1f4f737cae12951735fcd529d18315984b72668e5d5d9e91",
            "root_head": "f446faee63cc8c48da8d141aff3fdf953f4cb2b4",
            "native_head": "88188a1e3d687132baf4c2ab7c01b3c752ef4500",
            "markers": ["P2_YAKUSHIMA4_TRAVERSAL_PASS rooms=8 links=36"],
        },
        "contracts": {
            "cave_save": {
                "doc": "output/workflow/autofill/planning/dungeons/prepared/cave-save-contract-review-root/docs/PIKMIN2_CAVE_SAVE_PROVIDER_REVIEW.md",
                "worktree_commit": "8aaf6cf67abaf20de1568a9559ee53b516ee084b",
                "artifacts": [
                    "native/pc_port/pc_p2_cave.cpp:123-169 pc_p2_cave_checkpoint write sequence",
                    "engine/pc_port/pc_p2_cave_transfer.h:17-121 transfer wire format",
                    "engine/tools/test_p2_cave_transfer.cpp transfer-schema asserts",
                ],
            },
            "dayclock_anchors": {
                "doc": "output/workflow/autofill/planning-shards/provider-save-progression/prepared/save-anchor-audit-root/docs/PIKMIN2_SAVE_DAYCLOCK_ANCHOR_AUDIT.md",
                "worktree_commit": "4fff74c7ed656c42e24c46b8d9294fc97367b417",
                "inventory": "output/workflow/autofill/planning-shards/provider-save-progression/prepared/save-anchor-audit/out/inventory.json",
                "artifacts": [
                    "singleGameSection.cpp:216 advanceDayCount",
                    "singleGameSection.cpp:183/209 CaveDayEndState init/exec",
                    "mCaveSaveData/mCurrentCaveID/mCurrentFloor floor anchors",
                ],
            },
            "surface_session": {
                "doc": "output/workflow/prerequisites/surface-session-provider-contract/root/docs/PIKMIN2_SURFACE_SESSION_CONTRACT.md",
                "worktree_commit": "7b6d25df49749fa22f583ddc74773d5fdbd65ea0",
                "artifacts": [
                    "schema p2-surface-session-1 transition checker",
                    "save-after-sunset plus course-matched reload rules",
                ],
            },
        },
        "needed_slice": [
            "checkpoint write/read/validate at yakushima4 floor boundaries per the cave-save contract",
            "floor/roster state that must persist: floor id, living-squad census, NAV topology ref",
            "day/progression anchors: CaveDayEndState, mCurrentCaveID/mCurrentFloor, day count",
        ],
        "owner": {"kind": "new-lane", "lane": "yakushima4-save-persistence-slice",
                  "reason": "no live provider-save-progression implementation lane exists"},
        "first_slice": {
            "owned_files": [
                "experimental/pikmin2_yakushima4_save_persistence.py",
                "tests/test_pikmin2_yakushima4_save_persistence.py",
                "docs/PIKMIN2_YAKUSHIMA4_SAVE_PERSISTENCE.md",
            ],
            "root_base": "36b868391e62cccf37d992aa2f796f3cc9c6dc31",
            "native_base": "88188a1e3d687132baf4c2ab7c01b3c752ef4500",
            "downstream": 161,
        },
        "provider": "save-progression",
        "gates": "all six runtime gates UNTESTED",
    }


def validate_pin_record(rec):
    """Return a list of error codes; empty means valid (fail-closed)."""
    errors = []
    if not isinstance(rec, dict):
        return ["not-a-record"]
    for key in REQUIRED_TOP:
        if key not in rec:
            errors.append("missing-section:" + key)
    if errors:
        return errors
    if rec.get("schema") != "p2-yakushima4-savepin-1":
        errors.append("bad-schema")
    if rec.get("consumer") != 161:
        errors.append("bad-consumer")
    ev = rec.get("floor1_evidence") or {}
    if not HEX64.match(str(ev.get("validation_sha256", ""))):
        errors.append("bad-evidence-hash")
    for pin in (ev.get("root_head"), ev.get("native_head")):
        if not HEX40.match(str(pin or "")):
            errors.append("bad-evidence-pin")
    contracts = rec.get("contracts") or {}
    for name in REQUIRED_CONTRACTS:
        c = contracts.get(name)
        if not isinstance(c, dict):
            errors.append("missing-contract:" + name)
            continue
        if not c.get("doc") or not c.get("artifacts"):
            errors.append("thin-contract:" + name)
        if not HEX40.match(str(c.get("worktree_commit", ""))):
            errors.append("bad-contract-pin:" + name)
    if not rec.get("needed_slice"):
        errors.append("empty-needed-slice")
    owner = rec.get("owner") or {}
    if owner.get("kind") not in ("live-lane", "new-lane"):
        errors.append("absent-provider")
    if not owner.get("lane"):
        errors.append("absent-provider")
    fs = rec.get("first_slice") or {}
    files = fs.get("owned_files") or []
    if len(files) < 3 or not all(
            isinstance(f, str) and f.startswith(OWNED_PREFIXES) for f in files):
        errors.append("bad-first-slice-files")
    for pin in (fs.get("root_base"), fs.get("native_base")):
        if not HEX40.match(str(pin or "")):
            errors.append("bad-first-slice-pin")
    if fs.get("downstream") != 161:
        errors.append("bad-first-slice-consumer")
    if rec.get("provider") not in PROVIDER_CATALOG_KEYS:
        errors.append("off-catalog-provider")
    return errors


def main(argv):
    if len(argv) < 2 or argv[1] not in ("--emit", "--check"):
        print("P2_YAKUSHIMA4_SAVEPIN_REFUSED reason=usage")
        return 2
    if argv[1] == "--emit":
        print(json.dumps(pin_record(), indent=1))
        return 0
    if len(argv) > 2:
        try:
            with open(argv[2], "r", encoding="utf-8") as fh:
                rec = json.load(fh)
        except (OSError, ValueError):
            print("P2_YAKUSHIMA4_SAVEPIN_REFUSED reason=malformed-input")
            return 2
    else:
        rec = pin_record()
    errors = validate_pin_record(rec)
    if errors:
        print("P2_YAKUSHIMA4_SAVEPIN_REFUSED reason=" + errors[0])
        return 2
    print("P2_YAKUSHIMA4_SAVEPIN_OK sections=%d" % len(REQUIRED_TOP))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
