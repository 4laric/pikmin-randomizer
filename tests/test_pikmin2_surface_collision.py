import struct
import pytest
from experimental.pikmin2_collision import chunk,adjacency
from experimental.pikmin2_surface_collision import attach_surface_collision,source_neighbors
from experimental.pikmin2_surface_grid import decode_grid


def fixture():
    return dict(vertices=[[0,0,0],[0,0,10],[10,0,0],[10,0,10]],
                triangles=[[0,2,1],[1,2,3],[1,2,3]],mapcodes=[65,65,103],routes=[])


def model():
    return chunk(0x10,struct.pack('>I',1)+bytes(20)+struct.pack('>3f',100,0,100))+chunk(0xffff,b'')


def test_all_faces_slip_overlays_and_incidents_preserved():
    room=fixture()
    with pytest.raises(ValueError,match='Nonmanifold'):adjacency(room['triangles'])
    data,report=attach_surface_collision(model(),room)
    assert report['source_faces']==3 and report['source_face_ids']==[0,1,2]
    assert report['source_mapcodes']==[65,65,103]
    assert report['native_mapcodes'][1]!=report['native_mapcodes'][2]
    assert len(report['multi_incident_edges'])==1
    neighbors,incidents=source_neighbors(room['triangles'])
    assert neighbors[0][1]==neighbors[1][0]==neighbors[2][0]==-1
    cursor=0
    while True:
        tag,size=struct.unpack_from('>II',data,cursor);part=data[cursor:cursor+size+8]
        if tag==0x100:
            assert struct.unpack_from('>I',part,8)[0]==3
            for i,t in enumerate(room['triangles']):
                assert list(struct.unpack_from('>3I',part,68+40*i))==[v+1 for v in t]
                assert list(struct.unpack_from('>3h',part,82+40*i))==neighbors[i]
        if tag==0x110:assert decode_grid(part,3)['triangle_count']==3
        if tag==0xffff:break
        cursor+=size+8


@pytest.mark.parametrize('mutation', ['index','degenerate','material'])
def test_invalid_source_refused(mutation):
    room=fixture()
    if mutation=='index':room['triangles'][0][0]=100
    if mutation=='degenerate':room['triangles'][0]=[0,0,1]
    if mutation=='material':room['mapcodes'][0]=255
    with pytest.raises(ValueError):attach_surface_collision(model(),room)


def test_bad_or_existing_mod_refused():
    for data in [model()[:-1],model()+b'extra',chunk(0x100,b'')+model()]:
        with pytest.raises(ValueError):attach_surface_collision(data,fixture())
