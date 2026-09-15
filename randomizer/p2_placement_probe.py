"""Parse native ``P2_PLACEMENT_SLOT`` marker text into placement probe docs.

This is the root-side reader for the lane-04 native placement probe
(``pc_port/pc_p2_placement_probe``). The native marker records, per spawned Teki
actor, whether the spawn rests on terrain (``xyz``), its terrain class
(``terrain``), and whether it lies within the route graph's distance-capped
coverage radius (``route``). The native ``terrain`` class is ``none`` whenever no
ground triangle exists, so a destination-denied spawn can never be misread as
``ground``.

Each marker carries two ids: ``generator`` (the generator's 4-byte file id
``_70``) and ``slot`` (the placement-catalog slot uid read from a staged
``p2-placement-slots.txt`` sidecar; ``0`` when no mapping exists). The slot is
the catalog join key, never the generator id, so ``build_probe`` leaves unmapped
generators out of the stampable ``slots`` list and reports them explicitly.

The parser is token-based and tolerant: ``slot``, ``route_distance`` and
``x``/``y``/``z`` are optional, and ``generator`` may also appear as the legacy
``uid`` alias, so both current and older marker texts parse.
"""
import re

PROBE_SCHEMA = 'p2-placement-probe-v1'

_SLOT_PREFIX = 'P2_PLACEMENT_SLOT '


def _parse_slot_line(raw):
    parts = raw.split()
    if not parts or parts[0] != 'P2_PLACEMENT_SLOT':
        return None
    fields = {}
    for token in parts[1:]:
        if '=' not in token:
            return None
        key, value = token.split('=', 1)
        fields[key] = value
    required = ('xyz', 'terrain', 'route', 'water_depth')
    if not any(key in fields for key in ('generator', 'uid')) or any(key not in fields for key in required):
        return None
    try:
        generator = int(fields.get('generator', fields.get('uid')))
        xyz = fields['xyz'] == '1'
        terrain_class = fields['terrain']
        route = fields['route'] == '1'
        water_depth = float(fields['water_depth'])
        slot = int(fields.get('slot', '0'))
        route_distance = float(fields['route_distance']) if 'route_distance' in fields else None
        if {'x', 'y', 'z'} <= set(fields):
            position = [float(fields['x']), float(fields['y']), float(fields['z'])]
        else:
            position = None
    except (KeyError, ValueError):
        return None
    return {
        'generator': generator,
        'slot': slot or None,
        'xyz': xyz,
        'terrain': xyz and terrain_class in ('ground', 'water'),
        'route': route,
        'terrain_class': terrain_class,
        'water_depth': water_depth,
        'route_distance': route_distance,
        'position': position,
    }


def capture_markers(text):
    """Parse native stdout into ``(slots, window_marker, summary)``.

    ``slots`` is a list of dicts::

        {'generator': int, 'slot': int|None, 'xyz': bool, 'terrain': bool,
         'route': bool, 'terrain_class': str, 'water_depth': float,
         'route_distance': float|None, 'position': [x, y, z]|None}

    ``slot`` is ``None`` when the marker's ``slot`` field is absent or ``0``.
    ``terrain`` is True only when ``xyz`` is True AND the native class is
    ``ground`` or ``water``. ``window_marker`` is the first line containing
    ``window set to 960x540`` (else None); ``summary`` holds the stripped
    ``P2_PLACEMENT_PROBE`` lines.
    """
    slots = []
    window = None
    for line in text.splitlines():
        if line.startswith(_SLOT_PREFIX):
            slot = _parse_slot_line(line)
            if slot is not None:
                slots.append(slot)
        if 'window set to 960x540' in line:
            window = line.strip()
    summary = [l.strip() for l in text.splitlines() if l.startswith('P2_PLACEMENT_PROBE ')]
    return slots, window, summary


def build_probe(text):
    """Return a probe document for the placement-audit bridge.

    ::

        {'schema': PROBE_SCHEMA, 'catalog_join': bool,
         'mapping': [{'generator', 'slot', 'xyz', 'terrain', 'route', 'position'}, ...],
         'slots': [{'uid', 'xyz', 'terrain', 'route'}, ...],
         'unmapped_generators': [int, ...], 'malformed_markers': int}

    ``mapping`` lists only the sidecar-mapped slots (``slot`` not None); each
    entry keeps its sampled ``position``. ``slots`` is the stampable subset keyed
    by the catalog slot ``uid`` only — unmapped generators are NOT overloaded
    onto ``uid``. ``unmapped_generators`` lists generators whose ``slot`` was
    absent/0. ``malformed_markers`` counts ``P2_PLACEMENT_SLOT``-prefixed lines
    that failed to parse (for diagnostic visibility instead of silent drop).
    ``catalog_join`` is True when at least one mapping exists.
    """
    slots, _, _ = capture_markers(text)
    mapping = [
        {'generator': s['generator'], 'slot': s['slot'], 'xyz': s['xyz'],
         'terrain': s['terrain'], 'route': s['route'], 'position': s['position']}
        for s in slots if s['slot'] is not None
    ]
    unmapped = [s['generator'] for s in slots if s['slot'] is None]
    malicious = 0
    for line in text.splitlines():
        if line.startswith(_SLOT_PREFIX) and _parse_slot_line(line) is None:
            malicious += 1
    return {
        'schema': PROBE_SCHEMA,
        'catalog_join': bool(mapping),
        'mapping': mapping,
        'slots': [
            {'uid': m['slot'], 'xyz': m['xyz'], 'terrain': m['terrain'], 'route': m['route']}
            for m in mapping
        ],
        'unmapped_generators': unmapped,
        'malformed_markers': malicious,
    }
