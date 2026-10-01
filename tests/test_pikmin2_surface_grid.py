import math
import struct

import pytest

from experimental.pikmin2_collision import ground_height
from experimental.pikmin2_surface_grid import build_grid, decode_grid, encode_grid, query_faces


def fixture():
    # Long floor crosses many cells; wall, remote floor, and duplicate overlay
    # must all keep their original face IDs without inferring adjacency.
    return ([[0,0,0],[0,0,400],[400,0,0],[0,100,0],
             [2000,20,2000],[2000,20,2200],[2200,20,2000]],
            [[0,1,2],[0,3,1],[4,5,6],[0,1,2]])


def test_binary_roundtrip_source_faces_and_conservative_cell_membership():
    vertices, triangles=fixture()
    data=encode_grid(build_grid(vertices,triangles))
    grid=decode_grid(data,len(triangles))
    assert data==encode_grid(grid)
    assert {i for group in grid['groups'] for i in group}==set(range(4))
    assert -1 in grid['cells']
    # Independent exhaustive AABB oracle; includes exact expanded-cell boundaries.
    for z in range(grid['nz']):
        for x in range(grid['nx']):
            group=grid['cells'][z*grid['nx']+x]
            got=[] if group==-1 else grid['groups'][group]
            x0,z0=grid['min'][0]+x*64,grid['min'][2]+z*64
            expected=[]
            for i,t in enumerate(triangles):
                v=[vertices[j] for j in t]
                if max(p[0] for p in v)>=x0-64 and min(p[0] for p in v)<=x0+128 and max(p[2] for p in v)>=z0-64 and min(p[2] for p in v)<=z0+128:
                    expected.append(i)
            assert got==expected


def test_ground_parity_and_wall_preservation():
    vertices, triangles=fixture();grid=build_grid(vertices,triangles)
    for x,z in [(1,1),(50,200),(199,200),(300,300),(2050,2050),(1000,1000)]:
        local=[triangles[i] for i in query_faces(grid,x,z)]
        assert ground_height(vertices,local,x,z)==ground_height(vertices,triangles,x,z)
    assert 1 in query_faces(grid,0,200)  # vertical wall cannot be floor-filtered
    assert 0 in query_faces(grid,100,100) and 3 in query_faces(grid,100,100)
    assert max(map(len,grid['groups'])) < len(triangles)


@pytest.mark.parametrize('vertices,triangles,message',[
    ([],[],'count'),([[math.nan,0,0]],[[0,0,0]],'Nonfinite'),
    ([[0,0,0]],[[0,0,1]],'index'),([[0,0,0]],[[False,0,0]],'index'),
    ([[0,0,0],[1e6,0,1e6]],[[0,0,1]],'span'),
    ([[0,0,0]],[[0,0,0]]*32768,'count')])
def test_bad_source_refused(vertices,triangles,message):
    with pytest.raises(ValueError,match=message): build_grid(vertices,triangles)


def test_corrupt_binary_refused():
    vertices,triangles=fixture();data=encode_grid(build_grid(vertices,triangles))
    for bad in [data[:-32],data+b'\0'*32,data[:4]+b'\0'*4+data[8:]]:
        with pytest.raises(ValueError):decode_grid(bad,4)
    # First source reference, grid dimensions, and first group's signed count.
    for offset,fmt,value in [(76,'i',4),(60,'i',-1),(74,'h',-1)]:
        bad=bytearray(data);struct.pack_into('>'+fmt,bad,offset,value)
        with pytest.raises(ValueError):decode_grid(bytes(bad),4)


def test_reference_budget_and_invalid_consumer_count(monkeypatch):
    vertices,triangles=fixture()
    import experimental.pikmin2_surface_grid as module
    monkeypatch.setattr(module,'MAX_REFERENCES',1)
    with pytest.raises(ValueError,match='reference budget'):build_grid(vertices,triangles)
    with pytest.raises(ValueError,match='triangle count'):decode_grid(bytes(96),-1)
