"""Opt-in full tutorial prisms with preserved ambiguous edge incidences."""
from collections import defaultdict
import struct

from experimental.pikmin2_collision import chunk, collision_geometry, plane, route_ini
from experimental.pikmin2_surface_grid import build_grid, encode_grid
from experimental.pikmin2_surface_physics import surface_mapcode


def source_neighbors(triangles):
    edges=defaultdict(list)
    for i,t in enumerate(triangles):
        for e in range(3):edges[tuple(sorted((t[e],t[(e+1)%3])))].append((i,e))
    neighbors=[[-1]*3 for _ in triangles]
    incidents=[]
    for edge,peers in sorted(edges.items()):
        if len(peers)==2:
            (i,e),(j,f)=peers;neighbors[i][e]=j;neighbors[j][f]=i
        elif len(peers)>2:
            # The native tutorial index reconstructs this exact list. Never put
            # an arbitrary source face into P1's single-neighbor legacy slot.
            incidents.append(dict(vertices=list(edge),incidents=[dict(face=i,edge=e) for i,e in peers]))
    return neighbors,incidents


def attach_surface_collision(mod,room):
    vertices,triangles,codes=collision_geometry(room,mapcode_translator=surface_mapcode)
    if len(triangles)>32767:raise ValueError('Native triangle count exceeds signed adjacency range')
    neighbors,incidents=source_neighbors(triangles)
    cursor=0;parts=[];offset=None;ended=False
    while cursor+8<=len(mod):
        tag,size=struct.unpack_from('>II',mod,cursor)
        end=cursor+8+size
        if end>len(mod) or end%32:raise ValueError('Truncated or unaligned MOD chunk')
        part=mod[cursor:end]
        if tag==0xffff:
            if end!=len(mod):raise ValueError('Unexpected existing MOD routes/trailing data')
            ended=True;break
        if tag in (0x100,0x110):raise ValueError('MOD already has collision')
        if tag==0x10:
            if offset is not None or len(part)<32:raise ValueError('Invalid MOD vertex chunk')
            offset=struct.unpack_from('>I',part,8)[0]
            if 32+12*offset>len(part):raise ValueError('Truncated MOD vertices')
            payload=struct.pack('>I',offset+len(vertices))+bytes(20)+part[32:32+12*offset]
            payload+=b''.join(struct.pack('>3f',*v) for v in vertices)
            part=chunk(0x10,payload)
        parts.append(part);cursor=end
    if offset is None or not ended:raise ValueError('Missing MOD vertices/end chunk')
    payload=struct.pack('>II',len(triangles),1)+bytes(16)+struct.pack('>i',0)+bytes(28)
    for i,t in enumerate(triangles):
        payload+=struct.pack('>IIIIhhhh4f',codes[i],*(v+offset for v in t),0,*neighbors[i],*plane(vertices,t))
    data=b''.join(parts)+chunk(0x100,payload)+encode_grid(build_grid(vertices,triangles))+chunk(0xffff,b'')+route_ini(room['routes']).encode('ascii')
    return data,dict(source_faces=len(triangles),source_vertices=len(vertices),
                     multi_incident_edges=incidents,source_face_ids=list(range(len(triangles))),
                     source_mapcodes=room['mapcodes'],native_mapcodes=codes,
                     legacy_multi_edge_policy='-1; optional tutorial native index retains exact incident list',
                     full_gameplay_admitted=False)
