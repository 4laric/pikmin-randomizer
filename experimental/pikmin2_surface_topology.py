"""Audit source surface topology without deleting faces or inventing adjacency."""
import argparse
from collections import defaultdict
import hashlib
import itertools
import json
import math
from pathlib import Path

from experimental.pikmin2_collision import plane


def directed_edge(triangle, edge):
    return triangle[edge], triangle[(edge+1)%3]


def orientation(triangle):
    # Cyclic permutations retain winding; reversed order deliberately differs.
    return min(tuple(triangle[i:]+triangle[:i]) for i in range(3))


def audit(room):
    vertices, triangles, codes = room['vertices'], room['triangles'], room['mapcodes']
    if len(codes) != len(triangles): raise ValueError('Mapcode count mismatch')
    if any(len(t)!=3 or any(type(v) is not int or v<0 or v>=len(vertices) for v in t) for t in triangles):
        raise ValueError('Invalid triangle vertices')
    planes=[plane(vertices,t) for t in triangles]
    if not all(math.isfinite(v) for p in planes for v in p): raise ValueError('Nonfinite triangle geometry')
    edges=defaultdict(list); faces=defaultdict(list)
    for index, triangle in enumerate(triangles):
        faces[tuple(sorted(triangle))].append(index)
        for e in range(3): edges[tuple(sorted(directed_edge(triangle,e)))].append((index,e))
    duplicates=[]
    for face, ids in faces.items():
        if len(ids)>1:
            duplicates.append(dict(vertices=list(face),triangles=ids,
                                   same_winding=len({orientation(triangles[i]) for i in ids})==1,
                                   mapcodes=[codes[i] for i in ids],
                                   identical_physics_codes=len({codes[i] for i in ids})==1))
    bad=[]
    for edge, peers in edges.items():
        if len(peers)<=2: continue
        pairs=[]
        for (i,e),(j,f) in itertools.combinations(peers,2):
            pi,pj=planes[i],planes[j]
            dot=max(-1.,min(1.,sum(a*b for a,b in zip(pi[:3],pj[:3]))))
            opposite=directed_edge(triangles[i],e)==tuple(reversed(directed_edge(triangles[j],f)))
            coplanar=sum((a-b)**2 for a,b in zip(pi[:3],pj[:3]))<1e-10 and abs(pi[3]-pj[3])<.001
            coincident=set(triangles[i])==set(triangles[j])
            pairs.append(dict(triangles=[i,j],opposite_edge_winding=opposite,
                              normal_angle_degrees=math.degrees(math.acos(dot)),same_plane=coplanar,
                              coincident_face=coincident,same_mapcode=codes[i]==codes[j],
                              safe_smooth_candidate=opposite and coplanar and not coincident and codes[i]==codes[j]
                                                    and pi[1]>.6 and pj[1]>.6))
        bad.append(dict(vertices=list(edge),positions=[vertices[v] for v in edge],
                        incidents=[dict(triangle=i,edge=e,plane=planes[i],mapcode=codes[i]) for i,e in peers],
                        coincident_overlay=any(p['coincident_face'] for p in pairs),pairs=pairs))
    # A safe smooth pair alone cannot represent every incident face. Never promote
    # this diagnostic into a replacement topology without an all-face policy.
    return dict(schema=1,triangles=len(triangles),vertices=len(vertices),nonmanifold_edges=bad,
                duplicate_faces=duplicates,safe_smooth_pairs=sum(p['safe_smooth_candidate'] for b in bad for p in b['pairs']),
                topology_unchanged=True,native_conversion_approved=not bad,
                unresolved=['P1 stores one neighbor per edge; source P2 triangles have no neighbor field.',
                            'Missing-neighbor fallback can trigger P1 jump callbacks and truncate shadows.',
                            'Coincident faces with distinct slip/material codes cannot be discarded as identical.',
                            'A native multi-incident ground-transition policy needs integration/playtesting.'] if bad else [],
                mandatory_water_sidecar='surface-water.json',terrain_usable_alone=False)


def write_audit(imported, output):
    room_path=imported/'surface-collision.json'
    water_path=imported/'surface-water.json'
    room=json.loads(room_path.read_text())
    water=json.loads(water_path.read_text())
    if water.get('schema')!=1 or not isinstance(water.get('boxes'),list):
        raise ValueError('Required surface water sidecar missing/invalid')
    report=audit(room)
    report['source_sha256']={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in (room_path,water_path)}
    output.mkdir(parents=True,exist_ok=False)
    (output/'topology-audit.json').write_text(json.dumps(report,indent=2))
    return report


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--imported',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();result=write_audit(args.imported,args.output)
    print(json.dumps(dict(nonmanifold_edges=len(result['nonmanifold_edges']),duplicate_faces=result['duplicate_faces'],
                          safe_smooth_pairs=result['safe_smooth_pairs'],native_conversion_approved=result['native_conversion_approved'])))
