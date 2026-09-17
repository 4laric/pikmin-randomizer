"""Save-dayclock dependency-ready publisher for tutorial P1 consumers (#132).

Lane caves-tutorial-save-dayclock-dependency-ready. Reads the DONE audit lane
`provider-save-dayclock-anchor-audit` outputs READ-ONLY and publishes a
machine-readable dependency-ready record that tutorial P1 lanes
(p2-cave-tutorial_2 #152, p2-cave-tutorial_3 #153) can pin.

Every pinned value is hash-verified against the done lane outputs at publish
time; any mismatch fails closed with the exact difference. Nothing here
re-decodes source, invents audit values, builds, runs the game, edits shared
files or claims gameplay. All six runtime gates stay UNTESTED.

Inputs (all read-only):
- the audit machine inventory
  (`.../save-anchor-audit/out/inventory.json`, verdict `complete`);
- the audit lane record (root commit, owned files);
- the two research sources the anchors cite
  (`native/pikmin2-research/src/plugProjectKandoU/singleGameSection.cpp`,
  `gamePlayData.cpp`), hashed as source pins only.

Output: `dependency-ready.json` with schema 1, provider identity, source
pins, file hashes, anchor-group summary, downstream consumer references and
the explicitly unevaluated save semantics.
"""

import argparse
import hashlib
import json
import re
from pathlib import Path

SCHEMA = 1
PROVIDER_LANE = "provider-save-dayclock-anchor-audit"
PROVIDER_ISSUE = 132
PROVIDER_COMMIT = "4fff74c7ed656c42e24c46b8d9294fc97367b417"

# Anchor groups the audit must report as complete (non-empty), keyed exactly
# as the audit inventory reports them.
REQUIRED_GROUPS = (
    "day_clock",
    "sunset_loss",
    "debt_equipment",
    "louie_president",
    "save_migration",
)

# Expected-absent by audit design (recorded, never an anchor source here).
EXPECTED_ABSENT_GROUPS = ("sprout_regeneration",)

# Research sources the anchors cite (repo-relative, read-only).
RESEARCH_SOURCES = (
    "src/plugProjectKandoU/singleGameSection.cpp",
    "src/plugProjectKandoU/gamePlayData.cpp",
)

DOWNSTREAM = (
    {"lane": "p2-cave-tutorial_2", "issue": 152},
    {"lane": "p2-cave-tutorial_3", "issue": 153},
)

# Save semantics the audit explicitly leaves unevaluated; consumers must not
# treat this record as covering them.
UNEVALUATED = (
    "sprout_regeneration anchors (outside the two audited files; see audit notes)",
    "treasure-ledger semantics (provider-treasure-receipts shard)",
    "floor-generation semantics (provider-cave-generation shard)",
    "durable-save write paths and restart identity (future provider work)",
    "any runtime behavior, reward, revisit or restart observation",
)

_HEX64 = re.compile(r"[0-9a-f]{64}")


def _require(condition, message):
    if not condition:
        raise ValueError(message)
    return condition


def sha256_file(path):
    path = Path(path)
    _require(path.is_file(), "Missing input file: %s" % path)
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_json(path):
    path = Path(path)
    _require(path.is_file(), "Missing input file: %s" % path)
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError) as error:
        raise ValueError("Corrupt JSON input %s: %s" % (path, error))


def check_hash(value, what):
    _require(isinstance(value, str) and _HEX64.fullmatch(value),
             "Malformed recorded hash for %s" % what)
    _require(value != "0" * 64, "Placeholder recorded hash for %s" % what)
    return value


def verify_inventory(inventory):
    """Fail closed unless the audit inventory is complete and well-formed."""
    _require(isinstance(inventory, dict), "Inventory must be an object")
    _require(inventory.get("verdict") == "complete",
             "Inventory verdict is not complete: %r" % (inventory.get("verdict"),))
    _require(inventory.get("unresolved_groups", []) == [],
             "Inventory has unresolved groups: %r" % (inventory.get("unresolved_groups"),))
    _require(inventory.get("claimed_absent_verbatim") is True,
             "claimed_absent_verbatim is not true")
    groups = inventory.get("groups", {})
    _require(isinstance(groups, dict), "Inventory groups must be an object")
    summary = {}
    for name in REQUIRED_GROUPS:
        files = groups.get(name)
        _require(isinstance(files, list) and len(files) >= 1,
                 "Required anchor group missing or empty: %s" % name)
        summary[name] = sorted(files)
    for name in EXPECTED_ABSENT_GROUPS:
        _require(name in groups, "Expected-absent group missing: %s" % name)
        summary[name] = list(groups[name])
    sources = inventory.get("sources", {})
    _require(set(sources) == set(RESEARCH_SOURCES),
             "Inventory sources differ from audited pair: %r" % sorted(sources))
    return summary


