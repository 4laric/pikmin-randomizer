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
