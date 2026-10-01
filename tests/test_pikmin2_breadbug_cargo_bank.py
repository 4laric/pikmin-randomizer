import json
from unittest.mock import patch
import pytest
from experimental.pikmin2_breadbug_cargo_bank import mapping,prepare,CLIPS,sha

def source(tmp_path):
    root=tmp_path/'source';(root/'PanModoki').mkdir(parents=True);(root/'PanModoki/enemy.bmd').write_bytes(b'model');clips=[]
    for name,events in CLIPS.values():
        (root/'PanModoki'/name).write_bytes(name.encode());clips.append(dict(file=name,events=events,sha256=sha(name.encode()),source_frames=49))
    (root/'breadbugs.json').write_text(json.dumps(dict(schema=1,species={'PanModoki':dict(model_sha256=sha(b'model'),joints=[0],clips=clips)})));return root

def test_mapping_is_semantic_and_preserves_fallback():
    assert mapping(5,alive=True,has_cargo=True)['phase']=='intro'
    assert mapping(6,alive=True,has_cargo=True)['clip']=='back'
    assert mapping(8,alive=True,has_cargo=True)['clip']=='hide'
    assert not mapping(9,alive=True,has_cargo=False)['visible']
    for state in (0,1,3,7,10):assert mapping(state,alive=True,has_cargo=True) is None
    assert mapping(6,alive=False,has_cargo=True) is None
    assert mapping(6,alive=True,has_cargo=False) is None
    with pytest.raises(ValueError):mapping(True,alive=True,has_cargo=True)

def test_bank_keeps_event_samples_hashes_and_no_gameplay(tmp_path):
    root=source(tmp_path)
    def convert(model,target,*args,**kw):target.write_bytes(str(kw['pose']).encode())
    with patch('experimental.pikmin2_breadbug_cargo_bank.bca_pose',side_effect=lambda raw,frame,*a,**kw:(49,frame)),patch('experimental.pikmin2_breadbug_cargo_bank.convert',side_effect=convert):
        r=prepare(root,tmp_path/'bank')
    assert {10,39}.issubset(r['clips'][0]['frames']) and 20 in r['clips'][1]['frames']
    assert not r['events_executed'] and not r['native_ready']
    assert r['corpse_carry_excluded']=='type5.bca'
    for name,digest in r['files'].items():assert sha((tmp_path/'bank/models'/name).read_bytes())==digest
    assert b'\r' not in (tmp_path/'bank/breadbug-cargo-bank.json').read_bytes()

def test_tampered_clip_and_wrong_events_fail_before_output(tmp_path):
    root=source(tmp_path);(root/'PanModoki/move2.bca').write_bytes(b'wrong')
    with pytest.raises(ValueError):prepare(root,tmp_path/'bad')
    assert not (tmp_path/'bad').exists()
    (root/'PanModoki/move2.bca').write_bytes(b'move2.bca');p=root/'breadbugs.json';r=json.loads(p.read_text());r['species']['PanModoki']['clips'][0]['events']=[[11,0],[39,1]];p.write_text(json.dumps(r))
    with pytest.raises(ValueError):prepare(root,tmp_path/'wrong-events')
    assert not (tmp_path/'wrong-events').exists()
