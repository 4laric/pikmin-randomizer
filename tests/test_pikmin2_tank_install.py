import json,struct
from unittest.mock import patch
import pytest
from experimental.pikmin2_tank_install import CLIPS,plan,install,actor_ids,sha

def fixture(tmp_path):
    root=tmp_path/'profile';root.mkdir();variants={}
    for variant,identity,interaction in [('Tank',24,'InteractFire'),('Wtank',25,'InteractBubble')]:
        (root/variant).mkdir();clips=[]
        for name in CLIPS:
            poses=[]
            for i in (0,1):
                file=f'{name}_{i:02}.mod';(root/variant/file).write_bytes(b'pose');poses.append(dict(frame=i,file=file,sha256=sha(b'pose')))
            clips.append(dict(file=name+'.bca',duration=2,frames=[0,1],events=[],poses=poses,status='converted'))
        variants[variant]=dict(enemy_id=identity,interaction=interaction,clips=clips)
    (root/'tank.json').write_text(json.dumps(dict(schema=1,events_executed=False,variants=variants)))
    row=bytearray(81);struct.pack_into('<I',row,8,186151);row[72:76]=b'iket';row[80]=15
    return root,sha((root/'tank.json').read_bytes()),[bytes(row)]

def water():return dict(display_id=186153,position=[1,2,3],yaw_degrees=0,noninteractive=True)

def test_config_source_bound_and_water_never_actor(tmp_path):
    root,digest,rows=fixture(tmp_path);config,files=plan(root,digest,rows,[186151],water())
    assert b'\r' not in config and b'1\n186151 15\n1\n186153 1 2 3 0\n' in config
    assert 'tank_water_static.mod' in files and len(files)==15
    with pytest.raises(ValueError):plan(root,'0'*64,rows,[186151])
    with pytest.raises(ValueError):plan(root,digest,rows,[186151],dict(water(),noninteractive=False))
    with pytest.raises(ValueError):plan(root,digest,rows,[186151],dict(water(),position=[float('nan'),0,0]))

def test_ids_duplicate_or_wrong_native_family_rejected(tmp_path):
    _,_,rows=fixture(tmp_path)
    for rs,ids in [(rows*2,[186151]),(rows,[186151,186151]),(rows,[1])]:
        with pytest.raises(ValueError):actor_ids(rs,ids)
    bad=bytearray(rows[0]);bad[80]=8
    with pytest.raises(ValueError):actor_ids([bytes(bad)],[186151])

def test_install_prevalidates_tamper_and_refuses_overwrite(tmp_path):
    root,digest,rows=fixture(tmp_path);run=tmp_path/'run';room=run/'assets/dataDir/courses/pikmin2room';room.mkdir(parents=True);gen=run/'assets/dataDir/stages/chal0/default.gen';gen.parent.mkdir(parents=True);gen.write_bytes(b'gen')
    with patch('experimental.pikmin2_tank_install.records',return_value=rows):
        path=root/'Tank/type5_01.mod';path.write_bytes(b'tamper')
        with pytest.raises(ValueError):install(root,digest,run,[186151])
        assert not list(room.iterdir()) and not (run/'p2-tank-visual.txt').exists()
        path.write_bytes(b'pose');result=install(root,digest,run,[186151],water())
        assert result['config_sha256']==sha((run/'p2-tank-visual.txt').read_bytes())
        with pytest.raises(ValueError):install(root,digest,run,[186151],water())
