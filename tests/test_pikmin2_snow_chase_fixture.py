from pathlib import Path
import pytest
from experimental.pikmin2_snow_chase_fixture import instrument,evidence,CASES,ACTORS

def log():
    text='P2_TRACE_SETUP opted=1 receiver=TaiTracingAction_act fallback_speed=37\nP2_TRACE guard=motion pass=1\nP2_TRACE guard=no_target pass=1\n'
    for actor in ACTORS:
        for name,y in zip(CASES,(7,-13,5,9,-2)):
            text+=f'P2_TRACE case={name} actor={actor} angle=10 expected_angle=10 vx=8.6824089 vy={y} vz=49.2403877 expected_x=8.6824089 expected_y={y} expected_z=49.2403877\n'
    return text+'PASS p2 Snow native tracing receiver\n'

def test_source_anchor():
    result=instrument(Path('native/tools/preview_p2_room.cpp').read_text())
    assert 'tracing.act(*actor)' in result
    assert 'tracing.motionStarted(*enemy)' in result
    with pytest.raises(ValueError):instrument(result)

def test_success_and_exit():
    assert evidence(log(),0,True)['passed']
    assert not evidence(log(),1,True)['passed']

@pytest.mark.parametrize('mutation',['guard','case','actor','vx','vy','heading','mode','duplicate'])
def test_reject_bad_evidence(mutation):
    text=log()
    if mutation=='guard':text=text.replace('guard=motion pass=1','guard=motion pass=0')
    elif mutation=='case':text=text.replace('case=wrap actor=snow','case=unknown actor=snow')
    elif mutation=='actor':text=text.replace('actor=nonliving','actor=wrong')
    elif mutation=='vx':text=text.replace('vx=8.6824089','vx=9',1)
    elif mutation=='vy':text=text.replace('vy=7','vy=0',1)
    elif mutation=='heading':text=text.replace('angle=10 expected_angle=10','angle=11 expected_angle=10',1)
    elif mutation=='mode':text=text.replace('opted=1','opted=0')
    else:text+=text.splitlines()[3]+'\n'
    assert not evidence(text,0,True)['passed']
