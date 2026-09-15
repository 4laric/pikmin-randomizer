import pytest

from experimental.pikmin2_snow_lifecycle import evidence,instrument


LOG='''P2_SNOW_DRAW corpse=0
P2_SNOW_LIFECYCLE stage=attack motion=1 frame=3
P2_SNOW_LIFECYCLE stage=death motion=0 frame=3
P2_SNOW_DRAW corpse=1
P2_SNOW_LIFECYCLE stage=carried distance=30 state=3
P2_FIXTURE_COMBAT_PASS
P2_SNOW_LIFECYCLE stage=duplicate_credit pokos=182 repairs=0
PASS p2 room: actors, ground, controller movement, native carry delivery, unchanged repairs, native combat kill, far corpse transport and delivery
'''
LEDGER='P2_ECONOMY_1\ncorpse:test:1 2\ntreasure:dia_a_red 180\n'
HASH='a'*64


def test_complete_evidence_needs_exact_ledger_and_binary():
    assert evidence(LOG,0,LEDGER,HASH,HASH)['passed']
    assert not evidence(LOG,0,LEDGER,HASH,'b'*64)['passed']
    assert not evidence(LOG,1,LEDGER,HASH,HASH)['passed']
    assert not evidence(LOG,0)['passed']


@pytest.mark.parametrize('broken',[LEDGER+'corpse:test:1 2\n',LEDGER.replace('180','181'),
    LEDGER.replace('corpse:test:1','treasure:extra'),LEDGER.replace(' 2',' 3'), 'bad\n'])
def test_duplicate_wrong_or_unrelated_credits_fail(broken):
    assert not evidence(LOG,0,broken,HASH,HASH)['passed']


@pytest.mark.parametrize('marker',['stage=attack','stage=death','corpse=1','stage=carried','P2_FIXTURE_COMBAT_PASS','pokos=182'])
def test_each_missing_lifecycle_stage_fails(marker):
    assert not evidence(LOG.replace(marker,'absent'),0,LEDGER,HASH,HASH)['passed']


def test_instrumentation_rejects_changed_or_previously_patched_source():
    source='        if(phase==0) {\nrequire(corpseReachedGoal && corpseDistance>(assembled?1000:100),"goal");'
    patched=instrument(source)
    assert 'health_override=0 animation_override=0' in patched
    assert 'duplicate receipt changed persistent economy' in patched
    with pytest.raises(ValueError):instrument(patched)
    with pytest.raises(ValueError):instrument('changed')
