"""P2 dry-room collision to P1 MOD; experimental, not a general map converter."""
import argparse
import json
import math
from pathlib import Path
import struct


def translate_mapcode(code):
    # P2 attributes are not the P1 material enum. This audited dry concrete room
    # uses 2 and 5; Emergence uses 1, 6 and 7, and Hole of Beasts'
    # cent2/cent3 rooms also use 0. These audited rooms' waterbox
    # files are empty. P2 navi.cpp uses the attribute for walking sounds;
    # P1 has no matching P2 surface palette, so these fall back to solid.
    # HoudaiShotGun.cpp also selects dry impact effects with 6, independently
    # of findWater. Exact footstep/impact effects remain unconverted.
    # Preserve slip/bald bits, but do not interpret 7 as a P1 material enum.
    if code & 15 not in (0, 1, 2, 5, 6, 7):
        raise ValueError(f"Unaudited P2 material {code & 15}")
    return (((code >> 4) & 3) << 27) | ((not (code & 64)) << 25)


def plane(vertices, tri):
    a, b, c = (vertices[i] for i in tri)
    u = [b[i]-a[i] for i in range(3)]
    v = [c[i]-a[i] for i in range(3)]
    n = [v[1]*u[2]-v[2]*u[1], v[2]*u[0]-v[0]*u[2], v[0]*u[1]-v[1]*u[0]]
    length = math.sqrt(sum(x*x for x in n))
    if length < 1e-8:
        raise ValueError('Degenerate collision triangle')
    n = [x/length for x in n]
    return (*n, sum(n[i]*a[i] for i in range(3)))


# Lane 49: P1 attribute (bits 29-31) the engine already consumes for water
# (`MapCode::getAttribute == ATTR_Water` -> waypoint InWater, path avoidance and
# `ActTransport::useWaterRoute`). P2's own water is a separate SeaMgr volume, so
# this is a converter-side approximation: submerged upward-facing floor
# triangles are re-tagged water. Only water-unit conversion opts in.
ATTR_WATER = 5


def water_tagged_mapcodes(room, codes, boxes):
    """Return ``codes`` with P1 ``ATTR_Water`` set on triangles inside a box.

    A triangle qualifies when it is upward-facing (a walkable floor), its
    centroid XZ lies inside a box (1-unit tolerance) and its centroid Y is at or
    below the box surface (plus the source surface-3 admission tolerance). The
    exact P2 predicate has no lower-Y test; the P1 attribute is a surface tag, so
    only floors are marked here.
    """
    vertices = room['vertices']
    result = list(codes)
    for index, tri in enumerate(room['triangles']):
        nx, ny, nz, _ = plane(vertices, tri)
        if ny <= 0.01:
            continue
        cx = sum(vertices[v][0] for v in tri) / 3.0
        cy = sum(vertices[v][1] for v in tri) / 3.0
        cz = sum(vertices[v][2] for v in tri) / 3.0
        for box in boxes:
            low, high = box['min'], box['max']
            if (low[0] - 1.0 <= cx <= high[0] + 1.0 and low[2] - 1.0 <= cz <= high[2] + 1.0
                    and cy <= box['surface'] + 3.0):
                result[index] = (result[index] & ~(7 << 29)) | (ATTR_WATER << 29)
                break
    return result


def collision_geometry(room, cap_exits=False, *, mapcode_translator=translate_mapcode,
                       water_boxes=None):
    vertices = [list(v) for v in room['vertices']]
    triangles = [list(t) for t in room['triangles']]
    codes = [mapcode_translator(c) for c in room['mapcodes']]
    if len(codes) != len(triangles):
        raise ValueError('Mapcode count mismatch')
    if water_boxes:
        codes = water_tagged_mapcodes(room, codes, water_boxes)
    if cap_exits:
        lo, hi = room['bounds']['min'], room['bounds']['max']
        # Reversed face winding creates inward normals under P1 conventions. Boundary
        # walls intentionally overlap existing walls; they never add a floor.
        corners = [(lo[0],lo[2]), (hi[0],lo[2]), (hi[0],hi[2]), (lo[0],hi[2])]
        for i, (x,z) in enumerate(corners):
            xx,zz = corners[(i+1)%4]
            k=len(vertices)
            vertices.extend([[x,lo[1]-100,z],[xx,lo[1]-100,zz],[xx,hi[1],zz],[x,hi[1],z]])
            triangles.extend([[k,k+2,k+1],[k,k+3,k+2]])
            codes.extend([0,0])
    for tri in triangles:
        if len(tri)!=3 or any(i<0 or i>=len(vertices) for i in tri):
            raise ValueError('Invalid triangle vertex index')
        plane(vertices,tri)
    return vertices, triangles, codes


