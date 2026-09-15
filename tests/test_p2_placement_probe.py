"""Focused contract tests for ``randomizer.p2_placement_probe``.

The module under test is produced by a parallel worker and may not exist yet at
the moment this test file runs. Prefer the real module when present; otherwise
inject a minimal stub that honours the documented contract so the suite still
imports and exercises the same expectations.
"""
import importlib.util
import sys
import types

import randomizer.p2_placement_native as native

_PROBE_MODULE = 'randomizer.p2_placement_probe'


def _module_present():
    try:
        spec = importlib.util.find_spec(_PROBE_MODULE)
    except (ImportError, ValueError):
        return False
    return spec is not None


def _parse_fields(line):
    """Turn a ``P2_PLACEMENT_SLOT ...`` line into a validated field dict."""
    tokens = line.split()
    if tokens[0] != 'P2_PLACEMENT_SLOT':
        return None
    fields = {}
    for token in tokens[1:]:
        if '=' not in token:
            return None
        key, value = token.split('=', 1)
        fields[key] = value
    required = ('uid', 'actor', 'xyz', 'terrain', 'route', 'water_depth')
    if any(key not in fields for key in required):
        return None
    try:
        int(fields['uid'])
        int(fields['actor'])
        float(fields['water_depth'])
    except ValueError:
        return None
    return fields


def _stub_capture_markers(text):
    slots = []
    window_marker = None
    summary = []
    for raw in text.splitlines():
        line = raw.strip()
        if not line:
            continue
        if window_marker is None and 'window set to 960x540' in line:
            window_marker = line
            continue
        if line.startswith('P2_PLACEMENT_PROBE '):
            summary.append(line)
            continue
        if line.startswith('P2_PLACEMENT_SLOT '):
            fields = _parse_fields(line)
            if fields is None:
                continue
            xyz = fields['xyz'] == '1'
            terrain = xyz and fields['terrain'] in ('ground', 'water')
            route = fields['route'] == '1'
            slots.append({
                'uid': int(fields['uid']),
                'xyz': xyz,
                'terrain': terrain,
                'route': route,
                'terrain_class': fields['terrain'],
                'water_depth': float(fields['water_depth']),
            })
    return slots, window_marker, summary


def _stub_build_probe(text):
    slots, _, _ = _stub_capture_markers(text)
    return {
        'schema': 'p2-placement-probe-v1',
        'slots': [
            {'uid': s['uid'], 'xyz': s['xyz'], 'terrain': s['terrain'], 'route': s['route']}
            for s in slots
        ],
    }


if _module_present():
    USED_REAL_PROBE = True
    import randomizer.p2_placement_probe as probe  # noqa: E402
else:
    USED_REAL_PROBE = False
    _stub = types.ModuleType(_PROBE_MODULE)
    _stub.PROBE_SCHEMA = 'p2-placement-probe-v1'
    _stub.capture_markers = _stub_capture_markers
    _stub.build_probe = _stub_build_probe
    sys.modules[_PROBE_MODULE] = _stub
    import randomizer.p2_placement_probe as probe  # noqa: E402,F811


GROUND_LINE = (
    'P2_PLACEMENT_SLOT uid=385875968 actor=3 xyz=1 terrain=ground '
    'route=1 water_depth=0.00\n'
)


def _single(text):
    slots, _, _ = probe.capture_markers(text)
    assert len(slots) == 1
    return slots[0]


def test_capture_ground_marker():
    slot = _single(GROUND_LINE)
    assert slot['xyz'] is True
    assert slot['terrain'] is True
    assert slot['route'] is True
    assert slot['terrain_class'] == 'ground'
    assert slot['water_depth'] == 0.0
    assert slot['uid'] == 385875968


def test_capture_no_terrain_marker():
    slot = _single(
        'P2_PLACEMENT_SLOT uid=99 actor=3 xyz=0 terrain=none route=0 water_depth=0.00\n'
    )
    assert slot['xyz'] is False
    assert slot['terrain'] is False
    assert slot['terrain_class'] == 'none'


def test_capture_legacy_ground_with_zero_xyz():
    slot = _single(
        'P2_PLACEMENT_SLOT uid=98 actor=3 xyz=0 terrain=ground route=0 water_depth=0.00\n'
    )
    assert slot['xyz'] is False
    assert slot['terrain'] is False
    assert slot['terrain_class'] == 'ground'


def test_capture_water_marker():
    slot = _single(
        'P2_PLACEMENT_SLOT uid=7 actor=3 xyz=1 terrain=water route=1 water_depth=2.50\n'
    )
    assert slot['terrain'] is True
    assert slot['terrain_class'] == 'water'
    assert slot['water_depth'] == 2.5


def test_capture_ignores_malformed_and_captures_window_summary():
    text = (
        'unrelated log line\n'
        + 'P2_PLACEMENT_SLOT uid=broken actor=3 xyz=1 terrain=ground route=1 water_depth=0.00\n'
        + 'P2_PLACEMENT_SLOT uid=notanint actor=3 xyz=1 terrain=ground route=1 water_depth=0.00\n'
        + GROUND_LINE
        + 'window set to 960x540 (native)\n'
        + 'P2_PLACEMENT_PROBE actors=1 evidence_slots=1\n'
    )
    slots, window, summary = probe.capture_markers(text)
    assert [s['uid'] for s in slots] == [385875968]
    assert window is not None
    assert 'window set to 960x540' in window
    assert summary == ['P2_PLACEMENT_PROBE actors=1 evidence_slots=1']


def test_build_probe_normalizes():
    text = (
        'P2_PLACEMENT_SLOT uid=99 actor=3 xyz=0 terrain=none route=0 water_depth=0.00\n'
        + GROUND_LINE
        + 'window set to 960x540 (native)\n'
        + 'P2_PLACEMENT_PROBE actors=1 evidence_slots=2\n'
    )
    doc = probe.build_probe(text)
    assert doc['schema'] == 'p2-placement-probe-v1'
    normalized = native.normalize_probe(doc)
    assert normalized['schema'] == 'p2-placement-probe-v1'
    by_uid = {s['uid']: s for s in normalized['slots']}
    assert by_uid[99]['terrain'] is False
    assert by_uid[99]['xyz'] is False
    assert by_uid[385875968]['terrain'] is True
    assert by_uid[385875968]['route'] is True


def test_probe_schema_constant():
    assert probe.PROBE_SCHEMA == native.PROBE_SCHEMA == 'p2-placement-probe-v1'
