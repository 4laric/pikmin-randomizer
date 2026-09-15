"""Parse native ``P2_PLACEMENT_SLOT`` marker text into placement probe docs.

This is the root-side reader for the lane-04 native placement probe
(``pc_port/pc_p2_placement_probe``). The native marker records, per spawned Teki
actor, whether the spawn rests on terrain (``xyz``), its terrain class
(``terrain``), and whether it lies within the route graph's distance-capped
coverage radius (``route``). The native ``terrain`` class is ``none`` whenever no
ground triangle exists, so a destination-denied spawn can never be misread as
``ground``.

The marker's ``generator`` field is the generator's 4-byte file id (``_70``), not
a placement-catalog slot uid. We keep it as ``uid`` only because the probe
schema's slot key is named ``uid``; downstream tooling must not treat it as a
catalog slot.
"""
import re

PROBE_SCHEMA = 'p2-placement-probe-v1'

_SLOT_RE = re.compile(
    r'^P2_PLACEMENT_SLOT (?:generator|uid)=(?P<id>\d+) '
    r'actor=\d+ '
    r'xyz=(?P<xyz>[01]) '
    r'terrain=(?P<terrain>ground|water|none) '
    r'route=(?P<route>[01]) '
    r'(?:route_distance=(?P<dist>-?[\d.]+) )?water_depth=(?P<depth>-?[\d.]+)'
)


def capture_markers(text):
    """Parse native stdout into ``(slots, window_marker, summary)``.

    ``slots`` is a list of dicts::

        {'uid': int, 'xyz': bool, 'terrain': bool, 'route': bool,
         'terrain_class': str, 'water_depth': float, 'route_distance': float|None}

    ``terrain`` is True only when ``xyz`` is True AND the native class is
    ``ground`` or ``water``; a no-terrain or 'none' marker always yields
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
            dist = match.group('dist')
            slots.append({
                'uid': int(match.group('id')),
                'xyz': xyz,
                'terrain': xyz and terrain_class in ('ground', 'water'),
                'route': match.group('route') == '1',
                'terrain_class': terrain_class,
                'water_depth': float(match.group('depth')),
                'route_distance': float(dist) if dist is not None else None,
            })
        if 'window set to 960x540' in line:
            window = line.strip()
    summary = [l.strip() for l in text.splitlines() if l.startswith('P2_PLACEMENT_PROBE ')]
    return slots, window, summary


def build_probe(text):
    """Return a ``{'schema': PROBE_SCHEMA, 'slots': [...]}`` document."""
    slots, _, _ = capture_markers(text)
    return {
        'schema': PROBE_SCHEMA,
        'slots': [
            {'uid': slot['uid'], 'xyz': slot['xyz'], 'terrain': slot['terrain'], 'route': slot['route']}
            for slot in slots
        ],
    }