def adjacency(triangles):
    result=[[-1]*3 for _ in triangles]
    edges={}
    for i,t in enumerate(triangles):
        for e in range(3):
            key=tuple(sorted((t[e],t[(e+1)%3])))
            edges.setdefault(key,[]).append((i,e))
    for peers in edges.values():
        if len(peers)>2:
            raise ValueError('Nonmanifold triangle edge')
        if len(peers)==2:
            (i,e),(j,f)=peers
            result[i][e]=j
            result[j][f]=i
    return result


def chunk(tag,payload):
    data=struct.pack('>II',tag,0)+payload
    data+=bytes((-len(data))%32)
    return data[:4]+struct.pack('>I',len(data)-8)+data[8:]


def collision_chunks(vertices, triangles, mapcodes, vertex_offset=0, start_offset=0):
    if start_offset%32:
        raise ValueError('MOD chunks must start on a 32-byte boundary')
    neighbors=adjacency(triangles)
    p=struct.pack('>II',len(triangles),1)+bytes(16) # global offset32
    p+=struct.pack('>i',0)+bytes(28) # one room bound to joint0; triangles at64
    for i,t in enumerate(triangles):
        p+=struct.pack('>IIIIhhhhffff',mapcodes[i],*(j+vertex_offset for j in t),0,*neighbors[i],*plane(vertices,t))
    prism=chunk(0x100,p)
    # Conservative small-room grid: every cell references every triangle. Avoids
    # transplanting P2's incompatible acceleration structure or culling walls.
    lo=[min(v[i] for v in vertices)-64 for i in range(3)]
    hi=[max(v[i] for v in vertices)+64 for i in range(3)]
    nx=math.ceil((hi[0]-lo[0])/64)+1
    nz=math.ceil((hi[2]-lo[2])/64)+1
    p=bytes(24)+struct.pack('>7fiii',*lo,*hi,64.,nx,nz,1)
    p+=struct.pack('>hh',0,len(triangles))
    p+=b''.join(struct.pack('>i',i) for i in range(len(triangles)))
    p+=bytes(4*nx*nz)
    return prism+chunk(0x110,p)


def route_ini(routes):
    ids={p['id'] for p in routes}
    if len(ids)!=len(routes): raise ValueError('Duplicate route ID')
    lines=['route {',' id test'," name 'P2 room prototype'",' colour 255 255 0 255']
    for p in routes:
        lines.extend([' point {',f"  index {p['id']}",'  state 1','  pos '+' '.join(str(x) for x in p['position']),f"  width {p['radius']}",' }'])
    for p in routes:
        for other in p['links']:
            if other not in ids: raise ValueError('Missing route destination')
            lines.append(f" link {{ {p['id']} {other} }}")
    return '\n'.join(lines+['}',''])


def attach_collision(mod, room, cap_exits=False, *, mapcode_translator=translate_mapcode,
                     water_boxes=None):
    vertices,triangles,codes=collision_geometry(room,cap_exits,mapcode_translator=mapcode_translator,
                                                water_boxes=water_boxes)
    chunks=[]
    cursor=0
    offset=None
    while cursor<len(mod):
        tag,size=struct.unpack_from('>II',mod,cursor)
        part=mod[cursor:cursor+8+size]
        if tag==0xFFFF: break
        if tag in (0x100,0x110): raise ValueError('MOD already has collision')
        if tag==0x10:
            offset=struct.unpack_from('>I',part,8)[0]
            p=struct.pack('>I',offset+len(vertices))+bytes(20)
            p+=part[32:32+offset*12]
            p+=b''.join(struct.pack('>fff',*v) for v in vertices)
            part=chunk(tag,p)
        chunks.append(part)
        cursor+=8+size
    if offset is None: raise ValueError('Missing MOD vertex chunk')
    data=b''.join(chunks)
    data+=collision_chunks(vertices,triangles,codes,offset,len(data))
    data+=chunk(0xFFFF,b'')
    data+=route_ini(room['routes']).encode('ascii')
    return data



def ground_height(vertices, triangles, x, z, ceiling=10000):
    """Mirror P1 positive-Y plane and inward edge tests for offline probes."""
    heights=[]
    for tri in triangles:
        nx,ny,nz,d=plane(vertices,tri)
        if ny<=0.01: continue
        y=(d-nx*x-nz*z)/ny
        if y>ceiling: continue
        valid=True
        for i in range(3):
            a=vertices[tri[i]];b=vertices[tri[(i+1)%3]]
            ex,ey,ez=(b[j]-a[j] for j in range(3))
            inward=(ey*nz-ez*ny,ez*nx-ex*nz,ex*ny-ey*nx)
            if sum(inward[j]*(p-a[j]) for j,p in enumerate((x,y,z))) < -0.001:
                valid=False
                break
        if valid: heights.append(y)
    return max(heights) if heights else None



