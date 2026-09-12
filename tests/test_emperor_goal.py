import json
from collections import Counter
from randomizer.seed import generate, solo_rewards, spheres
from randomizer.session import Session
from randomizer.runner import NativeRun
from randomizer.catalog import ITEM_IDS, REPAIR, can_reach_manifest, item_pool


def test_emperor_goal_and_recovery(tmp_path):
    m = generate('emperor', 'ap', permanent_checks=True, goal_mode='emperor_bulblax')
    s = Session(m, tmp_path); s.bind_ap('test', 0, 1)
    s.receive(0, [ITEM_IDS[REPAIR]] * 25)
    assert not s.goal
    r = NativeRun(s)
    assert 'GOAL emperor25' in r.bootstrap.read_text()
    assert 'EMPEROR 0 END' in s.native_state(r.token, True)
    (r.directory / 'emperor.txt').write_text(f'EMPEROR_DEFEATED {r.token} {s.fingerprint}\n')
    s.recover_emperor(r.directory)
    assert s.goal and Session(m, tmp_path).goal
    assert 'EMPEROR 1 END' in s.native_state(r.token, True)


def test_secret_safe_gate_and_fills():
    for i in range(12):
        m = generate(str(i), permanent_checks=True, progressive_color_stats=True, goal_mode='emperor_bulblax')
        full = Counter(item_pool(m)); full[REPAIR] = 24
        assert not can_reach_manifest('Pikmin: Secret Safe', full, m)
        full[REPAIR] = 25
        assert can_reach_manifest('Pikmin: Secret Safe', full, m)
        assert sum(map(len, spheres(solo_rewards(m), m))) == len(m['locations'])