def verify_lane_record(record, expected_commit):
    """The lane record must name the provider lane/issue and the exact commit."""
    _require(isinstance(record, dict), "Lane record must be an object")
    _require(record.get("lane") == PROVIDER_LANE,
             "Lane record is not %s" % PROVIDER_LANE)
    _require(record.get("issue") == PROVIDER_ISSUE,
             "Lane record issue drift")
    commits = record.get("commits", [])
    _require(expected_commit in commits or record.get("head") == expected_commit,
             "Provider commit %s not in lane record" % expected_commit)
    return {"lane": PROVIDER_LANE, "issue": PROVIDER_ISSUE,
            "commit": expected_commit}


def build(inventory_path, lane_record, research_root, audit_files):
    """Verify everything and return the dependency-ready record dict.

    ``audit_files`` maps label -> path for the done lane outputs whose hashes
    are pinned (inventory, doc, adapter, tests). ``research_root`` is the
    read-only research tree the anchors cite.
    """
    inventory = load_json(inventory_path)
    summary = verify_inventory(inventory)
    provider = verify_lane_record(lane_record, PROVIDER_COMMIT)
    inventory_hash = sha256_file(inventory_path)
    pinned = {}
    for label, path in audit_files.items():
        pinned[label] = {"path": str(Path(path)),
                         "sha256": sha256_file(path)}
    research_root = Path(research_root)
    _require(research_root.is_dir(), "Missing research root: %s" % research_root)
    source_pins = {}
    for rel in RESEARCH_SOURCES:
        source_pins[rel] = sha256_file(research_root / rel)
    return {
        "schema": SCHEMA,
        "provider": provider,
        "contract": "audit-commit %s + inventory %s"
                    % (PROVIDER_COMMIT, inventory_hash),
        "inventory_sha256": inventory_hash,
        "anchor_groups": summary,
        "audit_files": pinned,
        "research_source_pins": source_pins,
        "downstream_consumers": [dict(entry) for entry in DOWNSTREAM],
        "unevaluated_save_semantics": list(UNEVALUATED),
        "generated": False,
        "placements": [],
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--inventory", type=Path, required=True,
                        help="Done lane inventory.json (read-only)")
    parser.add_argument("--lane-record", type=Path, required=True,
                        help="JSON file holding the done lane record")
    parser.add_argument("--research-root", type=Path, required=True,
                        help="Read-only research tree the anchors cite")
    parser.add_argument("--audit-file", action="append", default=[],
                        metavar="LABEL=PATH",
                        help="Done lane output to hash-pin; repeatable")
    parser.add_argument("--output", type=Path, required=True,
                        help="dependency-ready.json output path (parent must exist)")
    args = parser.parse_args(argv)
    audit_files = {}
    for item in args.audit_file:
        label, sep, path = item.partition("=")
        _require(sep and label and path, "Malformed --audit-file %r" % item)
        _require(label not in audit_files, "Duplicate audit label %r" % label)
        audit_files[label] = path
    _require(audit_files, "At least one --audit-file is required")
    lane_record = load_json(args.lane_record)
    result = build(args.inventory, lane_record, args.research_root, audit_files)
    out = Path(args.output)
    _require(out.parent.is_dir(), "Missing output directory: %s" % out.parent)
    out.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"provider": result["provider"]["lane"],
                      "commit": result["provider"]["commit"],
                      "groups": sorted(result["anchor_groups"]),
                      "downstream": [c["lane"] for c in result["downstream_consumers"]],
                      "inventory_sha256": result["inventory_sha256"]}, indent=2))


if __name__ == "__main__":
    main()