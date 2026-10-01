"""Per-species placement unit for P2-in-P1 slots (owner ruling 2026-09-30).

A pool row may carry ``"unit": N``: when that species replaces a generator slot the
slot is born as N actors instead of one (Anode Beetle 28 = 2, a pair that can link
within the ~300-unit partner radius). The unit is data on ``seed.P2_PLAYABLE_POOL``;
the launcher stages it into the run directory as ``p2-species-units.txt`` and the
native generator hook (``pc_p2_species_unit.h``) reads it. Species without a unit
keep the generator's own count.
"""
from pathlib import Path

UNITS_FILE = "p2-species-units.txt"
HEADER = "P2_SPECIES_UNITS_1"
MAX_UNIT = 8


def species_units():
    """``{source_id: unit}`` for every pool species whose unit is above 1."""
    from .seed import P2_PLAYABLE_POOL
    units = {}
    for row in P2_PLAYABLE_POOL:
        unit = row.get("unit", 1)
        if type(unit) is not int or not 1 <= unit <= MAX_UNIT:
            raise ValueError(f"invalid unit for species {row['source_id']}: {unit!r}")
        if unit > 1:
            units[row["source_id"]] = unit
    return units


def species_unit(source_id):
    return species_units().get(source_id, 1)


def units_for_layout(layout):
    """Units of the species actually bound by a ``p2_layout``."""
    bound = {binding["source_id"] for binding in (layout or {}).get("bindings", [])}
    return {source: unit for source, unit in sorted(species_units().items()) if source in bound}


def units_text(layout):
    units = units_for_layout(layout)
    if not units:
        return None
    return HEADER + "\n" + "".join(f"{source} {unit}\n" for source, unit in units.items())


def stage_units(run_dir, layout):
    """Write ``p2-species-units.txt`` into the run directory (no file when every
    bound species has unit 1). Returns the units staged."""
    text = units_text(layout)
    if text is None:
        return {}
    (Path(run_dir) / UNITS_FILE).write_text(text, encoding="utf-8", newline="\n")
    return units_for_layout(layout)
