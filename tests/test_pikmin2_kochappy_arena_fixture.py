import pytest
from experimental.pikmin2_kochappy_arena_fixture import instrument,evidence


def test_replaces_geometry_class():
    source='prefix\nclass RoomApp : public PlugPikiApp { old room bounds };\nint main(){}'
    result=instrument(source)
    assert 'old room bounds' not in result
    assert 'mPersonality->mPosition' in result and 'getPos()' in result
    assert 'resetPosition(' not in result and 'startMotion(' not in result
    with pytest.raises(ValueError):instrument(result)


def test_reject_incomplete_evidence():
    assert not evidence('PASS P2_RED_ARENA observation',0)['passed']


def test_complete_observations():
    lines=['P2_RED_ARENA_BIRTH id=186001','P2_RED_ARENA_BIRTH id=186002','P2_KOCHAPPY_DRAW corpse=0','PASS P2_RED_ARENA observation']
    lines += [f'P2_RED_ARENA_TICK tick={t} id={i} frame={t}' for t in range(1,241) for i in (186001,186002)]
    assert evidence('\n'.join(lines),0)['passed']
    assert not evidence('\n'.join(lines),1)['passed']
