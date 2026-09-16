from experimental.pikmin2_kochappy_arena_reentry import instrument,evidence


def test_actual_manager_lifecycle_not_family_reset():
    result=instrument('class RoomApp : public PlugPikiApp {};\nint main(){}')
    assert 'oldManager->killAll();tekiMgr=nullptr;' in result
    assert 'tekiMgr=new TekiMgr()' in result
    assert 'gen->mGenType->init(gen)' in result
    assert 'pc_p2_kochappy_reset()' not in result
    assert 'before_setup=130' in result


def test_no_pass_without_post_reload_animation():
    log='P2_RED_REENTRY old_registry=clear before_setup=130 new_red=200 control=130 birth=pass\nPASS P2_RED_REENTRY observation'
    assert not evidence(log,0)['passed']
    log+=''.join(f'\nP2_RED_ARENA_TICK tick={t} id={i} frame={t}' for t in range(121,241) for i in (186001,186002))
    assert evidence(log,0)['passed']
    assert not evidence(log,1)['passed']
