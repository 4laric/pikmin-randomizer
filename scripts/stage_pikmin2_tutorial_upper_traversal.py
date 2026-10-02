"""Fresh engineering start on unchanged complete tutorial terrain (#1177)."""
import hashlib
import json
import math
from pathlib import Path
import re
import struct

from experimental.pikmin2_surface_physics import in_water
from scripts.stage_pikmin2_surface_water import prepare as prepare_water

START_XZ = (-250., 1000.)
IDENTITY = 'c8598f04bb884ab396d126b8dfbed6a6ce78d2f6afc92e7b366a5e5c11ccc8d5'


def floor_at(room, x, z):
    """Read original upward faces; this staging query proves no live traversal."""
    candidates = []
    if not all(math.isfinite(v) for v in (x, z)):
        raise ValueError('Nonfinite spawn')
    for face, (tri, plane) in enumerate(zip(room['triangles'], room['planes'])):
        if plane[1] <= .01:
            continue
        a, b, c = (room['vertices'][v] for v in tri)
        den = (b[2]-c[2])*(a[0]-c[0])+(c[0]-b[0])*(a[2]-c[2])
        if abs(den) < 1e-9:
            continue
        u = ((b[2]-c[2])*(x-c[0])+(c[0]-b[0])*(z-c[2]))/den
        v = ((c[2]-a[2])*(x-c[0])+(a[0]-c[0])*(z-c[2]))/den
        if min(u, v, 1-u-v) >= -1e-6:
            y = u*a[1]+v*b[1]+(1-u-v)*c[1]
            if math.isfinite(y):
                candidates.append((y, face))
    if not candidates:
        raise ValueError('Spawn has no original upward floor')
    return max(candidates)


def starts(room, boxes):
    positions = []
    for i in range(20):
        x, z = START_XZ[0]-12+(i % 5)*6, START_XZ[1]-9+(i//5)*6
        y, face = floor_at(room, x, z)
        # Test settled feet and radius, not the disclosed +40 clearance.
        if any(in_water(box, (x, y, z), 10.) for box in boxes):
            raise ValueError('Starting Red footprint intersects source water')
        positions.append(dict(uid=i+1, position=[x, y+40., z], ground=y, face=face))
    return positions


def relocate(data, room, boxes):
    offsets = [m.start() for m in re.finditer(b'    0.0v', data)] + [len(data)]
    if len(offsets) != 21 or data[:4] != b'1.0v' or struct.unpack_from('>I', data, 20)[0] != 20:
        raise ValueError('Expected current twenty-Pikmin generator only')
    positions = starts(room, boxes)
    rows = []
    for (a, b), placement in zip(zip(offsets, offsets[1:]), positions):
        row = bytearray(data[a:b])
        if (row[72:76] != b'ikip' or row[80:84] != b'p00\x04'
                or row[88:92] != b'p01\x04' or struct.unpack_from('>i', row, 92)[0] != 1):
            raise ValueError('Expected native Red template; no species substitution')
        # Generator readID swaps Stream::readInt: IDs are little endian.
        struct.pack_into('<I', row, 8, placement['uid'])
        struct.pack_into('>3f', row, 48, *placement['position'])
        rows.append(bytes(row))
    y, _ = floor_at(room, *START_XZ)
    return b'1.0v'+struct.pack('>4fI', START_XZ[0], y+40., START_XZ[1], 0., 20)+b''.join(rows), positions


def prepare(assets, bundle, output):
    room = json.loads((bundle/'surface-geometry.json').read_bytes())
    boxes = json.loads((bundle/'surface-water.json').read_bytes())['boxes']
    if len(room['triangles']) != 5332 or len(room['routes']) != 102 or len(boxes) != 3:
        raise ValueError('Incomplete original tutorial inputs')
    starts(room, boxes)  # Refuse invalid placement before constructing an overlay.
    run = prepare_water(assets, bundle, IDENTITY, output)
    retained = {name: hashlib.sha256((run/'assets/dataDir/courses/p2tutorial'/name).read_bytes()).hexdigest()
                for name in ('full.mod', 'full.ini', 'full.water')}
    path = run/'assets/dataDir/stages/p2_tutorial/default.gen'
    data, positions = relocate(path.read_bytes(), room, boxes)
    path.write_bytes(data)
    y, _ = floor_at(room, *START_XZ)
    for name in ('init.gen', 'plants.gen', 'day.gen'):
        path = run/'assets/dataDir/stages/p2_tutorial'/name
        data = bytearray(path.read_bytes())
        if data[:4] != b'1.0v' or len(data) != 24 or struct.unpack_from('>I', data, 20)[0] != 0:
            raise ValueError('Unexpected empty generator boundary')
        struct.pack_into('>3f', data, 4, START_XZ[0], y+40., START_XZ[1])
        path.write_bytes(data)
    stage = run/'assets/dataDir/stages/p2_tutorial.ini'
    stage.write_bytes(re.sub(rb'(?m)^navi_start[^\r\n]*', b'navi_start -250.0 1000.0', stage.read_bytes()))
    assert retained == {name: hashlib.sha256((run/'assets/dataDir/courses/p2tutorial'/name).read_bytes()).hexdigest()
                        for name in retained}, 'Converted geometry/routes/water changed'
    files = [stage, *(run/'assets/dataDir/stages/p2_tutorial').glob('*.gen')]
    baseline = {}
    for original, name in (('full-surface-inputs.json', 'terrain-baseline-inputs.json'),
                           ('surface-water-inputs.json', 'water-baseline-inputs.json')):
        (run/original).rename(run/name)
        baseline[name] = hashlib.sha256((run/name).read_bytes()).hexdigest()
    record = dict(schema=1, issue=1177, source_receipt=IDENTITY, faces=5332, routes=102, waters=3,
                  starting_reds=20, engineering_spawn_clearance=40., original_spawns=positions,
                  captain_start=[START_XZ[0], y+40., START_XZ[1]],
                  pre_relocation_factory_records_sha256=baseline,
                  retained_course_sha256=retained, retail_generators=False, source_schedules=False,
                  actual_traversal=False, files={str(p.relative_to(run)): hashlib.sha256(p.read_bytes()).hexdigest() for p in files})
    (run/'upper-traversal-inputs.json').write_text(json.dumps(record, indent=2)+'\n')
    return run
