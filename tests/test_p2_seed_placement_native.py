"""Flip tests for the P2_PLACEMENT_SLOT / P2_SEED_RESOLVE / P2_ENEMY_READY co-occurrence.

Pure-Python: the validator passes on a representative captured log and flips when
any one of the three markers is stripped (so the marker — not incidental text —
carries the generator->slot->source agreement).

A second, unskipped-when-present source-text class pins the native emission sites
through ``PIKMIN_NATIVE_ROOT`` (probed via ``pc_port/`` and ``src/``) so the
markers are backed by the real probe and ``GenObjectTeki::birth`` hook. No lane
paths appear in this file; without ``PIKMIN_NATIVE_ROOT`` the source class skips.
"""
import os
import unittest
from pathlib import Path

from experimental.pikmin2_seed_placement_native import (
    ORANGE_SOURCE,
    SNOW_SOURCE,
    validate_cooccurrence,
)

ROOT = Path(__file__).resolve().parents[1]

SAMPLE_LOG = """\
P2_SEED_RESOLVE source_id=44 target=5465461 original_type=3 x=-150.0 z=1850.0
P2_PLACEMENT_SLOT generator=211001 slot=5465461 actor=3 xyz=1 terrain=ground route=1 route_distance=61.2 x=-150.000 y=30.000 z=1850.000 water_depth=0.00
P2_PLACEMENT_SLOT generator=211002 slot=0 actor=3 xyz=1 terrain=ground route=1 route_distance=129.3 x=150.000 y=30.000 z=1550.000 water_depth=0.00
P2_ENEMY_READY species=BlueKochappy source_id=44 native_family=Chappy generator=211001 x=-150.0000000 y=30.0000000 z=1850.0000000 health=250.0 max_health=250.0 behavior=P1
P2_PLACEMENT_PROBE actors=2 evidence_slots=2
"""


def _strip(text, token):
    return "\n".join(line for line in text.splitlines() if token not in line)


def test_validator_passes_on_closed_chain():
    result = validate_cooccurrence(SAMPLE_LOG)
    assert result.ok, result.reason
    assert result.generator == 211001
    assert result.slot == 5465461
    assert result.source == ORANGE_SOURCE


def test_validator_flips_when_placement_marker_stripped():
    result = validate_cooccurrence(_strip(SAMPLE_LOG, "P2_PLACEMENT_SLOT"))
    assert not result.ok
    assert "no mapped P2_PLACEMENT_SLOT" in result.reason


def test_validator_flips_when_resolve_marker_stripped():
    result = validate_cooccurrence(_strip(SAMPLE_LOG, "P2_SEED_RESOLVE"))
    assert not result.ok
    assert "no P2_SEED_RESOLVE matched" in result.reason


def test_validator_flips_when_ready_marker_stripped():
    result = validate_cooccurrence(_strip(SAMPLE_LOG, "P2_ENEMY_READY"))
    assert not result.ok
    assert "P2_ENEMY_READY births" in result.reason


def test_validator_flips_on_slot_source_mismatch():
    bogus = SAMPLE_LOG.replace("source_id=44 target=5465461", "source_id=45 target=5465461")
    result = validate_cooccurrence(bogus)
    assert not result.ok


def test_validator_flips_on_non_cohort_source():
    bogus = SAMPLE_LOG.replace("source_id=44 target=5465461", "source_id=15 target=5465461")
    result = validate_cooccurrence(bogus)
    assert not result.ok
    assert "non-cohort" in result.reason


def test_validator_passes_on_two_generator_chain():
    both = """\
P2_SEED_RESOLVE source_id=44 target=5465461 original_type=3 x=-150.0 z=1850.0
P2_SEED_RESOLVE source_id=44 target=513430982 original_type=3 x=150.0 z=1550.0
P2_PLACEMENT_SLOT generator=211001 slot=5465461 actor=3 xyz=1 terrain=ground route=1 route_distance=61.2 x=-150.000 y=30.000 z=1850.000 water_depth=0.00
P2_PLACEMENT_SLOT generator=211002 slot=513430982 actor=3 xyz=1 terrain=ground route=1 route_distance=129.3 x=150.000 y=30.000 z=1550.000 water_depth=0.00
P2_ENEMY_READY species=BlueKochappy source_id=44 native_family=Chappy generator=211001 x=-150.0000000 y=30.0000000 z=1850.0000000 health=250.0
P2_ENEMY_READY species=BlueKochappy source_id=44 native_family=Chappy generator=211002 x=150.0000000 y=30.0000000 z=1550.0000000 health=250.0
P2_PLACEMENT_PROBE actors=2 evidence_slots=2
"""
    result = validate_cooccurrence(both)
    assert result.ok, result.reason
    assert result.generator == 211001
    assert result.slot == 5465461
    assert result.source == ORANGE_SOURCE



def _native_root():
    root = os.environ.get("PIKMIN_NATIVE_ROOT")
    if root and (Path(root) / "pc_port" / "pc_p2_placement_probe.cpp").is_file():
        return Path(root).resolve()
    candidate = ROOT / "native"
    if (candidate / "pc_port" / "pc_p2_placement_probe.cpp").is_file():
        return candidate.resolve()
    return None


def _read(rel):
    native = _native_root()
    if native is None:
        return ""
    path = native / rel
    return path.read_text(errors="replace") if path.is_file() else ""


@unittest.skipUnless(_native_root(), "native worktree not available (set PIKMIN_NATIVE_ROOT)")
class NativeSourcePinTests(unittest.TestCase):
    def test_placement_probe_emits_sidecar_slot(self):
        self.assertIn("P2_PLACEMENT_SLOT", _read("pc_port/pc_p2_placement_probe.cpp"))
        self.assertIn("p2-placement-slots.txt", _read("pc_port/pc_p2_placement_probe.cpp"))

    def test_seed_bridge_emits_resolve_marker(self):
        self.assertIn("P2_SEED_RESOLVE", _read("src/plugPikiNakata/genteki.cpp"))


def test_cohort_constants():
    assert SNOW_SOURCE == 45
    assert ORANGE_SOURCE == 44
