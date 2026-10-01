import json
import struct
from pathlib import Path
import pytest
from experimental.pikmin2_collision import adjacency, attach_collision, chunk, collision_chunks, collision_geometry, plane, route_ini, translate_mapcode


def room():
    return {'vertices': [[0,0,0],[0,0,10],[10,0,10],[10,0,0]], 'triangles': [[0,2,1],[0,3,2]], 'mapcodes':[2,18], 'bounds':{'min':[0,0,0],'max':[10,100,10]},'routes':[{'id':0,'position':[2,0,2],'radius':2,'links':[1]},{'id':1,'position':[8,0,8],'radius':2,'links':[0]}]}


def test_plane_and_adjacency_match_native_inward_halfspaces():
    r=room()
    assert plane(r['vertices'],r['triangles'][0])==(0,1,0,0)
    assert adjacency(r['triangles'])==[[1,-1,-1],[-1,-1,0]]


def test_mapcode_does_not_turn_p2_wall_attribute5_into_p1_water():
    assert translate_mapcode(69)==0
    assert translate_mapcode(18)==(1<<27)|(1<<25)
    with pytest.raises(ValueError): translate_mapcode(15)


def test_perimeter_caps_point_inwards_and_do_not_add_ground():
    v,t,c=collision_geometry(room(),True)
    assert len(t)==10
    for tri in t[2:]:
        nx,ny,nz,d=plane(v,tri)
        assert ny==0
        assert nx*5+nz*5-d>0


def test_binary_layout_and_shared_vertex_offset():
    r=room();v,t,c=collision_geometry(r)
    data=collision_chunks(v,t,c,7)
    assert struct.unpack_from('>II',data,8)==(2,1)
    assert struct.unpack_from('>I',data,32)==(0,)
    assert struct.unpack_from('>III',data,68)==(7,9,8)
    size=struct.unpack_from('>I',data,4)[0]+8
    assert size%32==0
    assert struct.unpack_from('>I',data,size)==(0x110,)
    assert struct.unpack_from('>f',data,size+56)==(64.,)


def test_attach_preserves_render_vertices_and_adds_routes():
    src=chunk(0x10,struct.pack('>I',1)+bytes(20)+struct.pack('>fff',99,98,97))+chunk(0xffff,b'')
    out=attach_collision(src,room())
    assert struct.unpack_from('>I',out,8)==(5,)
    assert struct.unpack_from('>fff',out,32)==(99,98,97)
    assert out.endswith(route_ini(room()['routes']).encode())


def test_ground_probe_respects_triangle_edges_and_caps():
    from experimental.pikmin2_collision import ground_height
    v,t,_=collision_geometry(room(),True)
    assert ground_height(v,t,5,5)==0
    assert ground_height(v,t,11,5) is None


def test_decode_extracted_room_and_reject_truncation(tmp_path):
    from experimental.pikmin2_collision import decode_room
    r=room()
    grid=struct.pack('>I',4)+b''.join(struct.pack('>3f',*v) for v in r['vertices'])
    grid+=struct.pack('>I',2)
    for tri in r['triangles']:
        grid+=struct.pack('>3I16f',*tri,*plane(r['vertices'],tri),*([0]*12))
    (tmp_path/'grid.bin').write_bytes(grid+b'acceleration')
    (tmp_path/'mapcode.bin').write_bytes(struct.pack('>I',2)+bytes(r['mapcodes']))
    (tmp_path/'route.txt').write_text('2 # count\n{0 1 1 2 0 2 2}\n{1 1 0 8 0 8 2}')
    out=decode_room(tmp_path)
    assert out['triangles']==r['triangles']
    assert out['routes']==r['routes']
    assert out['unconverted_acceleration_bytes']==12
    (tmp_path/'grid.bin').write_bytes(grid[:5])
    with pytest.raises(ValueError,match='vertex count'):decode_room(tmp_path)
