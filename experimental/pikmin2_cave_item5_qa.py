"""Lane 51 (#489) item-5 independent QA for the P2 cave natural loop.

Item 5 (the end-to-end "come back with yellow" loop) is the single open cave
acceptance item. Lanes 48 (natural bud acquisition), 49 (real water/elec
geometry) and 50 (gate/pool carry blocking) close its three sub-parts. This
module is the independent checker/regression matrix over those three contracts
plus the collection timeline. It is QA tooling only: it never imports the
randomizer, the native engine or any GL fixture, and it never generates a cave.

It reads captured runtime marker logs (strings or line lists) and classifies
each matrix row fail-closed:

* ``natural_acquisition`` -- NATURAL / STAGED / MOCKED / MISSING (lane 48
  ``P2_CAVE_BUD_*`` + ``P2_CAVE_ROOMS_GRANT`` contract).
* ``real_geometry`` -- REAL / PROXY / MISSING (lane 49 ``P2_CAVE_GEOMETRY_*``
  contract).
* ``carry_blocked_closed`` -- PASS / FAIL / MISSING (lane 50: a carrying
  non-immune Pikmin is stopped at the closed door, no credit while closed).
* ``gate_open_credit`` -- PASS / FAIL / STAGED_OPEN / MISSING (lane 50 + 46:
  an immune Pikmin opens the gate, the same carry credits exactly once).
* ``water_gating`` -- PASS / FAIL / MISSING (lane 50: non-blue carrying is
  stopped at the water pool; water never opens).
* ``hole_gating`` -- PASS / FAIL / MISSING (the hole is reachable only after
  the required abilities, per the ``P2_CAVE_ROOMS_TIMELINE`` tags).
* ``timeline`` -- PASS / FAIL / MISSING (fresh -> yellow -> yellow+blue tags).

The whole report passes only when every row is at its natural value. Any
mocked, staged, proxy or missing row fails the report and is named in
``remaining`` so the re-sweep can file a precise finding on the owning lane
(48/49/50). A forced recolour (``staged=1``) is never reported as natural, and
a proxy layout is never reported as real geometry.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

SCHEMA = "p2-cave-item5-qa/1"

NATURAL = "NATURAL"
STAGED = "STAGED"
MOCKED = "MOCKED"
MISSING = "MISSING"
REAL = "REAL"
PROXY = "PROXY"
PASS = "PASS"
FAIL = "FAIL"
STAGED_OPEN = "STAGED_OPEN"

# Marker prefix -> result key. First prefix wins; lane-23 POM aliases accepted
# for the bud conversion path exactly as lane 48's validator does.
_MARKER_PREFIXES = (
    ("bud_actor", "P2_CAVE_BUD_ACTOR"),
    ("accept", "P2_CAVE_BUD_ACCEPT"),
    ("close", "P2_CAVE_BUD_CLOSE"),
    ("sprout", "P2_CAVE_BUD_SPROUT"),
    ("bud_done", "P2_CAVE_BUD_DONE"),
    ("grant", "P2_CAVE_ROOMS_GRANT"),
    ("timeline", "P2_CAVE_ROOMS_TIMELINE"),
    ("accept", "P2_POM_ACCEPT"),
    ("sprout", "P2_POM_SPROUT"),
    ("bud_done", "P2_POM_DONE"),
    ("geometry_node", "P2_CAVE_GEOMETRY_NODE"),
    ("geometry_ready", "P2_CAVE_GEOMETRY_READY"),
    ("geometry_draw", "P2_CAVE_GEOMETRY_DRAW"),
    ("geometry_gate", "P2_CAVE_GEOMETRY_GATE"),
    ("geometry_denki", "P2_CAVE_GEOMETRY_GATE_DENKI"),
    ("geometry_open", "P2_CAVE_GEOMETRY_GATE_OPEN"),
    ("geometry_class", "P2_CAVE_GEOMETRY_CLASS"),
    ("item_actor", "P2_CAVE_ITEM_ACTOR"),
    ("items_ready", "P2_CAVE_ITEMS_READY"),
    ("receipt", "P2_CAVE_ITEM_RECEIPT"),
    ("natural_carry", "P2_CAVE_ITEM_NATURAL_CARRY"),
    ("carry_door", "P2_CAVE_CARRY_DOOR"),
    ("carry_volume", "P2_CAVE_CARRY_VOLUME"),
    ("carry_plan", "P2_CAVE_CARRY_PLAN"),
    ("carry_open", "P2_CAVE_CARRY_OPEN"),
    ("carry_blocked", "P2_CAVE_CARRY_BLOCKED"),
    ("carry_phase", "P2_CAVE_CARRY_PHASE"),
    ("gen", "P2_CAVE_GEN"),
)

_PREFIX_TO_KEY: dict[str, str] = {}
for _key, _prefix in _MARKER_PREFIXES:
    _PREFIX_TO_KEY.setdefault(_prefix, _key)

_MARKER_KEYS = tuple(dict.fromkeys(key for key, _ in _MARKER_PREFIXES))

# Sub-part -> owning lane for precise findings.
ROW_OWNER = {
    "natural_acquisition": "lane 48 (#486)",
    "real_geometry": "lane 49 (#487)",
    "carry_blocked_closed": "lane 50 (#488)",
    "gate_open_credit": "lane 50 (#488) + lane 46 (#484)",
    "water_gating": "lane 50 (#488)",
    "hole_gating": "lane 44 (#482) timeline + lane 50 (#488)",
    "timeline": "lane 44 (#482)",
}

COLOUR_CODES = {"blue": 0, "red": 1, "yellow": 2, "purple": 3, "white": 4}


def _coerce(value: str):
    try:
        return int(value)
    except (TypeError, ValueError):
        pass
    try:
        return float(value)
    except (TypeError, ValueError):
        return value


def _parse_pairs(tokens) -> dict | None:
    parsed: dict = {}
    for token in tokens:
        if "=" not in token:
            return None
        key, value = token.split("=", 1)
        if not key:
            return None
        parsed[key] = _coerce(value)
    return parsed


def _iter_lines(source):
    if source is None:
        return []
    if isinstance(source, str):
        return source.splitlines()
    if isinstance(source, bytes):
        return source.decode("utf-8", "replace").splitlines()
    try:
        return list(source)
    except TypeError:
        return str(source).splitlines()


def parse_markers(source) -> dict:
    """Parse every known item-5 marker out of a log.

    Non-marker lines are ignored. A line whose first token is a known marker
    but whose trailing tokens are not ``key=value`` pairs is recorded under
    ``"malformed"`` instead of raising, so one bad line can never abort the
    verdict. Each parsed marker carries its source line index under ``_index``.
    """
    result: dict = {key: [] for key in _MARKER_KEYS}
    result["malformed"] = []
    for index, raw in enumerate(_iter_lines(source)):
        line = str(raw).strip()
        if not line:
            continue
        tokens = line.split()
        key = _PREFIX_TO_KEY.get(tokens[0])
        if key is None:
            continue
        parsed = _parse_pairs(tokens[1:]) if len(tokens) > 1 else None
        if parsed is None:
            result["malformed"].append(
                {"line": line, "reason": f"malformed {tokens[0]} marker", "index": index}
            )
        else:
            parsed["_index"] = index
            result[key].append(parsed)
    return result


def _is_one(value) -> bool:
    return value == 1 or value is True


def _first(items):
    return items[0] if items else None


def canonical_colour(value) -> str | None:
    """Map a bud colour token or a species name onto a canonical colour."""
    if value is None:
        return None
    text = str(value).strip().lower()
    if text in COLOUR_CODES:
        return text
    for colour in COLOUR_CODES:
        if colour in text:
            return colour
    return None


def _species_eq(left, right) -> bool:
    if left is None or right is None:
        return left == right
    return str(left).strip().lower() == str(right).strip().lower()


def evaluate_acquisition(parsed: dict) -> dict:
    """Classify the lane-48 natural-acquisition sub-part."""
    grants = parsed["grant"]
    buds = parsed["bud_actor"]
    accepts = parsed["accept"]
    conversions = parsed["sprout"] + parsed["bud_done"]

    species = None
    for grant in grants:
        if _is_one(grant.get("natural_acquire")) and not _is_one(grant.get("staged")):
            species = grant.get("species")
            break
    if species is None and grants:
        species = grants[0].get("species")
    colour = canonical_colour(species)

    species_grants = (
        [g for g in grants if _species_eq(g.get("species"), species)]
        if species is not None
        else []
    )
    staged = any(_is_one(g.get("staged")) for g in species_grants)
    natural = any(
        _is_one(g.get("natural_acquire")) and not _is_one(g.get("staged"))
        for g in species_grants
    )
    spawned = [b for b in buds if _is_one(b.get("spawned"))]
    matching = None
    if colour is not None:
        matching = _first(
            [b for b in spawned if canonical_colour(b.get("colour")) == colour]
        )
    accept = _first(accepts)
    conversion = None
    for line in conversions:
        hit = False
        if colour is not None:
            if line.get("colour") == COLOUR_CODES.get(colour):
                hit = True
            elif line.get("colour_index") == COLOUR_CODES.get(colour):
                hit = True
            elif canonical_colour(line.get("colour")) == colour:
                hit = True
        if not hit and species is not None and _species_eq(
            line.get("species"), species
        ):
            hit = True
        if hit:
            conversion = line
            break

    reasons = []
    if staged:
        reasons.append("staged_grant")
    if not spawned:
        reasons.append("no_bud_actor")
    elif matching is None:
        reasons.append("bud_colour_mismatch")
    if accept is None:
        reasons.append("no_accept")
    if conversion is None:
        reasons.append("no_conversion")
    if not grants:
        reasons.append("no_grant")
    elif not natural:
        reasons.append("no_natural_grant")

    if staged:
        classification = STAGED
    elif not grants and not spawned and not accepts and not conversions:
        classification = MISSING
    elif (accepts or conversions) and matching is None:
        classification = MOCKED
    elif not grants:
        classification = MISSING
    elif natural and matching is not None and accept is not None and conversion is not None:
        classification = NATURAL
    else:
        classification = MOCKED
    return {
        "classification": classification,
        "pass": classification == NATURAL,
        "species": species,
        "colour": colour,
        "natural": natural,
        "staged": staged,
        "reasons": reasons,
        "grant": _first(
            [
                g
                for g in species_grants
                if _is_one(g.get("natural_acquire"))
                and not _is_one(g.get("staged"))
            ]
        )
        or _first(species_grants),
        "counts": {
            "bud_actor": len(buds),
            "accept": len(accepts),
            "conversion": len(conversions),
            "grant": len(grants),
        },
    }


def evaluate_geometry(parsed: dict) -> dict:
    """Classify the lane-49 real-geometry sub-part."""
    nodes = parsed["geometry_node"]
    readies = parsed["geometry_ready"]
    draws = parsed["geometry_draw"]
    denkis = parsed["geometry_denki"]

    real_nodes = [n for n in nodes if n.get("class") == "real" and n.get("proxy") == 0]
    real_ids = {str(n.get("id")) for n in real_nodes}
    required = {"choke_water_0", "leaf_water_0", "leaf_elec_0"}
    required_real = required.issubset(real_ids)
    gate_real = any(
        n.get("kind") == "gate" and n.get("class") == "real" for n in nodes
    )
    ready_real = any(
        r.get("geometry") == "real" and int(r.get("real") or 0) >= 4
        for r in readies
    )
    draw_real = any(d.get("geometry") == "real" for d in draws)
    denki_ok = any(
        _is_one(d.get("accepted")) for d in denkis
    )
    proxy_seen = any(n.get("class") == "proxy" or n.get("proxy") == 1 for n in nodes)

    reasons = []
    if not nodes and not readies and not draws:
        reasons.append("no_geometry_markers")
    if nodes and not required_real:
        reasons.append("required_nodes_not_real")
    if not gate_real:
        reasons.append("no_real_gate")
    if not ready_real:
        reasons.append("no_ready_real4")
    if not draw_real:
        reasons.append("no_draw_real")

    if not nodes and not readies and not draws:
        classification = MISSING
    elif required_real and gate_real and ready_real and draw_real:
        classification = REAL
    else:
        classification = PROXY
    return {
        "classification": classification,
        "pass": classification == REAL,
        "required_nodes_real": required_real,
        "gate_real": gate_real,
        "ready_real4": ready_real,
        "draw_real": draw_real,
        "denki_accepted": denki_ok,
        "proxy_seen": proxy_seen,
        "real_ids": sorted(real_ids),
        "reasons": reasons,
        "counts": {
            "node": len(nodes),
            "real_node": len(real_nodes),
            "ready": len(readies),
            "draw": len(draws),
            "denki": len(denkis),
        },
    }


def _receipts_for(parsed: dict, item: str) -> list:
    return [
        r
        for r in parsed["receipt"]
        if str(r.get("item") or r.get("id") or "") == item
        or str(r.get("host") or "") == item
    ]


def evaluate_carry(parsed: dict, natural_yellow: bool) -> dict:
    """Classify the lane-50 gate/pool carry-blocking sub-part.

    ``natural_yellow`` records whether the gate opening was earned through the
    lane-48 natural bud path. A staged recolour opening the gate can never
    yield a natural ``gate_open_credit`` PASS.
    """
    plans = parsed["carry_plan"]
    doors = parsed["carry_door"]
    blocked = parsed["carry_blocked"]
    opens = parsed["carry_open"] + parsed["geometry_open"]
    phases = parsed["carry_phase"]
    receipts = parsed["receipt"]

    plan = _first(plans)
    elec_doors = [d for d in doors if d.get("carry_block") == "elec"]
    water_doors = [d for d in doors if d.get("carry_block") == "water"]
    plan_blocking = int(plan.get("blocking") or 0) if plan else 0

    carrying_blocks = [b for b in blocked if int(b.get("carrying") or 0) == 1]
    carrier_drops = [b for b in blocked if int(b.get("carrying") or 0) == 1]
    elec_carrier_blocks = [
        b for b in carrying_blocks if str(b.get("hazard")) == "elec"
    ]
    water_carrier_blocks = [
        b for b in carrying_blocks if str(b.get("hazard")) == "water"
    ]

    # Credit-while-closed: any receipt for the elec treasure at a line index
    # before the first gate open marker.
    open_index = min(
        [o.get("_index", 1 << 60) for o in opens if o.get("_index") is not None]
        + [1 << 60]
    )
    elec_receipts = [
        r
        for r in receipts
        if "elec" in str(r.get("item") or r.get("id") or r.get("host") or "")
    ]
    credited_while_closed = any(
        (r.get("_index", 1 << 60) or 1 << 60) < open_index
        and int(r.get("new") or 0) == 1
        for r in elec_receipts
    )
    elec_new_total = sum(int(r.get("new") or 0) for r in elec_receipts)

    phase_names = {str(p.get("phase")) for p in phases}
    has_block_phase = any(
        str(p.get("phase")) in ("blocked", "block_assign", "waiting")
        for p in phases
    )

    # --- carry_blocked_closed ---
    if not plans and not doors and not blocked and not phases:
        blocked_class = MISSING
        blocked_reasons = ["no_carry_markers"]
    elif elec_carrier_blocks and not credited_while_closed:
        blocked_class = PASS
        blocked_reasons = []
    elif credited_while_closed:
        blocked_class = FAIL
        blocked_reasons = ["credited_while_closed"]
    elif carrying_blocks and not elec_carrier_blocks:
        blocked_class = FAIL
        blocked_reasons = ["no_elec_carrier_block"]
    else:
        blocked_class = FAIL if (plans or doors or phases) else MISSING
        blocked_reasons = ["no_carrying_block_observed"] if blocked_class == FAIL else ["no_carry_markers"]

    # --- gate_open_credit ---
    fresh_credit = [r for r in elec_receipts if int(r.get("new") or 0) == 1]
    dup_credit = [r for r in elec_receipts if int(r.get("new") or 0) == 0]
    exactly_once = len(fresh_credit) == 1 and elec_new_total == 1
    opened = len(opens) > 0
    if not plans and not doors and not opens and not receipts and not phases:
        open_class = MISSING
        open_reasons = ["no_open_credit_markers"]
    elif not opened:
        open_class = MISSING if not receipts else FAIL
        open_reasons = ["no_gate_open"] if open_class else ["no_open_credit_markers"]
    elif credited_while_closed:
        open_class = FAIL
        open_reasons = ["credited_while_closed"]
    elif not exactly_once:
        open_class = FAIL
        open_reasons = ["credit_not_exactly_once"]
    elif not natural_yellow:
        open_class = STAGED_OPEN
        open_reasons = ["open_not_natural"]
    else:
        open_class = PASS
        open_reasons = []

    # --- water_gating ---
    if not plans and not doors and not blocked and not phases:
        water_class = MISSING
        water_reasons = ["no_carry_markers"]
    elif water_carrier_blocks:
        water_class = PASS
        water_reasons = []
    else:
        water_class = FAIL
        water_reasons = ["no_water_carrier_block"]

    return {
        "plan": plan,
        "plan_blocking": plan_blocking,
        "elec_doors": len(elec_doors),
        "water_doors": len(water_doors),
        "carry_blocked_closed": {
            "classification": blocked_class,
            "pass": blocked_class == PASS,
            "reasons": blocked_reasons,
        },
        "gate_open_credit": {
            "classification": open_class,
            "pass": open_class == PASS,
            "reasons": open_reasons,
            "opened": opened,
            "fresh_credits": len(fresh_credit),
            "duplicate_credits": len(dup_credit),
            "credited_while_closed": credited_while_closed,
        },
        "water_gating": {
            "classification": water_class,
            "pass": water_class == PASS,
            "reasons": water_reasons,
        },
        "counts": {
            "plan": len(plans),
            "door": len(doors),
            "blocked": len(blocked),
            "carrying_blocked": len(carrying_blocks),
            "open": len(opens),
            "phase": len(phases),
            "receipt": len(receipts),
        },
        "phases": sorted(phase_names),
    }


def evaluate_timeline(parsed: dict) -> dict:
    """Classify the lane-44 hazard timeline and the hole-gating sub-part."""
    rows = parsed["timeline"]
    by_tag = {}
    for row in rows:
        by_tag.setdefault(str(row.get("tag")), row)
    fresh = by_tag.get("fresh_floor_no_abilities")
    yellow = by_tag.get("come_back_with_yellow")
    full = by_tag.get("return_with_yellow_and_blue")

    reasons = []
    if not rows:
        return {
            "timeline": {"classification": MISSING, "pass": False, "reasons": ["no_timeline"]},
            "hole_gating": {"classification": MISSING, "pass": False, "reasons": ["no_timeline"]},
        }
    if fresh is None:
        reasons.append("no_fresh_tag")
    elif int(fresh.get("hole") or 0) != 0:
        reasons.append("hole_open_on_fresh_floor")
    if yellow is None:
        reasons.append("no_yellow_tag")
    elif int(yellow.get("treasure_elec") or 0) != 1:
        reasons.append("elec_not_open_with_yellow")
    if full is None:
        reasons.append("no_full_tag")
    elif int(full.get("hole") or 0) != 1:
        reasons.append("hole_not_open_with_yellow_and_blue")

    timeline_pass = not reasons
    hole_reasons = [r for r in reasons if "hole" in r]
    hole_class = PASS if not hole_reasons and fresh is not None and full is not None else (
        FAIL if rows else MISSING
    )
    return {
        "timeline": {
            "classification": PASS if timeline_pass else FAIL,
            "pass": timeline_pass,
            "reasons": reasons,
        },
        "hole_gating": {
            "classification": hole_class,
            "pass": hole_class == PASS,
            "reasons": hole_reasons,
        },
    }


def evaluate(source, seed: int = 468001) -> dict:
    """Return the item-5 verdict for captured cave log(s).

    ``source`` may be a single log string or a list of log strings; markers
    from every entry are merged with re-based line indices so multi-run
    evidence (block run + open run) evaluates as one loop.
    """
    if isinstance(source, (list, tuple)):
        merged: dict = {key: [] for key in _MARKER_KEYS}
        merged["malformed"] = []
        offset = 0
        for entry in source:
            part = parse_markers(entry)
            for key in _MARKER_KEYS:
                for row in part[key]:
                    row = dict(row)
                    if row.get("_index") is not None:
                        row["_index"] += offset
                    merged[key].append(row)
            merged["malformed"].extend(part["malformed"])
            offset += len(_iter_lines(entry)) + 1
        parsed = merged
    else:
        parsed = parse_markers(source)

    acquisition = evaluate_acquisition(parsed)
    geometry = evaluate_geometry(parsed)
    carry = evaluate_carry(parsed, acquisition["pass"])
    timeline = evaluate_timeline(parsed)

    rows = {
        "natural_acquisition": acquisition["classification"],
        "real_geometry": geometry["classification"],
        "carry_blocked_closed": carry["carry_blocked_closed"]["classification"],
        "gate_open_credit": carry["gate_open_credit"]["classification"],
        "water_gating": carry["water_gating"]["classification"],
        "hole_gating": timeline["hole_gating"]["classification"],
        "timeline": timeline["timeline"]["classification"],
    }
    row_pass = {
        "natural_acquisition": acquisition["pass"],
        "real_geometry": geometry["pass"],
        "carry_blocked_closed": carry["carry_blocked_closed"]["pass"],
        "gate_open_credit": carry["gate_open_credit"]["pass"],
        "water_gating": carry["water_gating"]["pass"],
        "hole_gating": timeline["hole_gating"]["pass"],
        "timeline": timeline["timeline"]["pass"],
    }
    remaining = [
        f"{name} ({ROW_OWNER[name]})"
        for name, ok in row_pass.items()
        if not ok
    ]
    evidence_class = (
        NATURAL
        if all(row_pass.values())
        else "PARTIAL"
    )
    return {
        "schema": SCHEMA,
        "seed": seed,
        "pass": all(row_pass.values()),
        "evidence_class": evidence_class,
        "rows": rows,
        "row_pass": row_pass,
        "remaining": remaining,
        "natural_acquisition": acquisition,
        "real_geometry": geometry,
        "carry": carry,
        "timeline": timeline["timeline"],
        "hole_gating": timeline["hole_gating"],
        "malformed": len(parsed["malformed"]),
    }


def main(argv=None) -> int:
    """CLI: score one or more run logs and write the JSON report."""
    parser = argparse.ArgumentParser(
        description="Lane 51 item-5 independent QA over cave run logs"
    )
    parser.add_argument("--log", action="append", default=[],
                        help="captured run log to score (repeatable)")
    parser.add_argument("--receipts", default=None,
                        help="optional P2_RECEIPTS_1 ledger (audited, not scored)")
    parser.add_argument("--seed", type=int, default=468001)
    parser.add_argument("--out", default=None)
    args = parser.parse_args(argv)

    if not args.log:
        print("no --log given", file=sys.stderr)
        return 2
    texts = []
    for path in args.log:
        texts.append(Path(path).read_text(encoding="utf-8", errors="replace"))
    result = evaluate(texts if len(texts) > 1 else texts[0], seed=args.seed)
    result["sources"] = list(args.log)
    if args.receipts is not None:
        ledger = Path(args.receipts).read_text(encoding="utf-8", errors="replace")
        result["ledger_lines"] = len(ledger.splitlines())
    text = json.dumps(result, indent=2, sort_keys=True)
    if args.out is not None:
        Path(args.out).write_text(text, encoding="utf-8")
    print(text)
    return 0 if result["pass"] else 1


if __name__ == "__main__":
    sys.exit(main())
