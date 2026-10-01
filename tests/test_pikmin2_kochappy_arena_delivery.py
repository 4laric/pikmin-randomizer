from experimental.pikmin2_kochappy_arena_delivery import instrument,evidence


def test_transport_not_enemy_or_reward_injection():
    result=instrument('class RoomApp : public PlugPikiApp {};\nint main(){}')
    assert 'PikiAction::Transport' in result
    assert 'red->mHealth=' not in result and 'red->mStateID=' not in result
    assert 'pc_p2_preview_goal()==nullptr' in result
    assert 'p2_receipts=not_applicable' in result


def test_requires_actual_transport_and_route():
    log='P2_RED_ARENA_BIRTH one\nP2_RED_ARENA_BIRTH two\nP2_KOCHAPPY_DRAW corpse=1\nP2_RED_P1_HAUL tick=60 transport=3 distance=120\nPASS P2_RED_P1_DELIVERY distance=300 reached=1 p2_receipts=not_applicable'
    assert evidence(log,0)['passed']
    assert not evidence(log.replace('transport=3','transport=0'),0)['passed']
    assert not evidence(log,1)['passed']


def test_no_receipt_claim_on_exit():
    r=evidence('',0)
    assert not r['passed']
    assert r['p2_receipt_gate'].startswith('not applicable')
