"""Tests for the lane 17 natural press receiver fixture/validator (#168/#219)."""
from pathlib import Path

import experimental.pikmin2_kogane_natural as natural


def _log(completion=True, census='P2_KOGANE_NATURAL_CENSUS pellets=1 nectar=5 pikis=19'):
    rows = ['P2_KOGANE_BIRTH id=%d type=3 x=0.000 y=30.000 z=0.000' % i
            for i in (219001, 219002, 219003, 219004)]
    rows += ['P2_KOGANE_NATURAL_COMMAND attackers=4']
    for f, pv, pc, nc in [(1, 1, 1, 0), (2, 0, 0, 2), (3, 0, 0, 3)]:
        rows.append('P2_KOGANE_NATURAL_ATTACK generator=219001 source_id=9 flip=%d' % f)
        rows.append('P2_KOGANE_FLIP generator=219001 source_id=9 flip=%d' % f)
        rows.append('P2_KOGANE_DROP generator=219001 source_id=9 flip=%d pellet%d=%d nectar=%d'
                    % (f, pv, pc, nc))
    rows += ['P2_KOGANE_ESCAPE generator=219001 source_id=9 flips=3',
             census]
    if completion:
        rows.append('PASS P2_KOGANE_NATURAL natural_attack flip3 escape1 control_alive')
    return '\n'.join(rows) + '\n'


def test_validate_natural_accepts_a_clean_natural_run():
    evidence = natural.validate_natural(_log(), 0)
    assert evidence['passed'], evidence['checks']
    assert evidence['naturals'] == [[219001, 1], [219001, 2], [219001, 3]]


def test_validate_natural_rejects_a_missing_natural_attack_marker():
    bad = _log().replace('P2_KOGANE_NATURAL_ATTACK generator=219001 source_id=9 flip=2\n', '')
    assert not natural.validate_natural(bad, 0)['passed']


def test_validate_natural_rejects_injected_only_runs():
    # a run with flips but no natural-attack markers cannot pass the receiver gate
    bad = _log()
    for f in (1, 2, 3):
        bad = bad.replace('P2_KOGANE_NATURAL_ATTACK generator=219001 source_id=9 flip=%d\n' % f, '')
    assert not natural.validate_natural(bad, 0)['passed']
    assert not natural.validate_natural(bad, 0)['checks']['natural_attacks']


def test_validate_natural_rejects_wrong_drop_table():
    # kogane flip1 is 1x 1-pellet; three 5-pellets must fail
    bad = _log().replace('P2_KOGANE_DROP generator=219001 source_id=9 flip=1 pellet1=1 nectar=0',
                         'P2_KOGANE_DROP generator=219001 source_id=9 flip=1 pellet5=3 nectar=0')
    assert not natural.validate_natural(bad, 0)['passed']


def test_validate_natural_rejects_missing_escape_and_truncated_flips():
    bad = _log().replace('P2_KOGANE_ESCAPE generator=219001 source_id=9 flips=3\n', '')
    assert not natural.validate_natural(bad, 0)['passed']
    assert not natural.validate_natural(_log(completion=False), 0)['passed']
    assert not natural.validate_natural(_log(), 'timeout')['passed']
    # an extra flip on a different beetle is ignored, but a truncated Kogane
    # sequence (only two flips) can never reach the escape gate
    truncated = _log()
    truncated = truncated.replace('P2_KOGANE_FLIP generator=219001 source_id=9 flip=3\n', '')
    truncated = truncated.replace('P2_KOGANE_NATURAL_ATTACK generator=219001 source_id=9 flip=3\n', '')
    assert not natural.validate_natural(truncated, 0)['passed']


def test_validate_natural_ignores_other_beetle_flips():
    # a neighbouring beetle may also be naturally pressed; that must not hide the
    # target's clean three-flip escape
    text = _log().replace(
        'P2_KOGANE_BIRTH id=219002 type=3 x=0.000 y=30.000 z=0.000\n',
        'P2_KOGANE_BIRTH id=219002 type=3 x=0.000 y=30.000 z=0.000\n'
        'P2_KOGANE_NATURAL_ATTACK generator=219002 source_id=10 flip=1\n'
        'P2_KOGANE_FLIP generator=219002 source_id=10 flip=1\n')
    assert natural.validate_natural(text, 0)['passed']


def test_instrument_splices_natural_attack_with_no_stimulus_injection():
    root = Path(__file__).resolve().parents[1]
    source = natural.instrument((root / 'engine/tools/preview_p2_room.cpp').read_text())
    assert 'PASS P2_KOGANE_NATURAL natural_attack flip3 escape1 control_alive' in source
    assert 'P2_KOGANE_NATURAL_CENSUS' in source
    assert 'startAction(PikiAction::Attack,beetle)' in source
    assert 'class RoomApp : public PlugPikiApp {' in source
    assert source.index('class RoomApp : public PlugPikiApp {') < source.index('int main(')
    # the natural fixture must never inject a press/attack stimulus itself
    assert 'InteractPress' not in source
    assert 'InteractAttack' not in source
    assert '.stimulate(' not in source


if __name__ == '__main__':
    import sys
    import pytest
    sys.exit(pytest.main([__file__, '-q']))
