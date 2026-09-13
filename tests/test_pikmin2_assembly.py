import copy
import json
from pathlib import Path

import pytest

from experimental.pikmin2_assembly import build, merge_rooms, merged_model, transform
from experimental.pikmin2_convert import convert, write_model


def test_quarter_turn_transforms_positions_and_normals_consistently():
    assert transform([3,2,5],1,[10,20,30])==[5,22,33]
    assert transform([3,2,5],2)==[-3,2,-5]
    point=[3,2,5]
    for _ in range(4): point=transform(point,1)
    assert point==[3,2,5]
    with pytest.raises(ValueError): transform([0,0,float('inf')],0)


def pair():
    room=dict(vertices=[[0,0,0],[0,0,10],[10,0,0]],triangles=[[0,2,1]],mapcodes=[7],
              spawns=[dict(type=2,position=[1,0,3],angle=30)],
              routes=[dict(id=0,position=[0,0,0],radius=30,links=[1]),dict(id=1,position=[0,0,10],radius=20,links=[])])
    definition=dict(doors=[dict(id=0,waypoint=1,direction=2)])
    return [(room,definition,0,[0,0,0]),(room,definition,2,[0,0,20])]


def test_only_seam_nodes_are_joined_and_directed_edges_are_preserved():
    instances=pair();before=copy.deepcopy(instances)
    result=merge_rooms(instances,[((0,0),(1,0))])
    assert len(result['routes'])==3
    assert result['routes'][0]['links']==[1]
    assert result['routes'][1]['links']==[]
    assert result['routes'][2]['links']==[1]
    assert result['vertices'][4]==[0,0,10]
    assert result['spawns'][1]['position']==[-1,0,17]
    assert result['spawns'][1]['angle']==210
    assert instances==before


def test_unsealed_misaligned_and_reused_doors_are_rejected():
    with pytest.raises(ValueError,match='unsealed'): merge_rooms(pair(),[])
    instances=pair();instances[1]=(*instances[1][:3],[0,0,21])
    with pytest.raises(ValueError,match='coincide'): merge_rooms(instances,[((0,0),(1,0))])
    with pytest.raises(ValueError,match='reused'): merge_rooms(pair(),[((0,0),(1,0)),((0,0),(1,0))])


IMPORTED=Path('output/pikmin2-emergence110/import-03')


@pytest.mark.skipif(not IMPORTED.exists(),reason='Requires locally extracted user-owned assets')
def test_scene_writer_preserves_single_unit_bytes(tmp_path):
    source=IMPORTED/'units/room_north_tutorial_1_snow/arc/view.bmd'
    convert(source,tmp_path/'single.mod',True)
    write_model(merged_model([(source.read_bytes(),0,[0,0,0])]),tmp_path/'scene.mod','single scene')
    assert (tmp_path/'single.mod').read_bytes()==(tmp_path/'scene.mod').read_bytes()


@pytest.mark.skipif(not IMPORTED.exists(),reason='Requires locally extracted user-owned assets')
def test_local_assembly_is_connected_deterministic_and_keeps_import_private(tmp_path):
    result=build(IMPORTED,tmp_path/'one');build(IMPORTED,tmp_path/'two')
    assert result['geometry']['bounds'][2]==-425
    assert result['geometry']['bounds'][5]==1445
    assert all(not row['unreachable_sources'] for row in result['route_audit'])
    assert len(result['seam_probes'])==195
    for name in ('room.mod','room.ini','collision.json'):
        assert (tmp_path/'one'/name).read_bytes()==(tmp_path/'two'/name).read_bytes()
    assert json.loads((IMPORTED/'manifest.json').read_text())['assembled'] is False
