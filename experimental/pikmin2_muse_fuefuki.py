"""Correlated natural-spawn observer for Fuefuki (Antenna Beetle, source 41).

Muse lane l57 (#497), child of #245. Gate 1 (identity_spawn) closes only when
the SAME real generated spawn appears in all three native marker legs:

1. Placement: ``P2_PLACEMENT_SLOT generator=<file-id> slot=<seed-uid> ...``
   (native/pc_port/pc_p2_placement_probe.cpp ``emitPlacementSlot``, driven per
   birth from src/plugPikiNakata/genteki.cpp ``GenObjectTeki::birth``).
2. Seed resolve: ``P2_SEED_RESOLVE source_id=41 target=<seed-uid> ...``
   (genteki.cpp P2 bridge path). ``target`` is the seed slot uid produced by
   ``pc_randomizer_generator_id`` and must equal the placement ``slot``.
3. Fuefuki actor binding: ``P2_HARDLANES_READY family=Fuefuki vehicle=Napkid
   gen=<file-id> ...`` (pc_port/pc_p2_hardlanes.cpp ``pc_p2_hardlanes_setup``)
   or any ``P2_FUEFUKI_TEKI_* ... generator=<file-id>`` marker. The binding
   ``gen``/``generator`` is the engine generator file id (``_70``) and must
   equal the placement ``generator``.

Fail-closed: any missing leg, any uid/file-id mismatch, an unmapped slot
(``slot=0``), non-ground terrain or missing route evidence yields
``gate1_ok == False``. A staged P1 ``TEKI_Napkid`` proxy birth without the
seed-resolve leg can never pass; synthetic markers are not generated here, so
nothing in this module can fabricate acceptance.

Dependency-free pure functions over log text; stdlib only. Read-only with
respect to the legacy l28 lane: this observer consumes the same marker
contract but owns no family FSM, placement, or packaging file.
"""

import json
import sys

SOURCE_ID = 41
SOURCE_NAME = "Fuefuki"

PLACEMENT = "P2_PLACEMENT_SLOT"
SEED_RESOLVE = "P2_SEED_RESOLVE"
HARDLANES_READY = "P2_HARDLANES_READY"
FUEFUKI_PREFIX = "P2_FUEFUKI_TEKI_"


def _fields(tokens):
    fields = {}
    for token in tokens:
        key, sep, value = token.partition("=")
        if sep:
            fields[key] = value
    return fields


def _int(value):
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _is_fuefuki_binding(tokens, line):
    """True for a Fuefuki actor-binding marker (ready line or TEKI marker)."""
    if any(tok.startswith(FUEFUKI_PREFIX) for tok in tokens):
        return True
    return HARDLANES_READY in tokens and "family=Fuefuki" in line


def _binding_file_id(fields):
    for key in ("generator", "gen", "generator_id"):
        num = _int(fields.get(key))
        if num is not None:
            return num
    return None


def parse(text):
    """Return the gate-1 correlated-spawn verdict for run-log text.

    A verdict is True only when at least one triple correlates: a placement
    line whose ``slot`` uid equals a ``P2_SEED_RESOLVE source_id=41`` target
    uid, and whose ``generator`` file id equals a Fuefuki binding file id,
    with ground terrain and route evidence on the placement line.
    """
    placements = []  # (generator, slot, terrain_ok, route_ok, line_no)
    seed_targets = []  # seed-uid targets resolved for source 41
    seed_other = False  # a resolve leg exists but for another source id
    bindings = []  # Fuefuki binding file ids

    for line_no, line in enumerate((text or "").splitlines(), start=1):
        tokens = line.split()
        if not tokens:
            continue
        fields = _fields(tokens)
        if PLACEMENT in tokens:
            placements.append(
                {
                    "generator": _int(fields.get("generator")),
                    "slot": _int(fields.get("slot")),
                    "terrain_ok": fields.get("terrain") == "ground"
                    and fields.get("xyz") == "1",
                    "route_ok": fields.get("route") == "1",
                    "line": line_no,
                }
            )
        if SEED_RESOLVE in tokens:
            target = _int(fields.get("target", fields.get("target_id")))
            if fields.get("source_id") == str(SOURCE_ID):
                if target is not None:
                    seed_targets.append(target)
            elif target is not None:
                seed_other = True
        if _is_fuefuki_binding(tokens, line):
            file_id = _binding_file_id(fields)
            if file_id is not None:
                bindings.append(file_id)

    match = None
    for placement in placements:
        if placement["generator"] is None or placement["slot"] is None:
            continue
        if placement["slot"] == 0:
            continue  # unmapped slot: no legal-slot profile, fail closed
        if not (placement["terrain_ok"] and placement["route_ok"]):
            continue  # unsupported terrain or missing carry route
        if placement["slot"] not in seed_targets:
            continue  # no source-41 resolve for this seed uid
        if placement["generator"] not in bindings:
            continue  # no Fuefuki actor bound to this generator file id
        match = {
            "seed_uid": placement["slot"],
            "generator": placement["generator"],
            "placement_line": placement["line"],
        }
        break

    return {
        "placement_lines": len(placements),
        "seed_resolve_41_targets": sorted(set(seed_targets)),
        "seed_resolve_other_source": seed_other,
        "fuefuki_bindings": sorted(set(bindings)),
        "generator": match["generator"] if match else -1,
        "seed_uid": match["seed_uid"] if match else -1,
        "same_generator": match is not None,
        "gate1_ok": match is not None,
    }


def main(argv=None):
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("path", nargs="?", help="Run-log path (defaults to stdin)")
    args = parser.parse_args(argv)
    if args.path:
        with open(args.path, encoding="utf-8", errors="replace") as handle:
            text = handle.read()
    else:
        text = sys.stdin.read()
    print(json.dumps(parse(text), indent=2))


if __name__ == "__main__":
    main()