def decode_room(texts, *, mapcode_translator=translate_mapcode):
    """Decode locally extracted P2 grid/mapcode/routes; no research-script dependency.

    P2 acceleration data is intentionally discarded and replaced by the P1 grid.
    Models/textures are converted separately. Proprietary source data stays local.
    """
    texts=Path(texts)
    data=(texts/'grid.bin').read_bytes()
    cursor=0
    def take(fmt):
        nonlocal cursor
        size=struct.calcsize('>'+fmt)
        if cursor+size>len(data): raise ValueError('Truncated P2 grid')
        values=struct.unpack_from('>'+fmt,data,cursor)
        cursor+=size
        return values
    count,=take('I')
    if not 0<count<=(len(data)-cursor)//12:
        raise ValueError('Invalid vertex count')
    vertices=[list(take('3f')) for _ in range(count)]
    count,=take('I')
    if not 0<count<=(len(data)-cursor)//76:
        raise ValueError('Invalid triangle count')
    triangles=[];planes=[]
    for _ in range(count):
        triangles.append(list(take('3I')))
        planes.append(list(take('16f')))
    if not all(math.isfinite(x) for row in vertices+planes for x in row):
        raise ValueError('Nonfinite geometry')
    codes=(texts/'mapcode.bin').read_bytes()
    if len(codes)!=count+4 or struct.unpack_from('>I',codes)[0]!=count:
        raise ValueError('Mapcode count mismatch')
    def tokens(name):
        source=(texts/name).read_text(encoding='utf-8')
        return iter(' '.join(line.split('#')[0] for line in source.splitlines()).replace('{',' ').replace('}',' ').split())
    routes=[]
    try:
        tok=tokens('route.txt')
        count=int(next(tok))
        if count<0: raise ValueError('Negative route count')
        for _ in range(count):
            index=int(next(tok));nlinks=int(next(tok))
            if nlinks<0: raise ValueError('Negative link count')
            links=[int(next(tok)) for _ in range(nlinks)]
            position=[float(next(tok)) for _ in range(3)]
            radius=float(next(tok))
            if radius<0 or not all(math.isfinite(x) for x in position+[radius]):
                raise ValueError('Invalid route coordinates')
            routes.append(dict(id=index,links=links,position=position,radius=radius))
        if next(tok,None) is not None: raise ValueError('Trailing route tokens')
        spawns=[]
        if (texts/'layout.txt').exists():
            tok=tokens('layout.txt');count=int(next(tok))
            if count<0: raise ValueError('Negative spawn count')
            for _ in range(count):
                kind=int(next(tok));position=[float(next(tok)) for _ in range(3)]
                angle=float(next(tok));radius=float(next(tok));lo=int(next(tok));hi=int(next(tok))
                if not all(math.isfinite(x) for x in position+[angle,radius]) or radius<0 or lo<0 or hi<lo:
                    raise ValueError('Invalid spawn data')
                spawns.append(dict(type=kind,position=position,angle=angle,radius=radius,min=lo,max=hi))
            if next(tok,None) is not None: raise ValueError('Trailing layout tokens')
    except StopIteration as error:
        raise ValueError('Truncated P2 route or layout') from error
    route_ini(routes) # validate IDs and destinations before writing runtime files
    room=dict(source=texts.parent.name,vertices=vertices,triangles=triangles,planes=planes,
              mapcodes=list(codes[4:]),routes=routes,spawns=spawns,
              bounds={name:[fn(v[i] for v in vertices) for i in range(3)] for name,fn in [('min',min),('max',max)]},
              unconverted_acceleration_bytes=len(data)-cursor)
    collision_geometry(room,mapcode_translator=mapcode_translator) # validate indices, degenerates and known material map
    return room


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    source=parser.add_mutually_exclusive_group(required=True)
    source.add_argument('--room',type=Path,help='Previously decoded intermediate JSON')
    source.add_argument('--texts',type=Path,help='Extracted P2 grid.bin/mapcode.bin/route.txt directory')
    parser.add_argument('--mod',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--cap-exits',action='store_true')
    args=parser.parse_args()
    room=decode_room(args.texts) if args.texts else json.loads(args.room.read_text())
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_bytes(attach_collision(args.mod.read_bytes(),room,args.cap_exits))
    args.output.with_suffix('.route.ini').write_text(route_ini(room['routes']),encoding='utf-8')
