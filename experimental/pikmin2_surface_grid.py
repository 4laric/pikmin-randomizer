"""Conservative P1 static collision broad phase; does not resolve P2 adjacency."""
import math
import struct

from experimental.pikmin2_collision import chunk

CELL = 64.0  # BaseShape's loader also hardcodes 64 when checking cell bounds.
MAX_CELLS = 1_000_000
MAX_REFERENCES = 16_000_000


def f32(value):
    return struct.unpack('>f', struct.pack('>f', value))[0]


def build_grid(vertices, triangles):
    if not vertices or not triangles or len(triangles) > 32767:
        raise ValueError('Invalid native triangle/vertex count')
    if any(len(v) != 3 or any(not math.isfinite(x) or abs(x) > 1e7 for x in v) for v in vertices):
        raise ValueError('Nonfinite or excessive vertex coordinates')
    if any(len(t) != 3 or any(type(i) is not int or i < 0 or i >= len(vertices) for i in t) for t in triangles):
        raise ValueError('Invalid triangle vertex index')
    vertices = [[f32(x) for x in v] for v in vertices]
    # Bounds are serialized floats, so calculate membership from those exact values.
    lo = [f32(min(v[i] for v in vertices) - CELL) for i in range(3)]
    hi = [f32(max(v[i] for v in vertices) + CELL) for i in range(3)]
    nx, nz = [math.ceil((hi[i] - lo[i]) / CELL) + 1 for i in (0, 2)]
    if nx * nz > MAX_CELLS:
        raise ValueError('Native grid span exceeds cell limit')
    cells = [[] for _ in range(nx * nz)]
    refs = 0
    for face, tri in enumerate(triangles):
        points = [vertices[i] for i in tri]
        spans = []
        for axis, count in ((0, nx), (2, nz)):
            a, b = min(p[axis] for p in points), max(p[axis] for p in points)
            # Include AABBs touching [cellMin-64, cellMin+128]. This deliberately
            # overincludes corners, vertical faces, and crossing/sliver triangles.
            first = max(0, math.ceil((a - lo[axis] - .001) / CELL - 2))
            last = min(count - 1, math.floor((b - lo[axis] + .001) / CELL + 1))
            spans.append((first, last))
        (x0, x1), (z0, z1) = spans
        refs += (x1-x0+1) * (z1-z0+1)
        if refs > MAX_REFERENCES:
            raise ValueError('Native grid reference budget exceeded')
        for z in range(z0, z1+1):
            for x in range(x0, x1+1):
                cells[z*nx+x].append(face)
    groups, ids, table = [], {}, []
    for cell in cells:
        key = tuple(cell)
        if not key:
            table.append(-1)
        else:
            if key not in ids:
                ids[key] = len(groups)
                groups.append(key)
            table.append(ids[key])
    return dict(min=lo, max=hi, cell_size=CELL, nx=nx, nz=nz,
                groups=groups, cells=table, triangle_count=len(triangles))


def encode_grid(grid):
    payload = bytes(24) + struct.pack('>7fiii', *grid['min'], *grid['max'], CELL,
                                     grid['nx'], grid['nz'], len(grid['groups']))
    for group in grid['groups']:
        if len(group) > 32767:
            raise ValueError('Native signed-short group overflow')
        payload += struct.pack('>hh', 0, len(group))  # no far-culling metadata
        payload += struct.pack('>'+'i'*len(group), *group)
    payload += struct.pack('>'+'i'*len(grid['cells']), *grid['cells'])
    return chunk(0x110, payload)


def decode_grid(data, triangle_count):
    """Strict independent reader of the native CollisionGrid binary contract."""
    if type(triangle_count) is not int or not 0 < triangle_count <= 32767:
        raise ValueError('Invalid native triangle count')
    if len(data) < 72 or len(data) % 32:
        raise ValueError('Truncated or unaligned collision grid')
    tag, size = struct.unpack_from('>II', data)
    if tag != 0x110 or size != len(data)-8 or any(data[8:32]):
        raise ValueError('Invalid collision grid chunk header')
    values = struct.unpack_from('>7fiii', data, 32)
    lo, hi, cell, nx, nz, n = list(values[:3]), list(values[3:6]), *values[6:]
    if not all(math.isfinite(v) for v in values[:7]) or cell != CELL or any(a >= b for a,b in zip(lo,hi)):
        raise ValueError('Invalid collision grid bounds/size')
    if nx <= 0 or nz <= 0 or nx*nz > MAX_CELLS or n < 0 or n > nx*nz:
        raise ValueError('Invalid collision grid dimensions/groups')
    cursor, groups, refs = 72, [], 0
    try:
        for _ in range(n):
            far, count = struct.unpack_from('>hh', data, cursor); cursor += 4
            if far != 0 or count <= 0:
                raise ValueError('Unsupported culling or invalid group count')
            refs += count
            if refs > MAX_REFERENCES: raise ValueError('Grid reference limit')
            group = list(struct.unpack_from('>'+'i'*count, data, cursor)); cursor += 4*count
            if any(i < 0 or i >= triangle_count for i in group) or group != sorted(set(group)):
                raise ValueError('Invalid source triangle reference')
            groups.append(group)
        cells = list(struct.unpack_from('>'+'i'*(nx*nz), data, cursor)); cursor += 4*nx*nz
    except struct.error as error:
        raise ValueError('Truncated collision grid records') from error
    if any(i < -1 or i >= n for i in cells) or len(data)-cursor >= 32 or any(data[cursor:]):
        raise ValueError('Invalid cell reference or trailing grid bytes')
    return dict(min=lo, max=hi, cell_size=cell, nx=nx, nz=nz, groups=groups,
                cells=cells, triangle_count=triangle_count)


def query_faces(grid, x, z):
    # C++ truncates toward zero, including for slightly negative coordinates.
    ix, iz = int((x-grid['min'][0])/CELL), int((z-grid['min'][2])/CELL)
    if ix < 0 or iz < 0 or ix >= grid['nx'] or iz >= grid['nz']: return []
    group = grid['cells'][iz*grid['nx']+ix]
    return [] if group == -1 else grid['groups'][group]
