"""Retail rigid bridge joints and platform triangles -> native dynamic MOD.

Each source joint receives its own parent wrapper because native dynamic joint
visibility operates on siblings. Vertices are baked once into model space.
"""
from pathlib import Path
import copy
import math
import struct
from experimental.pikmin2_convert import blocks, decode, write_model, u16, u32, Writer
from experimental.pikmin2_rigid import joint_matrices, apply
from experimental.pikmin2_collision import chunk, plane


def platforms(data, matrices):
    at = 0
    def take(fmt):
        nonlocal at
        result = struct.unpack_from('>'+fmt, data, at)
        at += struct.calcsize('>'+fmt)
        return result
    count, = take('I')
    if not 0 < count <= 64:
        raise ValueError('Unsupported platform count')
    joints = take('H'*count)
    size, = take('I')
    vertices = [take('3f') for _ in range(size)]
    def obb(depth=0):
        nonlocal at
        if depth > 64:
            raise ValueError('Invalid OBB nesting')
        take('50f')
        present, = take('B')
        if present:
            size, = take('I')
            if size > 100000:
                raise ValueError('Invalid OBB triangle index count')
            take('I'*size)
        children, = take('B')
        if children & ~3:
            raise ValueError('Invalid OBB child flags')
        if children & 1: obb(depth+1)
        if children & 2: obb(depth+1)
    result = []
    for joint in joints:
        if joint >= len(matrices):
            raise ValueError('Invalid platform joint')
        size, = take('I')
        triangles = []
        for _ in range(size):
            indices = take('3I')
            take('16f')
            if any(i >= len(vertices) for i in indices):
                raise ValueError('Invalid platform vertex')
            # Preserve source plane normal: native plane() uses reversed winding.
            triangles.append(tuple(reversed(indices)))
        obb()
        result.append((joint, [apply(matrices[joint], v) for v in vertices], triangles))
    if at != len(data):
        raise ValueError('Trailing platform bytes')
    return result


def convert_bridge(model, platform, output):
    b = blocks(model)
    matrices = joint_matrices(b)
    decoded = decode(model, approximate_materials=True, bake_rigid=True)
    mapping = {}
    h = b['INF1']; at = u32(h,20); current = 0; stack = []
    while True:
        kind, index = struct.unpack_from('>HH', h, at); at += 4
        if kind == 0: break
        if kind == 1: stack.append(current)
        elif kind == 2: current = stack.pop()
        elif kind == 0x10: current = index
        elif kind == 0x12: mapping[index] = current
    write_model(copy.deepcopy(decoded), output, 'retail bridge BMD')
    data = Path(output).read_bytes(); chunks = []; at = 0
    # Original root is native0; other source joints each get wrapper + leaf.
    leaf = lambda source: 0 if source == 0 else source*2
    joint_count = 1 + (len(matrices)-1)*2
    while at < len(data):
        tag, size = struct.unpack_from('>II', data, at); raw = bytearray(data[at:at+8+size])
        if tag == 80:
            cursor = 32
            for mesh in range(u32(raw,8)):
                struct.pack_into('>I', raw, cursor, leaf(mapping[mesh]))
                dl_size = u32(raw,cursor+30)
                cursor = (cursor+34+31)//32*32 + dl_size
        if tag == 96:
            writer = Writer(); writer.begin(96,joint_count); writer.pad()
            points = decoded[1][9]
            bounds = [min(v[k] for v in points) for k in range(3)] + [max(v[k] for v in points) for k in range(3)]
            for native in range(joint_count):
                parent = -1 if native==0 else 0 if native%2 else native-1
                source = native//2 if native%2==0 else None
                meshes = [m for m in reversed(decoded[0]['_draw_order']) if source is not None and mapping[m]==source]
                writer.put('iI6ff9fI',parent,0,*bounds,0.,1.,1.,1.,0.,0.,0.,0.,0.,0.,len(meshes))
                for mesh in meshes: writer.put('HH',mesh,mesh)
            writer.end();raw=writer.data
        if tag != 65535: chunks.append(bytes(raw))
        at += 8+size
    # Source collision has shared local vertices, transformed per attached joint.
    geometry = platforms(platform, matrices)
    vertices = []; triangles = []; rooms = []
    for joint, points, faces in geometry:
        start = len(vertices); vertices.extend(points); rooms.append(leaf(joint))
        for face in faces: triangles.append((len(rooms)-1,tuple(start+i for i in face)))
    # Append platform vertices to the already-baked render position array.
    position_offset = len(decoded[1][9])
    for i, raw in enumerate(chunks):
        if u32(raw,0)==16:
            points = decoded[1][9]+vertices
            chunks[i]=chunk(16,struct.pack('>I',len(points))+bytes(20)+b''.join(struct.pack('>3f',*v) for v in points))
    payload=struct.pack('>II',len(triangles),len(rooms))+bytes(16)
    for joint in rooms: payload+=struct.pack('>i',joint)+bytes(28)
    for room, face in triangles:
        payload+=struct.pack('>IIIIhhhhffff',0x02000000,*(v+position_offset for v in face),room,-1,-1,-1,*plane(vertices,face))
    chunks.append(chunk(256,payload))
    lo=[min(v[k] for v in vertices)-64 for k in range(3)];hi=[max(v[k] for v in vertices)+64 for k in range(3)]
    nx=math.ceil((hi[0]-lo[0])/64)+1;nz=math.ceil((hi[2]-lo[2])/64)+1
    payload=bytes(24)+struct.pack('>7fiii',*lo,*hi,64.,nx,nz,1)+struct.pack('>hh',0,len(triangles))+b''.join(struct.pack('>i',i) for i in range(len(triangles)))+bytes(4*nx*nz)
    chunks.extend([chunk(272,payload),chunk(65535,b'')]);Path(output).write_bytes(b''.join(chunks))
    return {'source_joints':len(matrices),'native_joints':joint_count,'platforms':len(rooms),'platform_triangles':len(triangles),'render_shapes':len(mapping)}
