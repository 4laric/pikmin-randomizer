"""Fresh-arena proving harness for the retail cave generation provider
(lane cave-generate-provider, issue #129).

P0-adjacent tooling: stages a fresh preview arena, writes one decoded floor
manifest as p2-cave-generate.txt (pool/rooms/door-links/roster-minima from a
completed-P0 packet, never forked), boots the private product binary, and
asserts the native P2_CAVE_GENERATE_* markers match an independent
root-side recomputation. Transfer/restore behavior must be unchanged
(P2_CAVE_READY still fires; no invalid abort).

Normative sidecar rules (mirrored by native pc_p2_cave_generate.h; the
harness cross-checks native output so drift fails the run, not silently):
quarter-turn rotation identical to experimental.pikmin2_assembly.transform,
anchor = room-0 origin with radius clamped 20..150 over the largest room
diagonal, every door link must resolve to a staged unit/door.
"""
import json
import math
import os
import re
import struct
import subprocess
import sys
import uuid
from pathlib import Path

MAGIC = 'P2_CAVE_GENERATE_1'
TOKEN_RE = re.compile(r'[A-Za-z0-9_.$-]{1,128}$')


class ContractViolation(ValueError):
    """A sidecar or recomputation disagrees with the generation contract."""


def rotate(point, turn):
    """Quarter-turn rotation: turn t applies t times (x,z) -> (-z,x)."""
    if turn not in (0, 1, 2, 3) or len(point) != 3:
        raise ContractViolation('bad rotation input')
    x, y, z = (float(v) for v in point)
    if not all(math.isfinite(v) for v in (x, y, z)):
        raise ContractViolation('nonfinite rotation input')
    for _ in range(turn):
        x, z = -z, x
    return [x, y, z]


def room_bounds(w, d, turn, offset):
    """World-space AABB of one placed room; mirrors the native computation."""
    if not (w > 0 and d > 0) or turn not in (0, 1, 2, 3) or len(offset) != 3:
        raise ContractViolation('bad room geometry input')
    corners = []
    for sx in (-w / 2, w / 2):
        for sz in (-d / 2, d / 2):
            p = rotate([sx, 0.0, sz], turn)
            corners.append([p[0] + offset[0], offset[1], p[2] + offset[2]])
    lo = [min(c[i] for c in corners) for i in range(3)]
    hi = [max(c[i] for c in corners) for i in range(3)]
    return lo, hi


def derive_anchor(rooms, kind):
    """Transition anchor: room-0 origin; radius clamped 20..150."""
    if kind not in ('hole', 'geyser') or not rooms:
        raise ContractViolation('bad anchor input')
    diags = [math.hypot(r['w'], r['d']) / 2 for r in rooms]
    radius = max(20.0, min(150.0, max(diags)))
    origin = rooms[0]['offset']
    return {'kind': kind, 'x': origin[0], 'y': origin[1], 'z': origin[2],
            'radius': radius}


def check_token(value, dollar=False):
    """Sidecar token shape; raises on malformed names."""
    if not isinstance(value, str) or not TOKEN_RE.fullmatch(value):
        raise ContractViolation('malformed token: %r' % (value,))
    if value.startswith('$') and not dollar:
        raise ContractViolation('unexpected variant token: %r' % (value,))
    return value


