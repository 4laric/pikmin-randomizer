"""Synthetic definition contracts; optional local disc conversion regressions."""
import json
from pathlib import Path
import pytest

from experimental.pikmin2_cave import cave_definition, parameters, route_audit, tree, unit_definition
from experimental.pikmin2_convert import convert, texture_layout
from experimental.pikmin2_collision import translate_mapcode


def test_comments_braces_and_truncation():
    assert tree('1 # comment {\n{ value # comment }\n}') == ['1',['value']]
    for text in ('{ x', '}'):
        with pytest.raises(ValueError): tree(text)
    with pytest.raises(ValueError): parameters([['f000'],'4','0'])
    with pytest.raises(ValueError): parameters([['f000'],'4','0',['f000'],'4','1',['_eof']])


def test_cave_rosters_keep_packed_weights_and_placement_classes():
    text='''{ {c000} 4 1 {_eof} } 1
    { {f000} 4 0 {f001} 4 0 {f008} -1 synthetic.txt {_eof} }
    { 2 enemy_a 40 0 plant_a 6 6 } { 1 item_a 10 } { 0 } { 0 }'''
    result=cave_definition(text)
    assert result[0]['enemies'][1]==dict(id='plant_a',packed_weight=6,placement_type=6)
    assert result[0]['treasures']==[dict(id='item_a',packed_weight=10)]
    with pytest.raises(ValueError): cave_definition(text.replace('{c000} 4 1','{c000} 4 2'))
    with pytest.raises(ValueError): cave_definition(text.replace('enemy_a 40 0','enemy_a 40'))


def test_unit_doors_preserve_waypoint_and_cell_dimensions():
    text='1 { 1 synthetic 2 3 1 0 1 2 0 0 1 4 1 170.5 1 1 1 2 0 5 1 170.5 0 1 }'
    unit=unit_definition(text)[0]
    assert unit['cells']==[2,3]
    assert unit['doors'][0]['waypoint']==4
    assert unit['doors'][1]['links']==[dict(distance=170.5,door=0,enemy_flag=1)]
    for invalid in (text.replace('synthetic','../bad'),text.replace('170.5 0 1','170.5 9 1'),text[:-2]+' extra }'):
        with pytest.raises(ValueError): unit_definition(invalid)


def test_route_audit_checks_incoming_paths_without_mutating_source():
    room={'routes':[dict(id=0,links=[1]),dict(id=1,links=[]),dict(id=2,links=[0])]}
    before=json.dumps(room)
    assert route_audit(room)==[dict(destination=0,unreachable_sources=[1]),
                               dict(destination=1,unreachable_sources=[]),
                               dict(destination=2,unreachable_sources=[0,1])]
    assert json.dumps(room)==before


@pytest.mark.parametrize('kind,expected',[(0,(3,32)),(1,(4,64)),(2,(5,64)),(3,(6,128)),(4,(0,128)),(5,(2,128)),(6,(7,256)),(14,(1,32))])
def test_gx_texture_tile_sizes_and_native_format_mapping(kind,expected):
    assert texture_layout(kind,8,8)==expected


def test_texture_padding_and_unsupported_palettes():
    assert texture_layout(3,5,5)==(6,128)
    with pytest.raises(ValueError): texture_layout(8,8,8)
    with pytest.raises(ValueError): texture_layout(0,0,8)


def test_dry_emergence_attributes_do_not_become_water_or_holes():
    for material in (1,6,7):
        assert translate_mapcode(material)>>29==0
        assert translate_mapcode(material|64)==0
        assert translate_mapcode(material|16)&(3<<27)==1<<27


def test_local_second_floor_extra_uv_is_opt_in_and_reported(tmp_path):
    source=Path('output/pikmin2-emergence110/import-01/units/room_purple14x14_snow/arc/view.bmd')
    if not source.exists(): pytest.skip('Requires locally extracted user-owned asset')
    with pytest.raises(ValueError,match='attribute 14'): convert(source,tmp_path/'strict.mod')
    report=convert(source,tmp_path/'approximate.mod',approximate_materials=True)
    assert report['discarded_attributes']==[14]
    assert report['triangles']==4108
    assert report['textures']==21
