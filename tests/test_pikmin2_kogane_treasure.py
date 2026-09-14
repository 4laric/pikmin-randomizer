"""Tests for the lane 17 first-flip treasure override fixture/validator (#168/#219)."""
import json
from pathlib import Path

import experimental.pikmin2_kogane_reentry as reentry


def _log(completion=True, census='P2_KOGANE_CENSUS pellets=1'):
    rows = ['P2_KOGANE_BIRTH id=%d type=3 x=0.000 y=30.000 z=0.000' % i
            for i in (219001, 219002, 219003, 219004)]
    rows += ['P2_KOGANE_FLIP generator=219002 source_id=10 flip=1',
             'P2_KOGANE_TREASURE generator=219002 value=5',
             'P2_KOGANE_DROP generator=219002 source_id=10 flip=1 pellet5=1 nectar=0',
             census]
    if completion:
        rows.append('PASS P2_KOGANE_TREASURE standin1 value5')
    return '\n'.join(rows) + '\n'


def _bank(tmp_path):
    clips = []
    for name in ('move', 'wait', 'damage'):
        dur = 50 if name == 'damage' else 15
        frames = [0, 24, 49] if name == 'damage' else [0, 7, 14]
        clips.append({'file': f'{name}.bca', 'source_frames': dur,
                      'poses': [{'file': f'{name}_{i:02d}.mod', 'frame': f, 'sha256': 'x' * 64}
                                for i, f in enumerate(frames)]})
    (tmp_path / 'beetles.json').write_text(json.dumps(
        {'schema': 1, 'family': 'Kogane', 'shared': {'clips': clips}}))
    return tmp_path


def test_validate_treasure_accepts_a_clean_override_run():
    evidence = reentry.validate_treasure(_log(), 0)
    assert evidence['passed'], evidence['checks']
    assert evidence['treasures'] == {'219002': 5}
    assert evidence['census'] == 1


def test_validate_treasure_rejects_a_missing_marker():
    # the override never ran: the table row is present but the marker is absent
    bad = _log().replace('P2_KOGANE_TREASURE generator=219002 value=5\n', '')
    assert not reentry.validate_treasure(bad, 0)['passed']


def test_validate_treasure_rejects_a_wrong_value():
    bad = _log().replace('P2_KOGANE_TREASURE generator=219002 value=5',
                         'P2_KOGANE_TREASURE generator=219002 value=1')
    assert not reentry.validate_treasure(bad, 0)['passed']


def test_validate_treasure_distinguishes_override_from_the_table():
    # a forged marker with the audited table row (three 5-pellets) must fail
    bad = _log().replace('P2_KOGANE_DROP generator=219002 source_id=10 flip=1 pellet5=1 nectar=0',
                         'P2_KOGANE_DROP generator=219002 source_id=10 flip=1 pellet5=3 nectar=0')
    evidence = reentry.validate_treasure(bad, 0)
    assert not evidence['passed']
    assert not evidence['checks']['standin']
    assert not evidence['checks']['override_vs_table']
    # the no-override case: the table row without any marker must also fail
    table_only = _log().replace('P2_KOGANE_TREASURE generator=219002 value=5\n', '').replace(
        'P2_KOGANE_DROP generator=219002 source_id=10 flip=1 pellet5=1 nectar=0',
        'P2_KOGANE_DROP generator=219002 source_id=10 flip=1 pellet5=3 nectar=0')
    assert not reentry.validate_treasure(table_only, 0)['passed']


def test_validate_treasure_rejects_drift():
    assert not reentry.validate_treasure(_log(completion=False), 0)['passed']
    assert not reentry.validate_treasure(_log(), 'timeout')['passed']
    # the stand-in is a single pellet; an extra pellet must fail the census
    assert not reentry.validate_treasure(
        _log(census='P2_KOGANE_CENSUS pellets=2'), 0)['passed']
    # a second flip on the configured beetle would leave the first-flip contract
    extra = _log().replace('P2_KOGANE_FLIP generator=219002 source_id=10 flip=1\n',
                           'P2_KOGANE_FLIP generator=219002 source_id=10 flip=1\n'
                           'P2_KOGANE_FLIP generator=219002 source_id=10 flip=2\n')
    assert not reentry.validate_treasure(extra, 0)['passed']


def test_treasure_sidecar_emits_the_first_flip_standin(tmp_path):
    lines = reentry.treasure_sidecar(_bank(tmp_path)).split('\n')
    assert lines[:6] == ['P2_KOGANE_NATIVE_1', 'karada 0', 'actors 3',
                         '219001 9', '219002 10', '219003 11']
    assert lines[6] == 'treasure 219002 5'
    assert lines[7] == 'move 3 15 0 7 14'


def test_instrument_splices_the_treasure_sequence():
    root = Path(__file__).resolve().parents[1]
    source = reentry.instrument((root / 'engine/tools/preview_p2_room.cpp').read_text(),
                                treasure=True)
    assert 'PASS P2_KOGANE_TREASURE standin1 value5' in source
    assert 'P2_KOGANE_CENSUS pellets=%d' in source
    assert '#include "Pellet.h"' in source
    assert 'class RoomApp : public PlugPikiApp {' in source
    assert source.index('class RoomApp : public PlugPikiApp {') < source.index('int main(')


if __name__ == '__main__':
    import sys
    import pytest
    sys.exit(pytest.main([__file__, '-q']))
