from collections import Counter
from randomizer.catalog import active_names, MODERN_LOCATION_IDS, modern_names, item_pool, REPAIR
from randomizer.seed import generate, validate, solo_rewards, spheres


def test_sticks_retired_without_changing_old_ids():
    new = generate('retire-sticks', permanent_checks=True, progressive_color_stats=True)
    assert len(active_names(new)) == 105
    assert not any('Climbing Stick' in n for n in active_names(new))
    assert Counter(item_pool(new))[REPAIR] == 30
    assert sum(map(len, spheres(solo_rewards(new), new))) == 105
    old = dict(new)
    old.pop('no_sticks')
    old['locations'] = {n: MODERN_LOCATION_IDS[n] for n in modern_names(True, True, True, True)}
    validate(old)
    assert len(active_names(old)) == 113
    assert len([n for n in active_names(old) if 'Climbing Stick' in n]) == 8
    assert all(old['locations'][n] == i for n, i in new['locations'].items())


def test_bootstrap_signals_retired_sticks(tmp_path):
    from randomizer.session import Session
    from randomizer.runner import NativeRun
    m = generate('stick-protocol', permanent_checks=True)
    assert 'CHECKSET 31\n' in NativeRun(Session(m, tmp_path / 'new')).bootstrap.read_text()
    m.pop('no_sticks')
    m['locations'] = {n: MODERN_LOCATION_IDS[n] for n in modern_names(True, True, True, True)}
    assert 'CHECKSET 15\n' in NativeRun(Session(m, tmp_path / 'old')).bootstrap.read_text()
