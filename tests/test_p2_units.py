"""Placement unit: Anode Beetle 28 is placed as a pair (owner ruling 2026-09-30)."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

from randomizer import p2_units
from randomizer.seed import P2_PLAYABLE_POOL


def layout(*ids):
    return {"bindings": [{"target": str(1000 + i), "source_id": sid, "enum_name": "X"} for i, sid in enumerate(ids)]}


def test_unit_is_pool_data_and_only_anode_beetle_has_one():
    assert p2_units.species_units() == {28: 2}
    assert p2_units.species_unit(28) == 2
    assert p2_units.species_unit(78) == 1
    assert [row["source_id"] for row in P2_PLAYABLE_POOL if row.get("unit", 1) != 1] == [28]


def test_units_file_lists_only_bound_species_with_a_unit(tmp_path):
    assert p2_units.units_text(layout(78, 59)) is None
    assert p2_units.stage_units(tmp_path, layout(78)) == {}
    assert not (tmp_path / p2_units.UNITS_FILE).exists()
    assert p2_units.stage_units(tmp_path, layout(28, 28, 78)) == {28: 2}
    # exactly what native pc_p2_species_unit.h parse() accepts
    assert (tmp_path / p2_units.UNITS_FILE).read_text() == "P2_SPECIES_UNITS_1\n28 2\n"


def test_bad_unit_is_rejected(monkeypatch):
    import randomizer.seed as seed
    rows = tuple(dict(row, unit=9) if row["source_id"] == 28 else row for row in seed.P2_PLAYABLE_POOL)
    monkeypatch.setattr(seed, "P2_PLAYABLE_POOL", rows)
    try:
        p2_units.species_units()
    except ValueError as error:
        assert "28" in str(error)
    else:
        raise AssertionError("unit 9 must be rejected")


def test_smoke_verify_expects_the_unit_count():
    import p2_smoke_verify as verify
    base = "AUTOPLAY_NAVI state=a navi=(0,0)\n"
    log = base + "P2_SEED_RESOLVE source_id=28 target=1000 original_type=4 x=10.0 z=10.0\n"
    ready = "P2_ENEMY_READY species=ElecBug native_family=Chappy generator=1000 x=%d.0 y=0 z=10.0 health=500.0\n"
    one = verify.evaluate(verify.parse_log(log + ready % 10), {1000: 28}, max_distance=1000)
    assert not one["ok"] and any("placement unit" in p for p in one["problems"])
    two = verify.evaluate(verify.parse_log(log + ready % 10 + ready % 50), {1000: 28}, max_distance=1000)
    assert two["ok"], two["problems"]
