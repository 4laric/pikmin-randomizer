import copy
from collections import Counter
import pytest
from randomizer.benefits import PRERELEASE, PROGG, benefit_state
from randomizer.catalog import item_pool, progression_pool, ITEM_IDS
from randomizer.seed import generate, validate, solo_rewards, spheres


def test_traps_replace_only_filler_and_remain_beatable():
    for weight in (1, 5, 10):
        old = generate('ambush', permanent_checks=True)
        m = generate('ambush', permanent_checks=True, prerelease_trap_weight=weight)
        validate(m)
        pool = Counter(item_pool(m))
        assert pool[PRERELEASE] > 0
        assert len(item_pool(m)) == len(item_pool(old)) == len(m['locations'])
        assert progression_pool(m) == progression_pool(old)
        rewards = solo_rewards(m)
        assert sum(map(len, spheres(rewards, m))) == len(m['locations'])
    assert PRERELEASE not in item_pool(old)
    assert ITEM_IDS[PRERELEASE] > ITEM_IDS[PROGG]


def test_strict_trap_option_and_capability():
    for value in (-1, 11, True, 1.5, '1'):
        with pytest.raises(ValueError): generate('bad', prerelease_trap_weight=value)
    m = generate('ambush', prerelease_trap_weight=1)
    for value in (0, 11, True):
        bad = copy.deepcopy(m); bad['prerelease_trap_weight'] = value
        with pytest.raises(ValueError): validate(bad)
    bad = copy.deepcopy(m); bad['capabilities'].remove('prerelease-trap-v1')
    with pytest.raises(ValueError): validate(bad)
    assert benefit_state(m, {PRERELEASE: 3}).split() == ['BENEFITS', '0', '0', '0', '0', '0', '0', '0', '0', '3']

def test_prerelease_and_deathlink_bootstrap_coexist(tmp_path):
    from randomizer.session import Session
    from randomizer.runner import NativeRun
    manifest = generate('combined-main-p2', 'ap', prerelease_trap_weight=1,
                        death_link=True, death_link_pikmin=7)
    validate(manifest)
    session = Session(manifest, tmp_path)
    session.bind_ap('integration', 0, 1)
    run = NativeRun(session)
    bootstrap = run.bootstrap.read_text()
    assert 'BENEFITS 17\n' in bootstrap
    assert 'DEATHLINK 7\n' in bootstrap
    assert {'prerelease-trap-v1', 'death-link-v1'} <= set(manifest['capabilities'])
