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
the catalog join key, never the generator id.
"""
import re

PROBE_SCHEMA = 'p2-placement-probe-v1'

_SLOT_RE = re.compile(
    r'^P2_PLACEMENT_SLOT '
    r'generator=(?P<generator>\d+) '
    r'slot=(?P<slot>\d+) '
    r'actor=\d+ '
    r'xyz=(?P<xyz>[01]) '
    r'terrain=(?P<terrain>ground|water|none) '
    r'route=(?P<route>[01]) '
    r'route_distance=(?P<dist>-?[\d.]+) '
    r'water_depth=(?P<depth>-?[\d.]+)'
)


def capture_markers(text):
    """Parse native stdout into ``(slots, window_marker, summary)``.

    ``slots`` is a list of dicts::

        {'generator': int, 'slot': int|None, 'xyz': bool, 'terrain': bool,
         'route': bool, 'terrain_class': str, 'water_depth': float,
         'route_distance': float}

    ``slot`` is ``None`` when the marker's ``slot`` field is ``0`` (no sidecar
    mapping). ``terrain`` is True only when ``xyz`` is True AND the native class
    is ``ground`` or ``water``; a no-terrain or 'none' marker always yields
    ``terrain == False``. ``window_marker`` is the first line containing
    ``window set to 960x540`` (else None); ``summary`` holds the stripped
    ``P2_PLACEMENT_PROBE`` lines.
    """
    slots = []
    window = None
    for line in text.splitlines():
        if line.startswith('P2_PLACEMENT_SLOT '):
            match = _SLOT_RE.match(line)
            if not match:
                continue
            xyz = match.group('xyz') == '1'
            terrain_class = match.group('terrain')
            slot = int(match.group('slot'))
            slots.append({
                'generator': int(match.group('generator')),
                'slot': slot or None,
                'xyz': xyz,
                'terrain': xyz and terrain_class in ('ground', 'water'),
                'route': match.group('route') == '1',
                'terrain_class': terrain_class,
                'water_depth': float(match.group('depth')),
                'route_distance': float(match.group('dist')),
            })
        if 'window set to 960x540' in line:
            window = line.strip()
    summary = [l.strip() for l in text.splitlines() if l.startswith('P2_PLACEMENT_PROBE ')]
    return slots, window, summary


def build_probe(text):
    """Return a probe document for the placement-audit bridge.

    ::

        {'schema': PROBE_SCHEMA, 'catalog_join': bool,
         'mapping': [{'generator': int, 'slot': int}, ...],
         'slots': [{'uid': int, 'xyz': bool, 'terrain': bool, 'route': bool}, ...]}

    ``mapping`` lists only the sidecar-mapped pairs. ``catalog_join`` is True
    when at least one mapping exists. Each slot's ``uid`` is the catalog ``slot``
    when mapped, otherwise the ``generator`` id (arena-only).
    """
    slots, _, _ = capture_markers(text)
    mapping = [{'generator': s['generator'], 'slot': s['slot']} for s in slots if s['slot'] is not None]
    return {
        'schema': PROBE_SCHEMA,
        'catalog_join': bool(mapping),
        'mapping': mapping,
        'slots': [
            {'uid': (s['slot'] if s['slot'] is not None else s['generator']),
             'xyz': s['xyz'], 'terrain': s['terrain'], 'route': s['route']}
            for s in slots
        ],
    }
