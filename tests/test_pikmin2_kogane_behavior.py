"""Tests for the batch-4 beetle behavior module: sidecar contract + log validation."""
import json

import pytest

import experimental.pikmin2_kogane_behavior as behavior


def bank(tmp_path, frames=None, duration=15):
    frames = frames if frames is not None else [0, 7, 14]
    clips = []
    for name in ('move', 'wait', 'damage'):
        dur = 50 if name == 'damage' else duration
        fr = [0, 24, 49] if name == 'damage' else frames
        clips.append({'file': f'{name}.bca', 'source_frames': dur,
                      'poses': [{'file': f'{name}_{i:02d}.mod', 'frame': f, 'sha256': 'x' * 64}
                                for i, f in enumerate(fr)]})
    manifest = {'schema': 1, 'family': 'Kogane', 'shared': {'clips': clips}}
    (tmp_path / 'beetles.json').write_text(json.dumps(manifest))
    return tmp_path


def test_sidecar_matches_native_parser_contract(tmp_path):
    text = behavior.native_sidecar(bank(tmp_path))
    lines = text.split('\n')
    assert lines[0] == 'P2_KOGANE_NATIVE_1'
    assert lines[1] == f'karada {behavior.KARADA_INDEX}'
    assert lines[2] == 'actors 3'
    assert lines[3:6] == ['219001 9', '219002 10', '219003 11']
    assert lines[6:9] == ['move 3 15 0 7 14', 'wait 3 15 0 7 14', 'damage 3 50 0 24 49']
    assert text.endswith('\n') and not text.endswith('\n\n')


def test_sidecar_rejects_noncanonical_mapping(tmp_path):
    with pytest.raises(ValueError, match='exactly'):
        behavior.native_sidecar(bank(tmp_path), {219001: 9, 219002: 10, 219003: 9})


def test_sidecar_rejects_frames_outside_parser_contract(tmp_path):
    with pytest.raises(ValueError, match='parser contract'):
        behavior.native_sidecar(bank(tmp_path, frames=[1, 7, 14]))  # must start at 0
    with pytest.raises(ValueError, match='parser contract'):
        behavior.native_sidecar(bank(tmp_path, frames=[0, 7, 13]))  # must end at duration-1


def _log(completion=True, census='P2_KOGANE_CENSUS pellets=4 nectar=14 pikis=19'):
    rows = ['P2_KOGANE_BIRTH id=%d type=3 x=0.000 y=30.000 z=0.000'
            % i for i in (219001, 219002, 219003, 219004)]
    rows += ['P2_KOGANE_BIND generator=%d source_id=%d karada_k0=%d visual_only=0'
             % (g, s, k) for (g, s, k) in
             ((219001, 9, 60), (219002, 10, 100), (219003, 11, 15))]
    rows += ['P2_ENEMY_READY species=Kogane_family generator=%d x=0 y=0 z=0 health=%s '
             'max_health=%s behavior=native' % (g, h, h)
             for g, h in ((219001, '1000.0'), (219002, '1200.0'), (219003, '1500.0'))]
    drops = {(219001, 1): (1, 1, 0), (219001, 2): (0, 0, 2), (219001, 3): (0, 0, 3),
             (219002, 1): (5, 3, 0), (219002, 2): (0, 0, 3), (219002, 3): (0, 0, 3),
             (219003, 1): (0, 0, 3)}
    for (g, f), (pv, pc, nc) in sorted(drops.items()):
        rows.append('P2_KOGANE_FLIP generator=%d source_id=%d flip=%d' % (g, behavior.SPECIES_ID[g], f))
        rows.append('P2_KOGANE_DROP generator=%d source_id=%d flip=%d pellet%d=%d nectar=%d'
                    % (g, behavior.SPECIES_ID[g], f, pv, pc, nc))
    rows += ['P2_KOGANE_ESCAPE generator=219001 source_id=9 flips=3',
             'P2_KOGANE_ESCAPE generator=219002 source_id=10 flips=3',
             'P2_KOGANE_GAS start generator=219003 duration=2.500 radius=20.0',
             'P2_KOGANE_GAS_KILL generator=219003 exposure=0.812',
             'P2_KOGANE_GAS end generator=219003',
             'P2_KOGANE_DRAW corpse=0', census]
    if completion:
        rows.append('PASS P2_KOGANE_BEHAVIOR flips7 wander3 escapes2 gas1')
    return '\n'.join(rows) + '\n'


def test_validate_behavior_accepts_clean_run():
    evidence = behavior.validate_behavior(_log(), 0)
    assert evidence['passed'], evidence['checks']
    assert evidence['census'] == {'pellets': 4, 'nectar': 14, 'pikis': 19}


def test_validate_behavior_rejects_drift():
    assert not behavior.validate_behavior(_log(completion=False), 0)['passed']
    assert not behavior.validate_behavior(_log(), 'timeout')['passed']
    # wrong drop table entry (wealthy flip 1 must be 3x 5-pellets)
    bad = _log().replace('P2_KOGANE_DROP generator=219002 source_id=10 flip=1 pellet5=3 nectar=0',
                         'P2_KOGANE_DROP generator=219002 source_id=10 flip=1 pellet1=1 nectar=0')
    assert not behavior.validate_behavior(bad, 0)['passed']
    # escape without gas kill must fail
    assert not behavior.validate_behavior(
        _log().replace('P2_KOGANE_GAS_KILL generator=219003 exposure=0.812\n', ''), 0)['passed']
    # a fifth pellet (corpse) must fail the census
    assert not behavior.validate_behavior(
        _log(census='P2_KOGANE_CENSUS pellets=5 nectar=14 pikis=19'), 0)['passed']
    # squad losses beyond the single gas kill must fail
    assert not behavior.validate_behavior(
        _log(census='P2_KOGANE_CENSUS pellets=4 nectar=14 pikis=17'), 0)['passed']


def test_validate_behavior_rejects_visual_only_binding():
    log = _log().replace('visual_only=0', 'visual_only=1')
    assert not behavior.validate_behavior(log, 0)['passed']
