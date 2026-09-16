"""The standalone P2 room adds explicitly audited P1 goal approaches."""
import re
from pathlib import Path
import pytest
from experimental.pikmin2_collision import chunk, decode_room, collision_geometry, ground_height, route_ini
from scripts.preview_pikmin2_room import prototype_routes, replace_embedded_routes


def test_goal_approaches_preserve_original_directed_graph():
    original={0:[5],1:[5],2:[6],3:[6],4:[5,6],5:[0,1,4],6:[2,3,4],7:[5,4],8:[6,5,4]}
    routes=[dict(id=i,links=links,position=[i,0,0],radius=30) for i,links in original.items()]
    source=route_ini(routes).encode()
    result=prototype_routes(source)
    edges=lambda b:{tuple(map(int,e)) for e in re.findall(rb'link\s*{\s*(\d+)\s+(\d+)\s*}',b)}
    before=edges(source);after=edges(result)
    assert after-before=={(4,7),(4,8)}
    assert before<=after
    assert re.findall(rb'point\s*{[^}]+}',source)==re.findall(rb'point\s*{[^}]+}',result)
    for start in original:
        seen={start};pending=[start]
        while pending:
            current=pending.pop()
            for a,b in after:
                if a==current and b not in seen:seen.add(b);pending.append(b)
        assert {7,8}<=seen
    assert prototype_routes(result)==result


def test_embedded_and_external_routes_identical():
    source=chunk(0,b'')+chunk(0xffff,b'')+b'old route'
    route=b'route { id test }'
    assert replace_embedded_routes(source,route)==source[:-9]+route


def test_local_goal_corridors_remain_on_dry_floor():
    texts=Path('output/pikmin2-content-probe/texts')
    if not texts.exists():pytest.skip('Requires locally extracted legally obtained room')
    room=decode_room(texts);v,t,_=collision_geometry(room)
    positions={p['id']:p['position'] for p in room['routes']}
    # Audit center and a 30-unit-wide carry corridor, not just endpoints.
    import math
    for goal in (7,8):
        a=positions[4];b=positions[goal];dx=b[0]-a[0];dz=b[2]-a[2];length=math.hypot(dx,dz)
        for k in range(101):
            for side in (-15,0,15):
                x=a[0]+dx*k/100-side*dz/length;z=a[2]+dz*k/100+side*dx/length
                y=ground_height(v,t,x,z)
                assert y is not None and abs(y)<0.01
