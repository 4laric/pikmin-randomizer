"""Challenge-2 contract consumer: readiness map + first P1 slice (#137).

Review-only tool (lane shard-challenge-2-contract-consumer). Consumes the
published P2 challenge framework contract (issue #136) for exactly the seven
challenge-2 stages (lowercase stage-key sha256 mod 4 == 2) instead of
inventing prerequisites:

- decode_partition(text, contract): decode the stage table THROUGH the
  contract parser (no fork), keep exactly the seven partition keys;
- cross_check(stages, inventory, contract): delegate to the contract
  cross-checker, restricted to partition mismatches;
- readiness_map(stages, contract): per-stage squads/sprays/timers/floors
  plus the unsupported semantics the contract itself names;
- first_slice(stages): deterministic smallest single-floor slice
  (fewest floors, then smallest timer total, then lowest ui_index);
- packet(...): machine-readable consumer map with sha256.

All six runtime gates stay UNTESTED; no playable claim; no manifest write.
Stdlib only.
"""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path

LANE = "shard-challenge-2-contract-consumer"
ISSUE = 137
CONTRACT_ISSUE = 136

PARTITION_KEYS = (
    "ch_ABEM_LeafChappy",
    "ch_MAT_conc_cave",
    "ch_MAT_flier",
    "ch_MAT_limited_time",
    "ch_MAT_t_hunter_hana",
    "ch_MUKI_bigfoot",
    "ch_MUKI_metal",
)

FIRST_SLICE_OWNERS = {
    "host_mode": "new framework lane (to dispatch; routed to #570, never duplicated here)",
    "generation_holes": "#129",
    "actors": "#130/#131",
    "saves_unlocks": "#132",
    "treasure": "#140",
    "stage_content": "challenge-2 P0 lanes (all seven done)",
}


class ConsumerError(ValueError):
    """Strict failure of the contract-consumption boundary."""


def load_contract(module_path=None):
    """Import the published framework contract artifact (no parser fork).

    module_path optionally points at an alternate contract file (tests);
    the default resolves the pinned in-tree artifact next to this module.
    """
    if module_path is None:
        module_path = Path(__file__).resolve().parent / "pikmin2_challenge_framework_contract.py"
    else:
        module_path = Path(module_path)
    if not module_path.is_file():
        raise ConsumerError("missing contract artifact: %s" % module_path)
    spec = importlib.util.spec_from_file_location("challenge_framework_contract", module_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    missing = [n for n in ("parse_stage_table", "cross_check_inventory", "framework_providers")
               if not callable(getattr(module, n, None))]
    if missing:
        raise ConsumerError("contract artifact lacks API: %s" % ", ".join(missing))
    return module


def _require(condition, message):
    if not condition:
        raise ConsumerError(message)


def decode_partition(text, contract):
    """Decode the stage table through the contract parser; keep exactly us."""
    stages = contract.parse_stage_table(text)
    rows = [s for s in stages if s.get("cave_id") in PARTITION_KEYS]
    have = sorted(s["cave_id"] for s in rows)
    _require(have == sorted(PARTITION_KEYS),
             "partition keys mismatch: have %r" % (have,))
    return sorted(rows, key=lambda s: s["cave_id"])


def cross_check(stages, inventory, contract):
    """Delegate to the contract cross-checker; partition mismatches only."""
    mismatches = contract.cross_check_inventory(stages, inventory)
    mine = [m for m in mismatches if m.get("cave_id") in PARTITION_KEYS]
    return mine


def _populations(row):
    return [{"color": color, "maturity": maturity, "count": count}
            for color, triple in enumerate(row.get("roster", []))
            for maturity, count in enumerate(triple)]


def readiness_map(stages, contract):
    """Per-stage readiness from decoded fields plus contract-named gaps."""
    providers = contract.framework_providers()
    unsupported = sorted(providers.get("missing", {}).keys())
    table = []
    for stage in stages:
        blockers = []
        pops = _populations(stage)
        if not any(p["count"] > 0 for p in pops):
            blockers.append("empty starting squad")
        timers = stage.get("floor_seconds", [])
        if len(timers) != stage.get("floors"):
            blockers.append("timer/floor count mismatch")
        if any(not isinstance(v, (int, float)) or v <= 0 for v in timers):
            blockers.append("non-positive floor timer")
        for key in ("bitter_sprays", "spicy_sprays"):
            value = stage.get(key)
            if not isinstance(value, int) or value < 0:
                blockers.append("bad %s" % key)
        table.append({"cave_id": stage["cave_id"], "floors": stage["floors"],
                      "timer_total": sum(timers),
                      "starting_pikmin_total": sum(p["count"] for p in pops),
                      "ready": not blockers, "blockers": blockers,
                      "unsupported_semantics": unsupported})
    return table


def first_slice(stages):
    """Deterministic smallest single-floor slice: fewest floors, then
    smallest timer total, then lowest ui_index. Returns the slice dict."""
    _require(bool(stages), "no stages to choose from")
    pick = min(stages, key=lambda s: (s["floors"], sum(s["floor_seconds"]),
                                      s["ui_index"]))
    return {"cave_id": pick["cave_id"], "floors": pick["floors"],
            "timer_total": sum(pick["floor_seconds"]),
            "owners": dict(FIRST_SLICE_OWNERS)}


def build_packet(text, inventory, contract):
    """Full consumer packet: map + cross-check + first slice. No gameplay."""
    stages = decode_partition(text, contract)
    mismatches = cross_check(stages, inventory, contract)
    _require(not mismatches, "inventory drift: %r" % (mismatches,))
    readiness = readiness_map(stages, contract)
    result = {"schema": 1, "lane": LANE, "issue": ISSUE,
              "contract_issue": CONTRACT_ISSUE,
              "partition": list(PARTITION_KEYS),
              "stages": readiness,
              "first_slice": first_slice(stages),
              "placements": [], "generated": False,
              "playability": "no claim of playability; gates UNTESTED"}
    result["packet_sha256"] = hashlib.sha256(
        json.dumps(result, sort_keys=True).encode("utf-8")).hexdigest()
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--stages-text", required=True,
                        help="raw stages.txt text file to decode")
    parser.add_argument("--inventory", required=True,
                        help="content inventory JSON with challenge stages")
    parser.add_argument("--output", required=True,
                        help="packet output JSON path (parent must exist)")
    parser.add_argument("--contract", default=None,
                        help="alternate contract module path (default: pinned in-tree artifact)")
    args = parser.parse_args(argv)
    contract = load_contract(args.contract)
    text = Path(args.stages_text).read_text(encoding="utf-8")
    inventory = json.loads(Path(args.inventory).read_text(encoding="utf-8"))
    result = build_packet(text, inventory, contract)
    out = Path(args.output)
    _require(out.parent.is_dir(), "Missing output directory: %s" % out.parent)
    out.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"lane": LANE, "stages": len(result["stages"]),
                      "first_slice": result["first_slice"]["cave_id"],
                      "packet_sha256": result["packet_sha256"]}, indent=2))


if __name__ == "__main__":
    main()