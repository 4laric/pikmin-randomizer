import json
from unittest.mock import patch
import pytest
from experimental.pikmin2_breadbug_cargo_install import install,sha

def fixture(tmp_path):
    bank=tmp_path/'bank';(bank/'models').mkdir(parents=True);profile=tmp_path/'profile';profile.mkdir();run=tmp_path/'run';room=run/'assets/dataDir/courses/pikmin2room';room.mkdir(parents=True)
    (profile/'breadbug-visual.json').write_text(json.dumps(dict(source_import_sha256='source')))
    (run/'p2-breadbug-actor.txt').write_bytes(b'actor')
    (run/'breadbug-actor-proxy.json').write_text(json.dumps(dict(generators=[1],config_sha256=sha(b'actor'),files={})))
    clips=[];files={}
    for name,source,frames,events in [('back','move2.bca',[0,10,39,48],[[10,0],[39,1]]),('hide','type3.bca',[0,20,48],[[20,2]])]:
        clips.append(dict(name=name,source_file=source,duration=49,frames=frames,events=events))
        for i in range(len(frames)):
            file=f'breadbug_cargo_{name}_{i:02}.mod';(bank/'models'/file).write_bytes(b'pose');files[file]=sha(b'pose')
    metadata=dict(schema=1,family='PanModoki',purpose='visual_cargo_reference_only',events_executed=False,source_import_sha256='source',clips=clips,files=files)
    (bank/'breadbug-cargo-bank.json').write_text(json.dumps(metadata));return bank,profile,run,room

def perform(args):
    with patch('experimental.pikmin2_breadbug_cargo_install.plan',return_value=(b'actor',{})),patch('experimental.pikmin2_breadbug_cargo_install.records',return_value=[]):return install(*args[:3])

def test_install_exact_config_and_no_overwrite(tmp_path):
    args=fixture(tmp_path);result=perform(args);raw=(args[2]/'p2-breadbug-cargo.txt').read_bytes()
    assert raw==b'P2_BREADBUG_CARGO_1\nback 49 4 0 10 39 48\nhide 49 3 0 20 48\n'
    assert sha(raw)==result['config_sha256'] and not result['gameplay_events_executed']
    with pytest.raises(ValueError):perform(args)

def test_all_hashes_checked_before_writes(tmp_path):
    args=fixture(tmp_path);(args[0]/'models/breadbug_cargo_hide_02.mod').write_bytes(b'corrupt')
    with pytest.raises(ValueError):perform(args)
    assert not list(args[3].iterdir()) and not (args[2]/'p2-breadbug-cargo.txt').exists()

def test_reject_different_source_profile(tmp_path):
    args=fixture(tmp_path);(args[1]/'breadbug-visual.json').write_text('{"source_import_sha256":"different"}')
    with pytest.raises(ValueError):perform(args)
    assert not list(args[3].iterdir())
