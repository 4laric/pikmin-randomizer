from pathlib import Path
import pytest
from experimental.pikmin2_kochappy_fixture import evidence,instrument

MANIFEST={'actors':[{'generator':5000,'expected_xyz':[185,0,-180]}]}


def log(red=True,lifecycle=False):
    text=f'P2_RED_HEALTH opted={int(red)} initial={200 if red else 130}.0 max={200 if red else 130}.0 fallback=130.0\nP2_RED_CONTROL initial=130.0 max=130.0 fallback=130.0 name=none\n'
    if red:text+='P2_ENEMY_READY species=Kochappy source_id=1 native_family=Chappy generator=5000 x=185.0000000 y=0.0000000 z=-180.0000000 health=200.0 max_health=200.0\nP2_KOCHAPPY_DRAW corpse=0\n'
    if lifecycle:
        for stage in ('attack','death','carried','duplicate_credit'):text+=f'P2_RED_LIFECYCLE stage={stage}\n'
        text+='P2_RED_CORPSE max=200 identity=Kochappy\nP2_KOCHAPPY_DRAW corpse=1\nP2_RED_REGISTRY post_delivery_reset=pass\nPASS p2 room: actors, ground, controller movement, native carry delivery, unchanged repairs, native combat kill, far corpse transport and delivery\n'
    else:
        for stage in ('forget','reload','reset'):text+=f'P2_RED_REGISTRY {stage}=pass\n'
        text+='PASS p2 Red health registry\n'
    return text


def test_instrument_scope():
    result=instrument(Path('native/tools/preview_p2_room.cpp').read_text())
    assert 'enemy->mHealth=0' not in result
    assert 'P2_RED_HEALTH' in result and 'P2_RED_CORPSE' in result
    with pytest.raises(ValueError):instrument(result)


@pytest.mark.parametrize('red,lifecycle',[(True,False),(False,False),(True,True)])
def test_valid_modes(red,lifecycle):
    result=evidence(log(red,lifecycle),0,MANIFEST,red,lifecycle)
    assert result['passed'] and not result['slot_reuse']
    assert not evidence(log(red,lifecycle),1,MANIFEST,red,lifecycle)['passed']


@pytest.mark.parametrize('bad',['x','y','z','id','identity','health','ordinary','draw','reset','corpse','death'])
def test_reject_missing_or_wrong_evidence(bad):
    text=log(True,True)
    replacements={'x':('x=185.0000000','x=184.0000000'),'y':('y=0.0000000','y=1.0000000'),'z':('z=-180.0000000','z=-179.0000000'),
                  'id':('generator=5000','generator=5001'),'identity':('species=Kochappy','species=YellowKochappy'),
                  'health':('initial=200.0','initial=150.0'),'ordinary':('initial=130.0','initial=200.0'),
                  'draw':('P2_KOCHAPPY_DRAW corpse=0','IGNORE'),'reset':('post_delivery_reset=pass','post_delivery_reset=fail'),
                  'corpse':('P2_RED_CORPSE max=200','P2_RED_CORPSE max=130'),'death':('stage=death','stage=other')}
    text=text.replace(*replacements[bad]);assert not evidence(text,0,MANIFEST,True,True)['passed']