def validate_sidecar(text):
    """Normative parse of one manifest sidecar; returns the manifest dict."""
    if not isinstance(text, str) or not text.strip():
        raise ContractViolation('empty sidecar')
    lines = [line.split() for line in text.splitlines()
             if line.strip() and not line.strip().startswith('#')]
    if not lines or lines[0] != [MAGIC]:
        raise ContractViolation('bad magic')
    pos = 1

    def take(kind):
        nonlocal pos
        if pos >= len(lines) or lines[pos][0] != kind:
            raise ContractViolation('expected %s section' % kind)
        row = lines[pos]
        pos += 1
        return row

    row = take('pool')
    if len(row) != 3:
        raise ContractViolation('bad pool row')
    pool, nunits = check_token(row[1]), int(row[2])
    if not 1 <= nunits <= 64:
        raise ContractViolation('bad unit count')
    units = []
    for i in range(nunits):
        row = take('unit')
        if len(row) != 6 or int(row[1]) != i:
            raise ContractViolation('bad unit row')
        w, d, kind = float(row[3]), float(row[4]), int(row[5])
        if not (w > 0 and d > 0) or kind < 0:
            raise ContractViolation('bad unit geometry')
        units.append({'name': check_token(row[2]), 'w': w, 'd': d, 'kind': kind})
    row = take('rooms')
    if len(row) != 2:
        raise ContractViolation('bad rooms row')
    rooms = []
    for i in range(int(row[1])):
        row = take('room')
        if len(row) != 7 or int(row[1]) != i:
            raise ContractViolation('bad room row')
        unit, turn = int(row[2]), int(row[3])
        if not 0 <= unit < nunits or turn not in (0, 1, 2, 3):
            raise ContractViolation('bad room reference')
        offset = [float(v) for v in row[4:7]]
        rooms.append({'unit': unit, 'turn': turn, 'offset': offset,
                      'w': units[unit]['w'], 'd': units[unit]['d']})
    if not rooms:
        raise ContractViolation('at least one room required')
    row = take('doors')
    doors = []
    for _ in range(int(row[1])):
        row = take('door')
        if len(row) != 4:
            raise ContractViolation('bad door row')
        unit, did, direction = int(row[1]), int(row[2]), int(row[3])
        if not 0 <= unit < nunits or did < 0 or direction not in (0, 1, 2, 3):
            raise ContractViolation('bad door reference')
        doors.append({'unit': unit, 'id': did, 'dir': direction})
    row = take('links')
    links = []
    for _ in range(int(row[1])):
        row = take('link')
        if len(row) != 6:
            raise ContractViolation('bad link row')
        unit, did, peer, pdoor = int(row[1]), int(row[2]), int(row[3]), int(row[4])
        dist = float(row[5])
        if not 0 <= unit < nunits or did < 0 or not 0 <= peer < nunits or pdoor < 0:
            raise ContractViolation('unresolvable link')
        if dist < 0 or not math.isfinite(dist):
            raise ContractViolation('bad link distance')
        links.append({'unit': unit, 'door': did, 'peer': peer,
                      'pdoor': pdoor, 'dist': dist})
    row = take('spawns')
    spawns = []
    for _ in range(int(row[1])):
        row = take('spawn')
        if len(row) != 3 or int(row[2]) < 1:
            raise ContractViolation('bad spawn row')
        spawns.append({'id': check_token(row[1], dollar=True), 'count': int(row[2])})
    if not spawns:
        raise ContractViolation('at least one spawn row required')
    row = take('anchor')
    if len(row) != 2 or row[1] not in ('hole', 'geyser'):
        raise ContractViolation('bad anchor row')
    if pos != len(lines):
        raise ContractViolation('trailing sidecar data')
    return {'pool': pool, 'units': units, 'rooms': rooms, 'doors': doors,
            'links': links, 'spawns': spawns, 'anchor_kind': row[1]}


def render_sidecar(manifest):
    """Canonical sidecar text for a validated manifest dict."""
    out = [MAGIC, 'pool %s %d' % (manifest['pool'], len(manifest['units']))]
    for i, unit in enumerate(manifest['units']):
        out.append('unit %d %s %g %g %d' % (i, unit['name'], unit['w'],
                                            unit['d'], unit['kind']))
    out.append('rooms %d' % len(manifest['rooms']))
    for i, room in enumerate(manifest['rooms']):
        out.append('room %d %d %d %g %g %g' % (
            i, room['unit'], room['turn'], *room['offset']))
    out.append('doors %d' % len(manifest['doors']))
    for door in manifest['doors']:
        out.append('door %d %d %d' % (door['unit'], door['id'], door['dir']))
    out.append('links %d' % len(manifest['links']))
    for link in manifest['links']:
        out.append('link %d %d %d %d %g' % (
            link['unit'], link['door'], link['peer'], link['pdoor'], link['dist']))
    out.append('spawns %d' % len(manifest['spawns']))
    for spawn in manifest['spawns']:
        out.append('spawn %s %d' % (spawn['id'], spawn['count']))
    out.append('anchor %s' % manifest['anchor_kind'])
    return '\n'.join(out) + '\n'


def manifest_from_packet(packet, floor_number, unit_defs, room_offset_step=600.0):
    """Build a generator manifest from a completed-P0 packet floor.

    Pool + roster minima come from the packet as-is (source_token with
    minimum_count; zero-minimum rows are skipped and the skip count
    reported, never hidden). Unit geometry (cells/kind/doors) comes from
    unit_defs {pool: [unit_definition dicts]} decoded by the caller with
    the shared unit_definition parser. Rooms place each pool unit once in
    a row; the anchor kind follows floor parity (odd hole / even geyser is
    harness shaping, not retail semantics).
    """
    floors = packet.get("floors") or []
    row = next((f for f in floors if f.get("first_floor") == floor_number), None)
    if row is None:
        raise ContractViolation("packet has no floor %d" % floor_number)
    pool = row["parameters"]["f008"]
    pool_units = (unit_defs or {}).get(pool)
    if not pool_units:
        raise ContractViolation("no unit data for pool %s" % pool)
    units, doors, links = [], [], []
    for unit in pool_units:
        idx = len(units)
        cells = unit["cells"]
        units.append({"name": unit["name"], "w": cells[0],
                      "d": cells[1], "kind": unit["kind"]})
        for door in unit["doors"]:
            doors.append({"unit": idx, "id": door["id"],
                          "dir": door["direction"]})
            for peer in door["links"]:
                links.append({"unit": idx, "door": door["id"],
                              "peer": idx, "pdoor": peer["door"],
                              "dist": peer["distance"]})
    rooms = [{"unit": i, "turn": i % 4,
              "offset": [i * room_offset_step, 0.0, 0.0],
              "w": u["w"], "d": u["d"]} for i, u in enumerate(units)]
    spawns, skipped = [], 0
    for enemy in row.get("enemies", []):
        source = enemy.get("source", enemy)
        minimum = source.get("minimum_count", 0)
        if minimum < 1:
            skipped += 1
            continue
        spawns.append({"id": source["source_token"], "count": minimum})
    if not spawns:
        raise ContractViolation("no positive roster minima on floor %d" % floor_number)
    return {"pool": pool, "units": units, "rooms": rooms,
            "doors": doors, "links": links, "spawns": spawns,
            "anchor_kind": "hole" if floor_number % 2 else "geyser",
            "skipped_zero_minima": skipped}


