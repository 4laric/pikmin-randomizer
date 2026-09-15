"""Focused contract tests for ``randomizer.p2_placement_probe``.

The module under test is produced by a parallel worker and must satisfy the
production-marker contract: markers use ``generator``/``slot``/``actor``/``xyz``
/``terrain``/``route``/``route_distance``/``water_depth`` fields, and the probe
document carries ``catalog_join`` and ``mapping``. These tests import the real
module unconditionally so a missing or outdated module fails loudly.
"""
import randomizer.p2_placement_probe as probe
import randomizer.p2_placement_native as native


GROUND_211001 = (
    'P2_PLACEMENT_SLOT generator=211001 slot=1646783045 actor=3 xyz=1 '
    'terrain=ground route=1 route_distance=71.7 water_depth=0.00\n'
)


def _single(text):
    slots, _, _ = probe.capture_markers(text)
    assert len(slots) == 1
    return slots[0]


def test_capture_production_ground_marker():
    slot = _single(GROUND_211001)
    assert slot['generator'] == 211001
    assert slot['slot'] == 1646783045
    assert slot['xyz'] is True
    assert slot['terrain'] is True
    assert slot['route'] is True
    assert slot['terrain_class'] == 'ground'
    assert slot['route_distance'] == 71.7
    assert slot['water_depth'] == 0.0


def test_capture_no_terrain_marker():
    slot = _single(
        'P2_PLACEMENT_SLOT generator=99 slot=0 actor=3 xyz=0 terrain=none '
        'route=0 route_distance=-1.0 water_depth=0.00\n'
    )
    assert slot['xyz'] is False
    assert slot['terrain'] is False
    assert slot['terrain_class'] == 'none'
    assert slot['slot'] is None


def test_capture_unmapped_slot_zero_is_none():
    slot = _single(
        'P2_PLACEMENT_SLOT generator=55 slot=0 actor=3 xyz=1 terrain=ground '
        'route=1 route_distance=12.0 water_depth=0.00\n'
    )
    assert slot['terrain'] is True
    assert slot['slot'] is None


def test_capture_water_marker():
    slot = _single(
        'P2_PLACEMENT_SLOT generator=7 slot=123 actor=3 xyz=1 terrain=water '
        'route=1 route_distance=5.0 water_depth=2.50\n'
    )
    assert slot['terrain'] is True
    assert slot['terrain_class'] == 'water'
    assert slot['slot'] == 123
    assert slot['water_depth'] == 2.5


def test_capture_ignores_malformed_and_captures_window_summary():
    text = (
        'unrelated log line\n'
        + 'P2_PLACEMENT_SLOT generator=broken slot=1 actor=3 xyz=1 terrain=ground route=1 route_distance=1.0 water_depth=0.00\n'
        + 'P2_PLACEMENT_SLOT generator=-1 slot=1 actor=3 xyz=1 terrain=ground route=1 route_distance=1.0 water_depth=0.00\n'
        + GROUND_211001
        + 'window set to 960x540 (native)\n'
        + 'P2_PLACEMENT_PROBE actors=1 evidence_slots=1\n'
    )
    slots, window, summary = probe.capture_markers(text)
    assert [s['generator'] for s in slots] == [211001]
    assert window is not None
    assert 'window set to 960x540' in window
    assert summary == ['P2_PLACEMENT_PROBE actors=1 evidence_slots=1']


def test_build_probe_catalog_join():
    text = (
        'P2_PLACEMENT_SLOT generator=999 slot=0 actor=3 xyz=0 terrain=none '
        'route=0 route_distance=-1.0 water_depth=0.00\n'
        + GROUND_211001
        + 'window set to 960x540 (native)\n'
        + 'P2_PLACEMENT_PROBE actors=2 evidence_slots=2\n'
    )
    doc = probe.build_probe(text)
    assert doc['catalog_join'] is True
    assert doc['mapping'] == [{'generator': 211001, 'slot': 1646783045}]
    by_uid = {s['uid']: s for s in doc['slots']}
    assert by_uid[1646783045]['terrain'] is True
    assert by_uid[999]['uid'] == 999
    assert native.normalize_probe({'schema': doc['schema'], 'slots': doc['slots']})  # no raise


def test_build_probe_arena_only():
    text = (
        'P2_PLACEMENT_SLOT generator=1 slot=0 actor=3 xyz=1 terrain=ground '
        'route=1 route_distance=10.0 water_depth=0.00\n'
        + 'P2_PLACEMENT_SLOT generator=2 slot=0 actor=3 xyz=0 terrain=none '
        'route=0 route_distance=-1.0 water_depth=0.00\n'
    )
    doc = probe.build_probe(text)
    assert doc['catalog_join'] is False
    assert doc['mapping'] == []
    assert [s['uid'] for s in doc['slots']] == [1, 2]


def test_probe_schema_constant():
    assert probe.PROBE_SCHEMA == native.PROBE_SCHEMA == 'p2-placement-probe-v1'
