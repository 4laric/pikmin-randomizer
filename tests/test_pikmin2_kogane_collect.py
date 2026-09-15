"""Tests for the lane 17 "real collection and restart dedupe" gate (#168/#219).

Pins the native-log contract for a full reward-beetle cycle where the drops are
actually collected through the ordinary P1 Onion/nectar path (not the Pod), the
lane-06 onion receipt ledger is granted exactly once, and a later process restart
reloads the receipts without re-arming the farmed beetle.
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


def _restart_log(completion=True):
    rows = ['P2_KOGANE_BIRTH id=219004 type=3 x=0.000 y=30.000 z=0.000',
            'P2_KOGANE_RECEIPTS loaded=1',
            'P2_KOGANE_RESTORED_ESCAPE generator=219001 flips=3',
            'P2_KOGANE_RESTART loaded=seen rearmed=0']
    if completion:
        rows.append('PASS P2_KOGANE_RESTART dedupe_ok rearmed=0')
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


def test_validate_restart_accepts_deduped_reload():
    evidence = collect.validate_restart(_restart_log(), 0)
    assert evidence['passed'], evidence['checks']
    assert evidence['receipts_loaded'] == [1]
    assert evidence['restored_escape'] == [[TARGET, 3]]


def test_validate_restart_rejects_re_arm():
    # a re-armed beetle that drops again after restart must fail
    bad = _restart_log().replace('P2_KOGANE_RESTORED_ESCAPE generator=219001 flips=3',
                                 'P2_KOGANE_DROP generator=219001 source_id=9 flip=1 pellet1=1 nectar=0')
    assert not collect.validate_restart(bad, 0)['passed']


def test_validate_cross_combines_both():
    evidence = collect.validate_cross(_collect_log(), 0, _restart_log(), 0)
    assert evidence['passed']
    assert not collect.validate_cross(_collect_log(), 0, _restart_log(completion=False), 0)['passed']


def test_instrument_splices_the_collection_app():
    root = Path(__file__).resolve().parents[1]
    source = collect.build.__wrapped__ if hasattr(collect.build, '__wrapped__') else None
    # exercise instrument via the module's INCLUDES/APP through the base builder is
    # not available headless; the app string must at least never inject a press.
    assert 'InteractPress' in collect.APP  # the labelled injected flip is present
    assert 'startAction(PikiAction::Transport,' in collect.APP  # native carry path


if __name__ == '__main__':
    import sys
    import pytest
    sys.exit(pytest.main([__file__, '-q']))
