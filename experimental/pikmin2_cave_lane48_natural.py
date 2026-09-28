"""Lane 48 natural-acquisition validator for the P2 cave Candypop bud path.

This module is a pure-Python, dependency-free reader of a captured cave
runtime log. It answers one question: was the cave ability acquired *naturally*
through a real Candypop bud conversion, or was it staged / mocked away?

It consumes the exact ``key=value`` marker lines lane 48 emits:

* ``P2_CAVE_BUD_ACTOR slot= colour= segment= count= x= y= z= spawned=1``
* ``P2_CAVE_BUD_ACCEPT slot= colour= thrown_colour= used= budget=`` (the lane-23
  ``P2_POM_ACCEPT`` form is accepted as an alias)
* ``P2_CAVE_BUD_SPROUT slot= colour= colour_index= plucked= natural=1`` (alias
  ``P2_POM_SPROUT``)
* ``P2_CAVE_BUD_DONE slot= colour= used= refunds= conversions=`` (alias
  ``P2_POM_DONE``)
* ``P2_CAVE_ROOMS_GRANT species= natural_acquire=0|1 staged=0|1``
* ``P2_CAVE_ROOMS_TIMELINE tag= hole= treasure_elec= treasure_water= untagged=``

It never imports the randomizer, the native engine or any GL fixture.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

SCHEMA = "p2-cave-lane48-natural/1"

NATURAL = "NATURAL"
STAGED = "STAGED"
MOCKED = "MOCKED"
MISSING = "MISSING"

COLOUR_CODES = {"blue": 0, "red": 1, "yellow": 2, "purple": 3, "white": 4}

_MARKER_PREFIXES = (
    ("bud_actor", "P2_CAVE_BUD_ACTOR"),
    ("accept", "P2_CAVE_BUD_ACCEPT"),
    ("sprout", "P2_CAVE_BUD_SPROUT"),
    ("done", "P2_CAVE_BUD_DONE"),
    ("grant", "P2_CAVE_ROOMS_GRANT"),
    ("timeline", "P2_CAVE_ROOMS_TIMELINE"),
    # Lane 23's own actor markers are accepted as aliases so a run that routes
    # the conversion through the source-policy module still validates.
    ("accept", "P2_POM_ACCEPT"),
    ("sprout", "P2_POM_SPROUT"),
    ("done", "P2_POM_DONE"),
)

# First prefix wins for a given key; aliases only add parser coverage.
_PREFIX_TO_KEY = {}
for _prefix_key, _prefix in _MARKER_PREFIXES:
    _PREFIX_TO_KEY.setdefault(_prefix, _prefix_key)

_MARKER_KEYS = tuple(dict.fromkeys(key for key, _ in _MARKER_PREFIXES))


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
    parsed = {}
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
    """Parse every known lane-48 marker out of a log (string or line list).

    Non-marker lines are ignored. A line whose first token is a known marker
    but whose trailing tokens are not ``key=value`` pairs is recorded under
    ``"malformed"`` instead of raising, so one bad line can never abort the
    verdict. Each parsed marker carries its source line index under ``_index``.
    """
    result = {key: [] for key in _MARKER_KEYS}
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
                {"line": line, "reason": f"malformed {tokens[0]} marker", "index": index})
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


def _resolve_species(grants):
    for grant in grants:
        if _is_one(grant.get("natural_acquire")) and not _is_one(grant.get("staged")):
            return grant.get("species")
    return grants[0].get("species") if grants else None


def _conversion_matches(line, species, colour) -> bool:
    if colour is not None:
        if line.get("colour") == COLOUR_CODES[colour]:
            return True
        if line.get("colour_index") == COLOUR_CODES[colour]:
            return True
        if canonical_colour(line.get("colour")) == colour:
            return True
    line_species = line.get("species")
    if species is not None and line_species is not None and _species_eq(line_species, species):
        return True
    return colour is not None and canonical_colour(line_species) == colour


def _classify(*, grants, buds, accepts, conversions, staged, matching_bud,
              natural, accept, conversion):
    if staged:
        return STAGED
    if not grants and not buds and not accepts and not conversions:
        return MISSING
    if (accepts or conversions) and matching_bud is None:
        return MOCKED
    if not grants:
        return MISSING
    if natural and matching_bud is not None and accept is not None and conversion is not None:
        return NATURAL
    return MOCKED


def _elec_after_grant(grant, timelines):
    if grant is None:
        return False, None, None
    grant_index = grant.get("_index")
    for row in timelines:
        row_index = row.get("_index")
        if (_is_one(row.get("treasure_elec")) and grant_index is not None
                and row_index is not None and row_index > grant_index):
            return True, grant_index, row_index
    return False, grant_index, None


def evaluate(source) -> dict:
    """Return the natural-acquisition verdict for a captured cave log."""
    parsed = parse_markers(source)
    grants = parsed["grant"]
    buds = parsed["bud_actor"]
    accepts = parsed["accept"]
    conversions = parsed["sprout"] + parsed["done"]
    timelines = parsed["timeline"]

    species = _resolve_species(grants)
    if species is None and conversions:
        species = conversions[-1].get("species")
    colour = canonical_colour(species)

    species_grants = ([grant for grant in grants if _species_eq(grant.get("species"), species)]
                      if species is not None else [])
    staged = any(_is_one(grant.get("staged")) for grant in species_grants)
    natural = any(_is_one(grant.get("natural_acquire")) and not _is_one(grant.get("staged"))
                  for grant in species_grants)
    natural_grant = _first([grant for grant in species_grants
                            if _is_one(grant.get("natural_acquire"))
                            and not _is_one(grant.get("staged"))])

    spawned_buds = [bud for bud in buds if _is_one(bud.get("spawned"))]
    any_bud = _first(spawned_buds)
    matching_bud = None
    if colour is not None:
        matching_bud = _first([bud for bud in spawned_buds
                               if canonical_colour(bud.get("colour")) == colour])

    accept = _first(accepts)
    conversion = _first([line for line in conversions
                         if _conversion_matches(line, species, colour)])

    reasons = []
    if staged:
        reasons.append("staged_grant")
    if any_bud is None:
        reasons.append("no_bud_actor")
    elif matching_bud is None:
        reasons.append("bud_colour_mismatch")
    if accept is None:
        reasons.append("no_accept")
    if conversion is None:
        reasons.append("no_conversion")
    if not grants:
        reasons.append("no_grant")
    elif not natural:
        reasons.append("no_natural_grant")

    classification = _classify(
        grants=grants, buds=spawned_buds, accepts=accepts, conversions=conversions,
        staged=staged, matching_bud=matching_bud, natural=natural,
        accept=accept, conversion=conversion)

    grant_for_timeline = natural_grant or _first(species_grants) or _first(grants)
    elec_after, grant_index, elec_index = _elec_after_grant(grant_for_timeline, timelines)

    return {
        "schema": SCHEMA,
        "pass": classification == NATURAL,
        "classification": classification,
        "species": species,
        "colour": colour,
        "reasons": reasons,
        "natural_grant": natural,
        "staged_grant": staged,
        "bud_actor": matching_bud,
        "bud_colour": canonical_colour((matching_bud or any_bud or {}).get("colour")),
        "accept": accept,
        "conversion": conversion,
        "grant": natural_grant or _first(species_grants),
        "timeline_rows": len(timelines),
        "elec_opened_after_grant": elec_after,
        "elec_grant_index": grant_index,
        "elec_timeline_index": elec_index,
        "counts": {
            "bud_actor": len(buds),
            "accept": len(accepts),
            "conversion": len(conversions),
            "grant": len(grants),
            "timeline": len(timelines),
            "malformed": len(parsed["malformed"]),
        },
    }


def main(path=None) -> int:
    """Print the JSON verdict for ``path`` and return the process exit code."""
    if path is None and len(sys.argv) > 1:
        path = sys.argv[1]
    if path is None:
        text = sys.stdin.read()
        display = "<stdin>"
    else:
        target = Path(str(path))
        text = target.read_text(encoding="utf-8", errors="replace")
        display = str(target)
    result = evaluate(text)
    result["source"] = display
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["pass"] else 1


if __name__ == "__main__":
    sys.exit(main())
