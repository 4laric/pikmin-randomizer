"""Tests for the lane 17 "real collection and restart dedupe" gate (#168/#219).

Pins the native-log contract for a full reward-beetle cycle where the drops are
actually collected through the ordinary P1 Onion/nectar path (not the Pod), the
lane-06 onion receipt ledger is granted exactly once, the three flips are natural
Pikmin attacks, and a later process restart re-drives a second flip sequence only
to hit the real Duplicate path with the ledger still at exactly three rows.
"""
from pathlib import Path

import experimental.pikmin2_kogane_collect as collect

TARGET = collect.TARGET
PASS_MARKER = 'PASS P2_KOGANE_COLLECT collect1 drink5 onion_receipt3'


def _collect_log(completion=True, collected='P2_KOGANE_COLLECTED pellets_collected=1 nectar_drunk=5 sprouts=1'):
    rows = ['P2_KOGANE_BIRTH id=%d type=3 x=0.000 y=30.000 z=0.000' % i
            for i in (219001, 219002, 219003, 219004)]
    rows += ['P2_KOGANE_FLIP generator=219001 source_id=9 flip=1',
             'P2_KOGANE_FLIP generator=219001 source_id=9 flip=2',
             'P2_KOGANE_FLIP generator=219001 source_id=9 flip=3']
    for f, pv, pc, nc in [(1, 1, 1, 0), (2, 0, 0, 2), (3, 0, 0, 3)]:
        rows.append('P2_KOGANE_DROP generator=219001 source_id=9 flip=%d pellet%d=%d nectar=%d'
                    % (f, pv, pc, nc))
        rows.append('P2_KOGANE_ONION_RECEIPT generator=219001 flip=%d granted=1 duplicate=0 ledger=onion seed=kogane-arena' % f)
    rows += ['P2_KOGANE_ESCAPE generator=219001 source_id=9 flips=3', collected]
    if completion:
        rows.append(PASS_MARKER)
    return '\n'.join(rows) + '\n'


def _natural_collect_log(completion=True):
    text = _collect_log(completion=completion)
    mode = 'P2_KOGANE_COLLECT_PASS pass=0 mode=natural\n'
    natural = ''.join('P2_KOGANE_NATURAL_ATTACK generator=219001 source_id=9 flip=%d\n' % f
                      for f in (1, 2, 3))
    return mode + text + natural


def _restart_log(completion=True):
    rows = ['P2_KOGANE_BIRTH id=219004 type=3 x=0.000 y=30.000 z=0.000',
            'P2_KOGANE_RECEIPTS loaded=1',
            'P2_KOGANE_RESTORED_ESCAPE generator=219001 flips=3',
            'P2_KOGANE_RESTART rearmed=0']
    rows += ['P2_KOGANE_ONION_RECEIPT generator=219001 flip=%d granted=0 duplicate=1 ledger=onion seed=kogane-arena' % f
             for f in (1, 2, 3)]
    rows += ['P2_KOGANE_REPROBE duplicates=3',
             'P2_KOGANE_ONION_LEDGER rows=3']
    if completion:
        rows.append('PASS P2_KOGANE_RESTART dedupe_ok rearmed=0 duplicate=3 ledger=3')
    return '\n'.join(rows) + '\n'


def test_validate_collect_accepts_a_clean_run():
    evidence = collect.validate_collect(_collect_log(), 0)
    assert evidence['passed'], evidence['checks']
    assert evidence['collected'] == dict(pellets=1, nectar=5, sprouts=1)


def test_validate_collect_rejects_wrong_drop_table():
    bad = _collect_log().replace(
        'P2_KOGANE_DROP generator=219001 source_id=9 flip=1 pellet1=1 nectar=0',
        'P2_KOGANE_DROP generator=219001 source_id=9 flip=1 pellet5=3 nectar=0')
    assert not collect.validate_collect(bad, 0)['passed']


def test_validate_collect_rejects_missing_escape():
    bad = _collect_log().replace('P2_KOGANE_ESCAPE generator=219001 source_id=9 flips=3\n', '')
    assert not collect.validate_collect(bad, 0)['passed']


def test_validate_collect_rejects_missing_onion_receipt():
    # a drop without a lane-06 onion receipt grant cannot pass the receipts gate
    bad = _collect_log().replace(
        'P2_KOGANE_ONION_RECEIPT generator=219001 flip=1 granted=1 duplicate=0 ledger=onion seed=kogane-arena\n', '')
    assert not collect.validate_collect(bad, 0)['passed']
    assert not collect.validate_collect(bad, 0)['checks']['onion_receipts']


def test_validate_collect_rejects_duplicate_grant_on_first_pass():
    # the first pass of a fresh run must grant (not find a duplicate)
    bad = _collect_log().replace('flip=2 granted=1 duplicate=0', 'flip=2 granted=0 duplicate=1')
    assert not collect.validate_collect(bad, 0)['passed']


def test_validate_collect_rejects_zero_sprout_credit():
    # no sprout credit means the pellet never reached the Onion
    bad = _collect_log().replace('P2_KOGANE_COLLECTED pellets_collected=1 nectar_drunk=5 sprouts=1',
                                 'P2_KOGANE_COLLECTED pellets_collected=1 nectar_drunk=5 sprouts=0')
    assert not collect.validate_collect(bad, 0)['passed']


