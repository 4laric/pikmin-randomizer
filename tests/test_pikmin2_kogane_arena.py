"""Tests for beetle arena roster/contract logic and runtime probe validation."""
import struct
from unittest.mock import patch

import pytest

import experimental.pikmin2_kogane_arena as arena
from experimental.pikmin2_kogane_runtime import validate


def entry(kind=b'iket', identity=1):
    r = bytearray(100)
    r[:8] = b'    0.0v'
    struct.pack_into('<I', r, 8, identity)
    r[72:76] = kind
    return bytes(r)


def staged(tmp_path, existing=None, template=None):
    source = tmp_path / 'dataDir/stages/practice/default.gen'
    source.parent.mkdir(parents=True)
    source.write_bytes(b'1.0v' + struct.pack('>4fI', 47, 30, 1919, 180, 1))
    with patch.object(arena, 'records', return_value=existing or [entry(b'goal')]), \
            patch.object(arena, 'generator', return_value=b'x' * 24 + (template or entry())):
        return arena.roster(tmp_path)


def test_roster_three_species_plus_control(tmp_path):
    data, actors = staged(tmp_path)
    assert struct.unpack_from('>I', data, 20)[0] == 5
    assert [a['species'] for a in actors] == ['kogane', 'wealthy', 'fart', 'P1 Chappy']
    assert [a['generator'] for a in actors] == [219001, 219002, 219003, 219004]
    assert len({a['generator'] for a in actors}) == 4
    for a in actors:
        assert a['offset'] == [0, 0, 0]
        assert a['source_yaw'] is None and a['source_yaw_applied'] is False
        assert len(a['expected_xyz']) == 3


def test_expected_xyz_translation_only(tmp_path):
    _, actors = staged(tmp_path)
    assert [tuple(a['expected_xyz']) for a in actors] == [tuple(p) for p in arena.POSITIONS]


def test_generator_id_collision_rejected(tmp_path):
    with pytest.raises(ValueError, match='collision'):
        staged(tmp_path, existing=[entry(identity=219003)])


def test_invalid_expected_xyz_rejected(tmp_path, monkeypatch):
    monkeypatch.setattr(arena, 'POSITIONS', ((-150., 30., float('inf')),) * 3 + ((150., 30., 1550.),))
    with pytest.raises(ValueError):
        staged(tmp_path)


GOOD_LOG = '\n'.join(
    f'P2_KOGANE_BIRTH id={i} type=3 x={x:.3f} y=30.000 z={z:.3f}'
    for (i, x, z) in [(219001, -150., 1850.), (219002, -50., 1850.),
                      (219003, 50., 1850.), (219004, 150., 1550.)]) + '\nPASS P2_KOGANE_RUNTIME births4 alive4 behavior=unregistered\n'


def test_validate_accepts_clean_probe():
    evidence = validate(GOOD_LOG, 0)
    assert evidence['passed']
    assert [int(b[0]) for b in evidence['births']] == [219001, 219002, 219003, 219004]
    assert 'flip/drop cycle' in evidence['unmeasured']
    assert '#219' in evidence['blocked_gates']


def test_validate_rejects_incomplete_births():
    log = GOOD_LOG.replace('P2_KOGANE_BIRTH id=219003 type=3 x=50.000 y=30.000 z=1850.000\n', '')
    assert not validate(log, 0)['passed']


def test_validate_rejects_timeout_and_missing_pass():
    assert not validate(GOOD_LOG, 'timeout')['passed']
    assert not validate(GOOD_LOG.replace('PASS P2_KOGANE_RUNTIME', ''), 0)['passed']
