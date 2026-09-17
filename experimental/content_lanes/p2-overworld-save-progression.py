"""Overworld surface save/progression boundary contract (#132).

Read-only audit + isolated contract adapter for the four P2 overworld lanes
(148 Valley of Repose, 149 Awakening Wood, 150 Perplexing Pool, 151 Wistful
Wild). It binds the decoded overworld surface tables
(docs/PIKMIN2_CONTENT_INVENTORY.json -> user/Abe/stages.txt) to the existing
surface runtime modules (identity, ledger, physics, pocket, runner, topology)
WITHOUT editing any of them.

Boundary covered here (host side): per-area registry + decoded-source binding;
the surface snapshot schema the SurfaceLedger persists
(region/day/time/position/squad/health/receipts); the ledger envelope
(schema/campaign/content/origin/revision/phase/surface/trip/events); content
identity shape (64-hex) and region token charset.

Boundary NOT covered (exact unsupported references; nothing invented): the four
native integration items resolved by pin-discovery #658 - sunset driver, save
serializer, receipt ledger endpoint, generator-cache restore. Their pins are
recorded verbatim as references, not re-derived. Local disc stage-table bytes
that are absent stay absent: this module never fabricates a stage row.

P0 tooling only: no native build/runtime/ADMIT, all six runtime gates
UNTESTED. Shared surface modules are imported read-only (audit helper); if one
must change, that change goes through existing-owner review (#186).
"""
import argparse
import json
import re
from pathlib import Path

INVENTORY = "docs/PIKMIN2_CONTENT_INVENTORY.json"
STAGES_SOURCE = "user/Abe/stages.txt"
OVERWORLD_ISSUES = {"tutorial": 148, "forest": 149, "yakushima": 150, "last": 151}
SURFACE_MODULES = (
    "experimental/pikmin2_surface_identity.py",
    "experimental/pikmin2_surface_ledger.py",
    "experimental/pikmin2_surface_physics.py",
    "experimental/pikmin2_surface_pocket.py",
    "experimental/pikmin2_surface_runner.py",
    "experimental/pikmin2_surface_topology.py",
)
SNAPSHOT_FIELDS = ("region", "day", "time", "position", "squad", "health", "receipts")
LEDGER_FIELDS = ("schema", "campaign", "content", "origin", "revision", "phase",
                 "surface", "trip", "events")
LEDGER_PHASES = ("surface", "cave", "return_ready", "failed")
EVENT_PREFIXES = ("enter", "floor", "return")
NATIVE_PINS = {
    "sunset_driver": ["singleGameSection.cpp:183", "singleGameSection.cpp:209",
                      "singleGameSection.cpp:660", "singleGameSection.cpp:684",
                      "singleGameSection.cpp:486", "singleGameSection.cpp:500"],
    "save_serializer": ["gamePlayDataMemCard.cpp:39", "gamePlayDataMemCard.cpp:707",
                        "gamePlayDataMemCard.cpp:1372", "gamePlayDataMemCard.cpp:1411",
                        "gamePlayDataMemCard.cpp:1346", "gamePlayDataMemCard.cpp:1360"],
    "receipt_ledger_endpoint": ["onyonMgr.cpp:403", "gamePlayData.cpp:800",
                                "onyonMgr.cpp:195"],
    "generator_cache_restore": ["gameGeneratorCache.cpp:557", "gameGeneratorCache.cpp:504",
                                "gameGeneratorCache.cpp:203", "gameGeneratorCache.cpp:281",
                                "gameGeneratorCache.cpp:341", "gameGeneratorCache.cpp:665"],
}
NATIVE_PIN_PROVENANCE = "shard-overworld-last-save-session-pin-discovery (#658)"

_HEX = re.compile(r"[0-9a-f]+")
_REGION = re.compile(r"[a-z0-9_-]+")


class BoundaryError(ValueError):
    """Malformed or missing boundary input."""