def test_validate_collect_rejects_bad_exit():
    assert not collect.validate_collect(_collect_log(completion=False), 0)['passed']
    assert not collect.validate_collect(_collect_log(), 'timeout')['passed']
    assert not collect.validate_collect(_collect_log(), 1)['passed']


def test_validate_collect_natural_accepts_real_attacks():
    evidence = collect.validate_collect_natural(_natural_collect_log(), 0)
    assert evidence['passed'], evidence['checks']
    assert evidence['natural_attacks'] == [1, 2, 3]


def test_validate_collect_natural_rejects_injected_flips():
    # the injected scenario lacks P2_KOGANE_NATURAL_ATTACK and is flagged injected
    bad = _collect_log().replace(PASS_MARKER, 'P2_KOGANE_COLLECT_PASS pass=0 mode=injected\n' + PASS_MARKER)
    assert not collect.validate_collect_natural(bad, 0)['passed']
    assert not collect.validate_collect_natural(bad, 0)['checks']['natural_attacks']


def test_validate_collect_natural_rejects_missing_natural_attack():
    bad = _natural_collect_log().replace('P2_KOGANE_NATURAL_ATTACK generator=219001 source_id=9 flip=2\n', '')
    assert not collect.validate_collect_natural(bad, 0)['passed']


def test_validate_restart_accepts_deduped_reload():
    evidence = collect.validate_restart(_restart_log(), 0)
    assert evidence['passed'], evidence['checks']
    assert evidence['receipts_loaded'] == [1]
    assert evidence['restored_escape'] == [[TARGET, 3]]
    assert evidence['reprobe_duplicates'] == [3]
    assert evidence['onion_ledger_rows'] == [3]


def test_validate_restart_rejects_re_arm():
    # a re-armed beetle that drops again after restart must fail
    bad = _restart_log().replace('P2_KOGANE_RESTORED_ESCAPE generator=219001 flips=3',
                                 'P2_KOGANE_DROP generator=219001 source_id=9 flip=1 pellet1=1 nectar=0')
    assert not collect.validate_restart(bad, 0)['passed']


def test_validate_restart_requires_the_ledger_count():
    bad = _restart_log().replace('P2_KOGANE_ONION_LEDGER rows=3\n', '')
    assert not collect.validate_restart(bad, 0)['passed']
    assert not collect.validate_restart(bad, 0)['checks']['onion_ledger_rows']


def test_validate_restart_rejects_ledger_count_drift():
    bad = _restart_log().replace('P2_KOGANE_ONION_LEDGER rows=3', 'P2_KOGANE_ONION_LEDGER rows=4')
    assert not collect.validate_restart(bad, 0)['passed']


def test_validate_restart_rejects_a_regrant_probe():
    # a genuine re-probe must come back duplicate (never a fresh grant)
    bad = _restart_log().replace('P2_KOGANE_REPROBE duplicates=3', 'P2_KOGANE_REPROBE duplicates=0')
    assert not collect.validate_restart(bad, 0)['passed']
    bad = _restart_log().replace('flip=1 granted=0 duplicate=1', 'flip=1 granted=1 duplicate=0')
    assert not collect.validate_restart(bad, 0)['passed']


def test_validate_cross_combines_both():
    evidence = collect.validate_cross(_collect_log(), 0, _restart_log(), 0)
    assert evidence['passed']
    assert not collect.validate_cross(_collect_log(), 0, _restart_log(completion=False), 0)['passed']


def test_validate_mixed_scene_detects_ledger_collision():
    # two consumers each in their own file -> separate
    clean_kogane = 'P2_RECEIPTS_1\nkogane-arena enemy:9 219001 flip1\nkogane-arena enemy:9 219001 flip2\nkogane-arena enemy:9 219001 flip3\n'
    clean_flora = 'P2_RECEIPTS_1\nlocal flora-pelplant:240001 240001 onion\n'
    evidence = collect.validate_mixed_scene(clean_kogane, clean_flora)
    assert evidence['passed'], evidence['checks']
    # the single-consumer host spills Kogane grants into Flora's file -> detected
    collided = collect.validate_mixed_scene('', clean_kogane)
    assert not collided['passed']
    assert collided['checks']['flora_has_no_kogane'] is False
    assert collided['flora_leak'] == ['enemy:9', 'enemy:9', 'enemy:9']


def test_instrument_splices_the_collection_app():
    root = Path(__file__).resolve().parents[1]
    # the app still offers both the natural attack command and the labelled
    # injected press (separately flagged legacy scenario); the carry is native.
    assert 'startAction(PikiAction::Attack,' in collect.APP  # natural flip trigger
    assert 'InteractPress' in collect.APP  # labelled injected legacy scenario
    assert 'startAction(PikiAction::Transport,' in collect.APP  # native carry path
    assert 'pc_p2_kogane_reprobe_duplicates' in collect.APP  # genuine Duplicate probe
    assert 'pc_p2_kogane_onion_ledger_rows' in collect.APP  # persisted ledger count


if __name__ == '__main__':
    import sys
    import pytest
    sys.exit(pytest.main([__file__, '-q']))
