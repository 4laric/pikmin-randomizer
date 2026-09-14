"""Tests for the lane 17 in-process re-entry fixture and its log validator (#168/#219)."""
from pathlib import Path

import pytest

import experimental.pikmin2_kogane_reentry as reentry


def _log(completion=True):
    rows = ['P2_KOGANE_BIRTH id=%d type=3 x=0.000 y=30.000 z=0.000' % i
            for i in (219001, 219002, 219003, 219004)]
    rows += ['P2_KOGANE_FLIPS_RESTORED generator=219001 flips=3',
             'P2_KOGANE_RESTORED_ESCAPE generator=219001 flips=3',
             'P2_KOGANE_FLIPS_RESTORED generator=219002 flips=1',
             'P2_KOGANE_REENTRY reset_setup=2']
    if completion:
        rows.append('PASS P2_KOGANE_REENTRY restored2 escaped1')
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


def test_instrument_splices_the_reentry_sequence():
    root = Path(__file__).resolve().parents[1]
    source = reentry.instrument((root / 'engine/tools/preview_p2_room.cpp').read_text())
    assert 'pc_p2_kogane_reset();pc_p2_kogane_setup();' in source
    assert 'PASS P2_KOGANE_REENTRY restored2 escaped1' in source
    assert source.index('class RoomApp : public PlugPikiApp {') < source.index('int main(')


def test_sidecar_is_reused_from_the_behavior_contract():
    assert reentry.native_sidecar is not None
    assert reentry.IDS == (219001, 219002, 219003)
    assert reentry.MAX_FLIPS == 3


if __name__ == '__main__':
    import sys
    sys.exit(pytest.main([__file__, '-q']))
