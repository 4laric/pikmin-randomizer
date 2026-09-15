from pathlib import Path
import pytest
from experimental.pikmin2_snow_health_fixture import instrument,evidence

LOG='''P2_HEALTH initial=150.0 max=150.0 fallback=100.0 opted=1
P2_HEALTH ordinary=pass
P2_HEALTH forget=pass
P2_HEALTH reload=pass
P2_HEALTH reset=pass
PASS p2 Snow health probe
'''

def test_real_source_instrumentation():
    result=instrument(Path('native/tools/preview_p2_room.cpp').read_text())
    assert result.count('PASS p2 Snow health probe')==1
    with pytest.raises(ValueError):instrument(result)

def test_wrong_source():
    with pytest.raises(ValueError):instrument('')

def test_pass():
    assert evidence(LOG,0,True)['passed']

@pytest.mark.parametrize('marker',['ordinary=pass','forget=pass','reload=pass','reset=pass','PASS p2 Snow health probe'])
def test_missing(marker):
    assert not evidence(LOG.replace(marker,''),0,True)['passed']

def test_wrong_health_or_mode_or_exit():
    assert not evidence(LOG.replace('max=150.0','max=100.0'),0,True)['passed']
    assert not evidence(LOG,0,False)['passed']
    assert not evidence(LOG,1,True)['passed']

def test_absent_policy():
    baseline=LOG.replace('150.0','100.0').replace('opted=1','opted=0')
    assert evidence(baseline,0,False)['passed']
    assert 'actual manager slot reuse' in evidence(baseline,0,False)['unmeasured']

def test_corpse_instrumentation():
    from experimental.pikmin2_snow_health_fixture import instrument_lifecycle
    result=instrument_lifecycle(Path('native/tools/preview_p2_room.cpp').read_text())
    assert 'P2_HEALTH corpse=pass' in result
    assert 'corpse->mPelletView==static_cast<PelletView*>(enemy)' in result
    assert 'stage=duplicate_credit' in result

def test_native_slot_evidence():
    result=evidence(LOG+'P2_HEALTH slot_reuse=pass\n',0,True)
    assert result['passed'] and result['slot_reuse']
    assert 'actual manager slot reuse' not in result['unmeasured']
