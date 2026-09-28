"""Tests for the lane 17 in-process re-entry fixture and its log validator (#168/#219)."""
from pathlib import Path

import pytest

import experimental.pikmin2_kogane_reentry as reentry


def _log(completion=True):
    rows = ['P2_KOGANE_PASS pass=0',
            'P2_KOGANE_RECEIPTS loaded=0']
    rows += ['P2_KOGANE_BIRTH id=%d type=3 x=0.000 y=30.000 z=0.000' % i
             for i in (219001, 219002, 219003, 219004)]
    rows += ['P2_KOGANE_RECEIPTS loaded=2',
             'P2_KOGANE_FLIPS_RESTORED generator=219001 flips=3',
             'P2_KOGANE_RESTORED_ESCAPE generator=219001 flips=3',
             'P2_KOGANE_FLIPS_RESTORED generator=219002 flips=1',
             'P2_KOGANE_REENTRY reset_setup=2']
    if completion:
        rows.append('PASS P2_KOGANE_REENTRY restored2 escaped1')
    return '\n'.join(rows) + '\n'


def _pass1(completion=True):
    rows = ['P2_KOGANE_PASS pass=1', 'P2_KOGANE_RECEIPTS loaded=0']
    rows += ['P2_KOGANE_BIRTH id=%d type=3 x=0.000 y=30.000 z=0.000' % i
             for i in (219001, 219002, 219003, 219004)]
    rows += ['P2_KOGANE_FLIP generator=219001 source_id=9 flip=1',
             'P2_KOGANE_FLIP generator=219002 source_id=10 flip=1',
             'P2_KOGANE_FLIP generator=219001 source_id=9 flip=2',
             'P2_KOGANE_FLIP generator=219001 source_id=9 flip=3',
             'P2_KOGANE_ESCAPE generator=219001 source_id=9 flips=3']
    if completion:
        rows.append('PASS P2_KOGANE_RECEIPTS_PASS1 flips4 escaped1')
    return '\n'.join(rows) + '\n'


def _pass2(completion=True):
    rows = ['P2_KOGANE_PASS pass=2', 'P2_KOGANE_RECEIPTS loaded=2',
            'P2_KOGANE_FLIPS_RESTORED generator=219001 flips=3',
            'P2_KOGANE_RESTORED_ESCAPE generator=219001 flips=3',
            'P2_KOGANE_FLIPS_RESTORED generator=219002 flips=1',
            'P2_KOGANE_BIRTH id=219002 type=3 x=0.000 y=30.000 z=0.000',
            'P2_KOGANE_BIRTH id=219003 type=3 x=0.000 y=30.000 z=0.000',
            'P2_KOGANE_FLIP generator=219002 source_id=10 flip=2',
            'P2_KOGANE_FLIP generator=219002 source_id=10 flip=3',
            'P2_KOGANE_ESCAPE generator=219002 source_id=10 flips=3']
    if completion:
        rows.append('PASS P2_KOGANE_RECEIPTS_PASS2 restored2 escaped1')
    return '\n'.join(rows) + '\n'


def test_validate_accepts_a_clean_reentry_run():
    evidence = reentry.validate(_log(), 0)
    assert evidence['passed'], evidence['checks']
    assert evidence['restored'] == {'219001': 3, '219002': 1}
    assert evidence['restored_escape'] == [[219001, reentry.MAX_FLIPS]]


def test_validate_rejects_drift():
    assert not reentry.validate(_log(completion=False), 0)['passed']
    assert not reentry.validate(_log(), 'timeout')['passed']
    # the surviving beetle must resume at its restored count, not the cap
    bad = _log().replace('P2_KOGANE_FLIPS_RESTORED generator=219002 flips=1',
                         'P2_KOGANE_FLIPS_RESTORED generator=219002 flips=0')
    assert not reentry.validate(bad, 0)['passed']
    # a spent beetle must also report the reconstructed escape
    bad = _log().replace('P2_KOGANE_RESTORED_ESCAPE generator=219001 flips=3\n', '')
    assert not reentry.validate(bad, 0)['passed']
    # an untouched beetle must never be restored
    bad = _log().replace('P2_KOGANE_REENTRY reset_setup=2',
                         'P2_KOGANE_FLIPS_RESTORED generator=219003 flips=2\n'
                         'P2_KOGANE_REENTRY reset_setup=2')
    assert not reentry.validate(bad, 0)['passed']
    # the escape must be attached to the spent beetle, not the survivor
    bad = _log().replace('P2_KOGANE_RESTORED_ESCAPE generator=219001 flips=3',
                         'P2_KOGANE_RESTORED_ESCAPE generator=219002 flips=3')
    assert not reentry.validate(bad, 0)['passed']
    # missing births must fail
    assert not reentry.validate(_log().replace(
        'P2_KOGANE_BIRTH id=219003 type=3 x=0.000 y=30.000 z=0.000\n', ''), 0)['passed']