def _markers(text):
    return [line.strip() for line in text.splitlines()
            if 'P2_CAVE_GENERATE_' in line or line.strip().startswith('P2_CAVE_READY')]


def _parse_floats(line, keys):
    values = {}
    for key in keys:
        marker = key + '='
        at = line.find(marker)
        if at < 0:
            raise ContractViolation('marker lacks %s: %s' % (key, line))
        chunk = line[at + len(marker):].split()[0]
        try:
            values[key] = float(chunk)
        except ValueError:
            raise ContractViolation('non-numeric %s: %s' % (key, line))
    return values


def verify_run(text, manifest, tol=0.002):
    """Assert native markers match the independent recomputation."""
    lines = _markers(text)
    if any('P2_CAVE_GENERATE_REFUSED' in line for line in lines):
        raise ContractViolation('native refused the manifest')
    ready = [line for line in text.splitlines() if 'P2_CAVE_READY' in line]
    if not ready:
        raise ContractViolation('existing P2_CAVE_READY missing; behavior changed')
    if any('Invalid P2 cave entry' in line for line in text.splitlines()):
        raise ContractViolation('entry invalid abort fired')
    pool = next((line for line in lines if 'P2_CAVE_GENERATE_POOL' in line), None)
    if pool is None or 'pool=%s' % manifest['pool'] not in pool:
        raise ContractViolation('pool marker mismatch')
    rooms = [line for line in lines if 'P2_CAVE_GENERATE_ROOM' in line]
    if len(rooms) != len(manifest['rooms']):
        raise ContractViolation('room marker count mismatch')
    for line, room in zip(rooms, manifest['rooms']):
        got = _parse_floats(line, ('x0', 'y0', 'z0', 'x1', 'y1', 'z1'))
        lo, hi = room_bounds(room['w'], room['d'], room['turn'], room['offset'])
        for key, want in zip(('x0', 'y0', 'z0', 'x1', 'y1', 'z1'), lo + hi):
            if abs(got[key] - want) > tol:
                raise ContractViolation('room bounds drift: %s' % line)
    spawns = [line for line in lines if 'P2_CAVE_GENERATE_SPAWN' in line]
    want = [(s['id'], str(s['count'])) for s in manifest['spawns']]
    got = [(line.split('id=')[1].split()[0], line.split('count=')[1].split()[0]) for line in spawns]
    if sorted(' '.join(pair) for pair in got) != sorted(' '.join(pair) for pair in want):
        raise ContractViolation('spawn marker set mismatch')
    links = next((line for line in lines if 'P2_CAVE_GENERATE_LINKS' in line), None)
    if links is None or 'total=%d' % len(manifest['links']) not in links:
        raise ContractViolation('link marker mismatch')
    anchor = next((line for line in lines if 'P2_CAVE_GENERATE_ANCHOR' in line), None)
    want_anchor = derive_anchor(manifest['rooms'], manifest['anchor_kind'])
    if anchor is None or 'kind=%s' % want_anchor['kind'] not in anchor:
        raise ContractViolation('anchor marker mismatch')
    got_anchor = _parse_floats(anchor, ('x', 'y', 'z', 'radius'))
    for key in ('x', 'y', 'z', 'radius'):
        if abs(got_anchor[key] - want_anchor[key]) > tol:
            raise ContractViolation('anchor drift: %s' % anchor)
    done = next((line for line in lines if 'P2_CAVE_GENERATE_PASS' in line), None)
    if done is None:
        raise ContractViolation('PASS marker missing')
    return {'rooms': len(rooms), 'spawns': len(spawns),
            'links': len(manifest['links']), 'anchor': want_anchor}
