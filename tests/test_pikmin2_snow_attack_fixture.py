from pathlib import Path
import pytest
from experimental.pikmin2_snow_attack_fixture import instrument,evidence,CASES

def log():
    rows='P2_GATE_SETUP opted=1 receiver=BTeki_attackableCreature\n'
    for actor in ('snow','ordinary','reused'):
        for case in CASES:
            accepted=case in {'inside','vertical_inside','angle_inside','angle_negative_inside','wrap_inside'}
            distance=400 if accepted or 'angle' in case or 'wrap' in case else 900
            angle=21 if not accepted and ('angle' in case or 'wrap' in case) else 0
            rows+=f'P2_GATE case={case} actor={actor} actual={int(accepted)} expected={int(accepted)} d2={distance}.0 angle={angle}.0\n'
    return rows+'P2_GATE eligibility=pass self_stick=pass\nP2_GATE ordinary=pass\nP2_GATE slot_reuse=pass\nPASS p2 Snow native attack-entry receiver\n'

def test_instrument_real_source():
    text=instrument(Path('native/tools/preview_p2_room.cpp').read_text())
    assert 'actor->attackableCreature(target)' in text
    assert text.count('class SnowGateTarget')==1
    with pytest.raises(ValueError):instrument(text)

@pytest.mark.parametrize('change',['missing','mismatch','wrong_mode','no_completion','duplicate'])
def test_reject_bad_evidence(change):
    value=log()
    if change=='missing':value=value.replace('case=boundary actor=snow','case=unknown actor=snow')
    elif change=='mismatch':value=value.replace('actual=1 expected=1','actual=0 expected=1',1)
    elif change=='wrong_mode':value=value.replace('opted=1','opted=0')
    elif change=='no_completion':value=value.replace('PASS p2 Snow native attack-entry receiver','')
    else:value+='P2_GATE case=inside actor=snow actual=1 expected=1 d2=400 angle=0\n'
    assert not evidence(value,0,True)['passed']

def test_success_and_exit():
    assert evidence(log(),0,True)['passed']
    assert evidence(log(),0,True)['slot_reuse']
    assert not evidence(log(),1,True)['passed']

def test_unmeasured_reuse():
    value=log().replace('P2_GATE slot_reuse=pass','P2_GATE slot_reuse=unmeasured')
    result=evidence(value,0,True)
    assert result['passed'] and 'native same-address reuse' in result['unmeasured']

def test_fresh_registration_requires_cases():
    assert not evidence(log()+'P2_GATE recycle_target=fresh_registered_actor\n',0,True)['passed']
