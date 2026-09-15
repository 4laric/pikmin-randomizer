"""Contract tests for ``randomizer.p2_placement_probe`` (final v1 contract).

The final contract is token-based: each ``P2_PLACEMENT_SLOT <k>=<v> ...`` line is
split on whitespace into ``k=v`` tokens. Required keys are ``generator`` (legacy
alias ``uid``), ``xyz``, ``terrain``, ``route`` and ``water_depth``; optional
keys are ``slot`` (int, default 0), ``route_distance`` and ``x``/``y``/``z``.

``capture_markers`` returns ``(slots, window_marker, summary)`` with each slot::

    {'generator': int, 'slot': int|None, 'xyz': bool, 'terrain': bool, 'route': bool,
     'terrain_class': str, 'water_depth': float, 'route_distance': float|None,
     'position': [x, y, z]|None}

``build_probe`` returns a ``p2-placement-probe-v1`` document whose ``mapping``
lists only mapped pairs (each carrying xyz/terrain/route/position) and whose
``slots`` lists only mapped catalog slots; unmapped generators are collected in
``unmapped_generators``.
"""
import randomizer.p2_placement_probe as probe
import randomizer.p2_placement_native as native


GROUND_211001 = (
    'P2_PLACEMENT_SLOT generator=211001 slot=648204418 actor=3 xyz=1 '
    'terrain=ground route=1 route_distance=61.2 x=-150.0 y=30.0 z=1850.0 '
    'water_depth=0.00\n'
)


def _single(text):
    slots, _, _ = probe.capture_markers(text)
    assert len(slots) == 1
    return slots[0]


def test_capture_production_ground_marker():
    line = (
        'P2_PLACEMENT_SLOT generator=211001 slot=648204418 actor=3 xyz=1 '
        'terrain=ground route=1 route_distance=61.2 x=-150.0 y=30.0 z=1850.0 '
        'water_depth=0.00\n'
    )
    slot = _single(line)
    assert slot['generator'] == 211001
    assert slot['slot'] == 648204418
    assert slot['xyz'] is True
    assert slot['terrain'] is True
    assert slot['route'] is True
    assert slot['terrain_class'] == 'ground'
    assert slot['route_distance'] == 61.2
    assert slot['position'] == [-150.0, 30.0, 1850.0]


def test_capture_slice1_log_no_slot_field():
    slot = _single(
        'P2_PLACEMENT_SLOT generator=385875968 actor=3 xyz=1 terrain=ground '
        'route=1 route_distance=71.7 water_depth=0.00\n'
    )
    assert slot['slot'] is None
    assert slot['terrain'] is True
    assert slot['generator'] == 385875968


def test_capture_unmapped_slot_zero_and_no_position():
    slot = _single(
        'P2_PLACEMENT_SLOT generator=55 slot=0 actor=3 xyz=1 terrain=ground '
        'route=1 water_depth=0.00\n'
    )
    assert slot['slot'] is None
    assert slot['position'] is None


def test_capture_no_terrain_marker():
    slot = _single(
        'P2_PLACEMENT_SLOT generator=99 xyz=0 terrain=none route=0 '
        'water_depth=0.00\n'
    )
    assert slot['xyz'] is False
    assert slot['terrain'] is False
    assert slot['terrain_class'] == 'none'


def test_capture_water_marker():
    slot = _single(
        'P2_PLACEMENT_SLOT generator=7 slot=123 xyz=1 terrain=water route=1 '
        'water_depth=2.5\n'
    )
    assert slot['terrain'] is True
    assert slot['terrain_class'] == 'water'
    assert slot['water_depth'] == 2.5


def test_capture_ignores_malformed_and_captures_window_summary():
    text = (
        'unrelated log line\n'
        + 'P2_PLACEMENT_SLOT generator=broken slot=1 actor=3 xyz=1 terrain=ground '
        'route=1 route_distance=1.0 water_depth=0.00\n'
        + 'P2_PLACEMENT_SLOT generator=1 xyz=1 terrain=ground route=1\n'
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
        GROUND_211001
        + 'P2_PLACEMENT_SLOT generator=211002 slot=0 actor=3 xyz=0 terrain=none '
        'route=0 water_depth=0.00\n'
        + 'window set to 960x540 (native)\n'
        + 'P2_PLACEMENT_PROBE actors=2 evidence_slots=2\n'
    )
    doc = probe.build_probe(text)
    assert doc['catalog_join'] is True
    assert doc['mapping'] == [{
        'generator': 211001, 'slot': 648204418, 'xyz': True, 'terrain': True,
        'route': True, 'position': [-150.0, 30.0, 1850.0],
    }]
    assert doc['slots'] == [{'uid': 648204418, 'xyz': True, 'terrain': True, 'route': True}]
    assert doc['unmapped_generators'] == [211002]
    assert native.normalize_probe({'schema': doc['schema'], 'slots': doc['slots']})


def test_build_probe_arena_only():
    text = (
        'P2_PLACEMENT_SLOT generator=1 slot=0 actor=3 xyz=1 terrain=ground '
        'route=1 water_depth=0.00\n'
        + 'P2_PLACEMENT_SLOT generator=2 slot=0 actor=3 xyz=0 terrain=none '
        'route=0 water_depth=0.00\n'
    )
    doc = probe.build_probe(text)
    assert doc['catalog_join'] is False
    assert doc['mapping'] == []
    assert doc['slots'] == []
    assert doc['unmapped_generators'] == [1, 2]


def test_probe_schema_constant():
    assert probe.PROBE_SCHEMA == 'p2-placement-probe-v1'
    assert probe.PROBE_SCHEMA == native.PROBE_SCHEMA
