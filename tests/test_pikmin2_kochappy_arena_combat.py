from experimental.pikmin2_kochappy_arena_combat import instrument,evidence


def test_stimulus_not_enemy_rewrite():
    source='class RoomApp : public PlugPikiApp {} ;\nint main(){}'
    result=instrument(source)
    assert 'p->changeMode(PikiMode::FreeMode,n)' in result
    assert 'n->resetPosition(stimulus)' in result
    assert 'red->mHealth=' not in result and 'red->mStateID=' not in result
    assert 'PikiAction::Attack' not in result


def test_no_acceptance_from_exit_alone():
    result=evidence('DONE P2_RED_COMBAT',0)
    assert not result['passed'] and not result['checks']['damage']


def test_gate_evidence():
    log='DONE P2_RED_COMBAT\nP2_RED_ARENA_BIRTH a\nP2_RED_ARENA_BIRTH b\nP2_KOCHAPPY_DRAW corpse=0\nP2_KOCHAPPY_DRAW corpse=1\nP2_RED_COMBAT tick=1 state=11 target=1 health=199 corpses=0\nP2_RED_COMBAT tick=2 state=0 target=0 health=0 corpses=1'
    assert evidence(log,0)['passed']
    assert not evidence(log,1)['passed']