def load_inventory(path=INVENTORY):
    """Read and validate the decoded overworld surface registry."""
    source = Path(path)
    if not source.is_file():
        raise BoundaryError("missing inventory: %s" % path)
    try:
        data = json.loads(source.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise BoundaryError("invalid inventory JSON: %s" % exc)
    surfaces = data.get("surfaces")
    if not isinstance(surfaces, list) or len(surfaces) != 4:
        raise BoundaryError("expected 4 decoded surfaces")
    registry = {}
    for row in surfaces:
        if not isinstance(row, dict) or set(row) != {"id", "name", "issue", "source"}:
            raise BoundaryError("malformed surface row")
        key = row["id"]
        if key not in OVERWORLD_ISSUES:
            raise BoundaryError("unknown overworld area: %r" % (key,))
        if row["issue"] != OVERWORLD_ISSUES[key]:
            raise BoundaryError("issue mismatch for %s" % key)
        if not isinstance(row["name"], str) or not row["name"].strip():
            raise BoundaryError("missing display name for %s" % key)
        if row["source"] != STAGES_SOURCE:
            raise BoundaryError("unexpected source table for %s" % key)
        registry[key] = {"name": row["name"], "issue": row["issue"], "source": row["source"]}
    missing = set(OVERWORLD_ISSUES) - set(registry)
    if missing:
        raise BoundaryError("missing overworld areas: %s" % sorted(missing))
    return registry


def validate_snapshot(snapshot):
    """Validate the surface snapshot fields the ledger persists (host schema)."""
    if not isinstance(snapshot, dict) or set(snapshot) != set(SNAPSHOT_FIELDS):
        raise BoundaryError("invalid surface snapshot fields")
    region = snapshot["region"]
    if (not isinstance(region, str) or not region or len(region) > 100
            or _REGION.fullmatch(region) is None):
        raise BoundaryError("invalid surface region token")
    if type(snapshot["day"]) is not int or not 1 <= snapshot["day"] <= 1000000:
        raise BoundaryError("invalid surface day")
    time = snapshot["time"]
    if type(time) not in (int, float) or not 0 <= time <= 24:
        raise BoundaryError("invalid surface time")
    position = snapshot["position"]
    if not isinstance(position, list) or len(position) != 3:
        raise BoundaryError("invalid surface position")
    for value in position:
        if type(value) not in (int, float) or abs(value) > 100000:
            raise BoundaryError("invalid surface position component")
    if not isinstance(snapshot["squad"], list) or not isinstance(snapshot["health"], list):
        raise BoundaryError("invalid surface squad/health")
    if not isinstance(snapshot["receipts"], dict):
        raise BoundaryError("invalid surface receipts")
    return snapshot


def validate_ledger_envelope(state):
    """Validate the ledger envelope shape; identity values are not re-hashed."""
    if not isinstance(state, dict) or set(state) != set(LEDGER_FIELDS):
        raise BoundaryError("invalid ledger envelope fields")
    if type(state["schema"]) is not int or state["schema"] != 1:
        raise BoundaryError("invalid ledger schema")
    for key, length in (("campaign", 32), ("content", 64), ("origin", 64)):
        value = state[key]
        if not isinstance(value, str) or len(value) != length or _HEX.fullmatch(value) is None:
            raise BoundaryError("invalid ledger identity: %s" % key)
    if state["phase"] not in LEDGER_PHASES:
        raise BoundaryError("invalid ledger phase")
    events = state["events"]
    if not isinstance(events, dict) or len(events) > 4096:
        raise BoundaryError("invalid ledger events")
    if type(state["revision"]) is not int or state["revision"] != len(events):
        raise BoundaryError("invalid ledger revision")
    for key, value in events.items():
        if not isinstance(key, str) or ":" not in key:
            raise BoundaryError("invalid ledger event key")
        prefix, _, suffix = key.partition(":")
        if prefix not in EVENT_PREFIXES:
            raise BoundaryError("invalid ledger event prefix")
        if len(suffix) != 32 or _HEX.fullmatch(suffix) is None:
            raise BoundaryError("invalid ledger event trip id")
        if not isinstance(value, str) or len(value) != 64 or _HEX.fullmatch(value) is None:
            raise BoundaryError("invalid ledger event digest")
    validate_snapshot(state["surface"])
    return state


def audit_area(area, registry, snapshot=None, ledger_state=None):
    """Audit one overworld area's save/progression boundary (no fabrication)."""
    if area not in registry:
        raise BoundaryError("unknown overworld area: %r" % (area,))
    row = registry[area]
    report = dict(area=area, name=row["name"], issue=row["issue"], source=row["source"],
                  decoded_table_present=True, snapshot="absent", ledger="absent")
    if snapshot is not None:
        validate_snapshot(snapshot)
        report["snapshot"] = "valid"
    if ledger_state is not None:
        validate_ledger_envelope(ledger_state)
        report["ledger"] = "valid"
    return report


def boundary_contract(inventory_path=INVENTORY):
    """Publish the covered/uncovered boundary contract for all four areas."""
    registry = load_inventory(inventory_path)
    areas = [audit_area(area, registry) for area in sorted(registry)]
    return dict(
        contract="p2-overworld-save-progression-v1",
        areas=areas,
        snapshot_fields=list(SNAPSHOT_FIELDS),
        ledger_fields=list(LEDGER_FIELDS),
        ledger_phases=list(LEDGER_PHASES),
        event_prefixes=list(EVENT_PREFIXES),
        covered_modules=sorted(SURFACE_MODULES),
        unsupported=dict(
            native_integration_items=sorted(NATIVE_PINS),
            native_pins=NATIVE_PINS,
            native_pin_provenance=NATIVE_PIN_PROVENANCE,
            missing_local_disc_tables=[STAGES_SOURCE],
            note="local disc stage-table bytes absent stay absent; nothing invented",
        ),
    )


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--inventory", default=INVENTORY)
    parser.add_argument("--output")
    args = parser.parse_args(argv)
    contract = boundary_contract(args.inventory)
    text = json.dumps(contract, indent=1, sort_keys=True)
    if args.output:
        Path(args.output).write_text(text, encoding="utf-8")
    else:
        print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())