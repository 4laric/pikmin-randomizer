import json,math
from unittest.mock import patch
import pytest
from experimental.pikmin2_tank_assets import event_frames,loop_bounds,emitter,receiver,write_pose,extract,parameter_blocks

def test_event_boundaries_order_and_budgets():
    assert loop_bounds([[15,0],[44,1]])==[15,44]
    assert loop_bounds([[55,2]]) is None
    for events in ([[15,0]],[[15,1],[44,0]],[[1,0],[2,0],[44,1]]):
        with pytest.raises(ValueError):loop_bounds(events)
    assert {0,55,94}.issubset(event_frames(95,[[55,2]],3))
    assert {15,44}.issubset(event_frames(55,[[15,0],[44,1]],3))
    for duration,events,limit in [(1,[],3),(95,[[95,2]],3),(95,[[55,2],[40,0]],3),(95,[[True,2]],3),(95,[[55,256]],3),(95,[],9),(95,[[1,0]]*33,3)]:
        with pytest.raises(ValueError):event_frames(duration,events,limit)

def test_emitter_is_finite_normalized_and_offset_is_explicit():
    r=emitter([[2,0,0,1],[0,1,0,2],[0,0,1,3]])
    assert r['direction']==[1,0,0] and r['origin']==[11,-8,3]
    for matrix in ([[0]*4]*3,[[math.nan,0,0,0],[0,1,0,0],[0,0,1,0]],[[1,0,0]]):
        with pytest.raises(ValueError):emitter(matrix)

def test_fire_and_zero_damage_water_status_are_distinct():
    assert receiver('Tank','red') is None
    assert receiver('Wtank','blue') is None
    assert receiver('Tank','blue')=='fire_panic'
    assert receiver('Wtank','red')=='water_panic'
    for species in ('Tank','Wtank'):
        assert receiver(species,'bulbmin') is None
        assert receiver(species,'yellow',invincible=True) is None
        assert receiver(species,'yellow',transittable=False) is None
    with pytest.raises(ValueError):receiver('Wtank','unknown')

def test_report_is_independent_of_output_directory(tmp_path):
    def fake(model,target,source):
        target.write_bytes(b'pose');return dict(source=source,output=str(target),vertices=247)
    outputs=[]
    with patch('experimental.pikmin2_tank_assets.write_model',side_effect=fake):
        for directory in ('a','b'):
            target=tmp_path/directory/'pose.mod';target.parent.mkdir();write_pose({},target);outputs.append(target.with_suffix('.json').read_bytes())
    assert outputs[0]==outputs[1] and b'\r' not in outputs[0]
    assert json.loads(outputs[0])['output']=='pose.mod'

def test_invalid_sampling_rejected_before_disc_or_output(tmp_path):
    with pytest.raises(ValueError):extract(tmp_path/'missing.iso',tmp_path/'output',tmp_path/'source',99)
    assert not (tmp_path/'output').exists()

def test_refuse_existing_output_without_mutation(tmp_path):
    output=tmp_path/'output';output.mkdir();(output/'existing').write_bytes(b'keep')
    with patch('experimental.pikmin2_tank_assets.disc_files',return_value={}),patch('experimental.pikmin2_tank_assets.SOURCE_FILES',[]),patch('experimental.pikmin2_tank_assets.subprocess.check_output',return_value='revision'):
        with pytest.raises(FileExistsError):extract(tmp_path/'disc',output,tmp_path/'source')
    assert (output/'existing').read_bytes()==b'keep' and len(list(output.iterdir()))==1

def test_parameters_keep_distinct_blocks_and_reject_nonfinite():
    assert parameter_blocks(b'{ {fp00} 4 1000 {_eof} } { {fp00} 4 2 {_eof} }')==[{'fp00':1000},{'fp00':2}]
    with pytest.raises(ValueError):parameter_blocks(b'{ {fp00} 4 nan {_eof} }')
