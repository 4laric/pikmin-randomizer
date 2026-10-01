from pathlib import Path
import re
import pytest
from experimental.pikmin2_snow_natural_chase import SETUP,OBSERVER,evidence,instrument


def log(opted=True):
    text=f'P2_NATURAL_SETUP opted={int(opted)} state=15 frozen=0 x=0 y=0 z=0 run=50 visible=95\n'
    for tick in range(1,201):
        text+=f'P2_NATURAL tick={tick} dt=.033 state=11 motion=6 frame={tick%30} target=1 frozen=0 x={tick/2} y=0 z=0 vx=50 vy=0 vz=0 tx=50 ty=0 tz=0 face={tick/100} ground=0 stimulus={int(tick>20)}\n'
        if tick==20:text+='P2_NATURAL_RETARGET after_tick=20\n'
    return text+'PASS p2 Snow natural chase observation\n'


def test_observation_only():
    code=SETUP+OBSERVER
    for forbidden in ('tracing.act','moveVelocity(','setCreaturePointer(','startMotion(','setDirection('):
        assert forbidden not in code
    assert not re.search(r'(mIsFrozen|mStateID)\s*=(?!=)',code)
    result=instrument(Path('native/tools/preview_p2_room.cpp').read_text())
    assert result.index('PlugPikiApp::idle()')<result.index('P2_NATURAL tick=')
    with pytest.raises(ValueError):instrument(result)


@pytest.mark.parametrize('opted',[True,False])
def test_modes(opted):
    assert evidence(log(opted),0,opted)['passed']
    assert not evidence(log(opted),1,opted)['passed']


@pytest.mark.parametrize('bad',['missing','duplicate','state','motion','target','frozen','ground','frame','position','face','speed','retarget','mode','nan'])
def test_reject_bad(bad):
    text=log()
    changes={'missing':('P2_NATURAL tick=1 ','IGNORE tick=1 '),'state':('state=11','state=12'),'motion':('motion=6','motion=2'),
             'target':('target=1','target=0'),'frozen':('frozen=0','frozen=1'),'ground':('ground=0','ground=10'),
             'retarget':('P2_NATURAL_RETARGET','IGNORE'),'mode':('opted=1','opted=0'),'nan':('dt=.033','dt=nan'),
             'speed':('tx=50','tx=40')}
    if bad in changes:text=text.replace(*changes[bad])
    elif bad=='duplicate':text+='\n'+text.splitlines()[1]
    else:
        import re
        key={'frame':'frame','position':'x','face':'face'}[bad]
        text=re.sub(r'\b'+key+r'=[\d.]+',key+'=0',text)
    assert not evidence(text,0,True)['passed']