def test_validate_rejects_a_missing_reset_setup_cycle():
    assert not reentry.validate(_log().replace('P2_KOGANE_REENTRY reset_setup=2\n', ''), 0)['passed']


def test_validate_requires_the_receipts_reload():
    assert not reentry.validate(_log().replace('P2_KOGANE_RECEIPTS loaded=2\n', ''), 0)['passed']


def test_validate_cross_process_accepts_a_two_process_restart():
    evidence = reentry.validate_cross_process(_pass1(), 0, _pass2(), 0)
    assert evidence['passed'], evidence['checks']
    assert evidence['restored'] == {'219001': 3, '219002': 1}
    assert evidence['restored_escape'] == [[219001, reentry.MAX_FLIPS]]
    assert evidence['receipt_rows'] == 2


def test_validate_cross_process_rejects_drift():
    # the first pass must complete
    assert not reentry.validate_cross_process(_pass1(completion=False), 0, _pass2(), 0)['passed']
    # the second process must load exactly the two sidecar rows
    bad = _pass2().replace('P2_KOGANE_RECEIPTS loaded=2', 'P2_KOGANE_RECEIPTS loaded=0')
    assert not reentry.validate_cross_process(_pass1(), 0, bad, 0)['passed']
    # a spent beetle must be reconstructed as escaped, not respawned
    bad = _pass2().replace('P2_KOGANE_RESTORED_ESCAPE generator=219001 flips=3\n', '')
    assert not reentry.validate_cross_process(_pass1(), 0, bad, 0)['passed']
    # the restored survivor must resume at its persisted count
    bad = _pass2().replace('P2_KOGANE_FLIPS_RESTORED generator=219002 flips=1',
                           'P2_KOGANE_FLIPS_RESTORED generator=219002 flips=0')
    assert not reentry.validate_cross_process(_pass1(), 0, bad, 0)['passed']
    # the untouched beetle must never be restored
    bad = _pass2().replace('P2_KOGANE_RECEIPTS loaded=2',
                           'P2_KOGANE_FLIPS_RESTORED generator=219003 flips=2\n'
                           'P2_KOGANE_RECEIPTS loaded=2')
    assert not reentry.validate_cross_process(_pass1(), 0, bad, 0)['passed']
    # the first process must start with a fresh (empty) ledger
    bad = _pass1().replace('P2_KOGANE_RECEIPTS loaded=0', 'P2_KOGANE_RECEIPTS loaded=2')
    assert not reentry.validate_cross_process(bad, 0, _pass2(), 0)['passed']
    # a timeout cannot pass
    assert not reentry.validate_cross_process(_pass1(), 0, _pass2(), 'timeout')['passed']


def test_instrument_splices_the_reentry_sequence():
    root = Path(__file__).resolve().parents[1]
    source = reentry.instrument((root / 'engine/tools/preview_p2_room.cpp').read_text())
    assert 'pc_p2_kogane_reset();pc_p2_kogane_setup();' in source
    assert 'PASS P2_KOGANE_REENTRY restored2 escaped1' in source
    assert 'PASS P2_KOGANE_RECEIPTS_PASS1 flips4 escaped1' in source
    assert 'PASS P2_KOGANE_RECEIPTS_PASS2 restored2 escaped1' in source
    assert 'P2_KOGANE_PASS pass=%d' in source
    assert source.index('class RoomApp : public PlugPikiApp {') < source.index('int main(')


def test_sidecar_is_reused_from_the_behavior_contract():
    assert reentry.native_sidecar is not None
    assert reentry.IDS == (219001, 219002, 219003)
    assert reentry.MAX_FLIPS == 3


if __name__ == '__main__':
    import sys
    sys.exit(pytest.main([__file__, '-q']))
