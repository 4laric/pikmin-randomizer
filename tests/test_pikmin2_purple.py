from pathlib import Path
import json
import struct
import pytest
from experimental.pikmin2_purple import bca_pose


def animation():
    data=bytearray(256);data[:8]=b'J3D1bca1';struct.pack_into('>II',data,8,256,1)
    base=32;data[base:base+4]=b'ANF1';struct.pack_into('>I',data,base+4,224)
    struct.pack_into('>HH',data,base+10,2,1)
    struct.pack_into('>4I',data,base+20,64,128,132,144)
    for axis in range(3):struct.pack_into('>6H',data,base+64+axis*12,1,0,1,0,2 if axis==0 else 1,0 if axis==0 else axis+1)
    struct.pack_into('>f',data,base+128,1);struct.pack_into('>h',data,base+132,0)
    struct.pack_into('>4f',data,base+144,1,3,4,5)
    return data


def test_bca_frames_and_constant_tracks():
    data=animation();duration,first=bca_pose(data,0,1);_,last=bca_pose(data,100,1)
    assert duration==2
    assert [row[3] for row in first[0]]==[1,4,5]
    assert [row[3] for row in last[0]]==[3,4,5]
    assert bca_pose(data[:-4],1,1)==bca_pose(data,1,1) # omitted terminal alignment bytes


def test_bca_rejects_scaled_animation_and_wrong_skeleton():
    data=animation()
    with pytest.raises(ValueError,match='skeleton'):bca_pose(data,0,2)
    struct.pack_into('>f',data,32+128,2)
    with pytest.raises(ValueError,match='Scaled'):bca_pose(data,0,1)


def test_bca_rejects_truncated_tracks():
    with pytest.raises(ValueError):bca_pose(b'J3D1bca1',0,1)
    data=animation();struct.pack_into('>I',data,32+32,1000)
    with pytest.raises(ValueError,match='Truncated BCA track'):bca_pose(data,0,1)


def test_local_purple_source_data_and_distinct_walk_poses():
    directory=Path('output/pikmin2-purple113/import-05')
    if not directory.exists():pytest.skip('Requires local user-owned disc extraction')
    report=json.loads((directory/'purple.json').read_text())
    assert report['joints']==11
    assert report['source_stats']['movement']==0.8
    assert report['source_stats']['carry_speed_power']==0.6
    assert report['source_stats']['attack']==20
    assert report['source_stats']['throw_height']==49
    from experimental.pikmin2_convert import blocks,u32
    bmd=blocks((directory/'purple.bmd').read_bytes())['MAT3']
    assert struct.unpack_from('>4h',bmd,u32(bmd,80))==(28,0,52,255)
    data=(directory/'purple_wait_00.mod').read_bytes()
    # Untextured body material retains its distinct base color; eyes stay white.
    assert struct.pack('>Ii4BI',257,-1,28,0,52,255,0) in data
    assert (directory/'purple_walk_00.mod').read_bytes()!=(directory/'purple_walk_06.mod').read_bytes()
    for name in ('wait','walk','attack1'):
        assert len(list(directory.glob(f'purple_{name}_*.mod')))==12


def test_local_atlas_config_is_equipment_catalog_and_requires_101():
    directory=Path('output/pikmin2-purple113/atlas-01')
    if not directory.exists():pytest.skip('Requires local user-owned disc extraction')
    report=json.loads((directory/'pod.json').read_text())
    assert (report['treasure']['name'],report['treasure']['money'],report['treasure']['min'],report['treasure']['max'])==('map01','200','101','101')


def test_local_violet_generator_count_and_pod_requirement(tmp_path):
    from scripts.preview_pikmin2_emergence import prepare
    from scripts.preview_pikmin2_room import records
    assets=Path('C:/Users/alari/bbft/dist/cohesion/pikmin/assets');imported=Path('output/pikmin2-emergence110/import-03')
    purple=Path('output/pikmin2-purple113/import-05');pod=Path('output/pikmin2-purple113/atlas-01');treasure=Path('output/pikmin2-room105/treasure.mod')
    if not all(p.exists() for p in (assets,imported,purple,pod,treasure)):pytest.skip('Requires local user-owned assets')
    with pytest.raises(ValueError,match='requires Research Pod'):prepare(assets,imported,treasure,tmp_path,purple=purple)
    run=prepare(assets,imported,treasure,tmp_path,pod=pod,purple=purple)
    entries=records(run/'assets/dataDir/stages/chal0/default.gen')
    flowers=[e for e in entries if e[16:48].startswith(b'preview violet')]
    assert len(flowers)==2 and len(entries)==26
    assert all(struct.unpack_from('>I',e,80)[0]==0x45 for e in flowers)
    assert (run/'p2-purple.txt').read_bytes()==(purple/'p2-purple.txt').read_bytes()
