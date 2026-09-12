from pathlib import Path
import pytest
from experimental.pikmin2_snow_chase_physics import evidence,instrument


def log(opted=True):
    text=f'P2_PHYS_SETUP opted={int(opted)} ticks=60 ai_frozen=1 acceleration=controlled_native physics=regular\n'
    for tick in range(1,61):
        x=50 if tick<=30 else -50;y=(7 if tick<=30 else -3) if opted else 0
        if tick==31:text+='P2_PHYS_RETARGET tick=31\n'
        text+=f'P2_PHYS_CMD tick={tick} tx={x} ty={y} tz=0 face=1\n'
        text+=f'P2_PHYS_OBS tick={tick} dt=.033 x={tick} y=0 z=0 vx={x} vy=0 vz=0 tx={x} ty={y} tz=0 face=1 ground=0\n'
    return text+'PASS p2 Snow chase real physics\n'


def test_instrument():
    result=instrument(Path('native/tools/preview_p2_room.cpp').read_text())
    assert result.index('PlugPikiApp::idle()')<result.index('P2_PHYS_OBS')
    assert 'tracing.act(*enemy)' in result
    assert 'enemy->mIsFrozen=1' in result
    assert 'enemy->update(' not in result
    with pytest.raises(ValueError):instrument(result)


@pytest.mark.parametrize('opted',[True,False])
def test_modes(opted):
    assert evidence(log(opted),0,opted)['passed']
    assert not evidence(log(opted),1,opted)['passed']


@pytest.mark.parametrize('bad',['missing','duplicate','dt','ground','speed','y','consumed','retarget','stationary','nan','partial','mode'])
def test_bad_evidence(bad):
    text=log()
    if bad=='missing':text=text.replace('P2_PHYS_OBS tick=30 ','IGNORED tick=30 ')
    elif bad=='duplicate':text+='\n'+text.splitlines()[2]
    elif bad=='dt':text=text.replace('dt=.033','dt=0')
    elif bad=='ground':text=text.replace('ground=0','ground=10')
    elif bad=='speed':text=text.replace('tx=50','tx=40')
    elif bad=='y':text=text.replace('ty=7','ty=0')
    elif bad=='consumed':text=text.replace('vx=50 vy=0 vz=0 tx=50','vx=50 vy=0 vz=0 tx=49')
    elif bad=='retarget':text=text.replace('P2_PHYS_RETARGET','IGNORED')
    elif bad=='stationary':text=text.replace('x=60 y=0','x=0 y=0')
    elif bad=='nan':text=text.replace('dt=.033','dt=nan')
    elif bad=='partial':text=text.replace('face=1 ground=0','ground=0',1)
    else:text=text.replace('opted=1','opted=0')
    assert not evidence(text,0,True)['passed']
