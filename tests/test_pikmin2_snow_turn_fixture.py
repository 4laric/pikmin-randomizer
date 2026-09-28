from pathlib import Path
import pytest
from experimental.pikmin2_snow_turn_fixture import instrument,evidence,CASES,ACTORS

VALUES=dict(zip(CASES,(10,350,4,356,359.8,350,0.5,25,10)))

def log():
    text='P2_TURN_SETUP opted=1 dt=0.033333333 receiver=BTeki_turnToward\n'
    for actor in ACTORS:
        for name in CASES:
            arrived=int(name in ('arrival','already_facing'))
            text+=f'P2_TURN case={name} actor={actor} angle={VALUES[name]} expected={VALUES[name]} arrived={arrived} expected_arrived={arrived}\n'
    for marker in ('ordinary','nonliving','forget','reload','reset'):text+=f'P2_TURN {marker}=pass\n'
    return text+'PASS p2 Snow native turn receiver\n'

def test_source_anchor():
    text=instrument(Path('native/tools/preview_p2_room.cpp').read_text())
    assert 'actor->turnToward(target,c.speed)' in text
    assert 'clearTekiOption(BTeki::TEKI_OPTION_ALIVE)' in text
    with pytest.raises(ValueError):instrument(text)

def test_pass_and_exit():
    assert evidence(log(),0,True)['passed']
    assert not evidence(log(),1,True)['passed']

@pytest.mark.parametrize('mutation',['missing_case','missing_actor','duplicate','mismatch','arrival','mode','dt','source_pattern'])
def test_failure(mutation):
    text=log()
    if mutation=='missing_case':text=text.replace('case=wrap actor=snow','case=unknown actor=snow')
    elif mutation=='missing_actor':text=text.replace('actor=reset','actor=wrong')
    elif mutation=='duplicate':text+='P2_TURN case=wrap actor=snow angle=359.8 expected=359.8 arrived=0 expected_arrived=0\n'
    elif mutation=='mismatch':text=text.replace('angle=10 expected=10','angle=11 expected=10',1)
    elif mutation=='arrival':text=text.replace('arrived=0 expected_arrived=0','arrived=1 expected_arrived=0',1)
    elif mutation=='mode':text=text.replace('opted=1','opted=0')
    elif mutation=='dt':text=text.replace('dt=0.033333333','dt=0')
    else:text=text.replace('angle=10 expected=10','angle=12 expected=12',1)
    assert not evidence(text,0,True)['passed']
