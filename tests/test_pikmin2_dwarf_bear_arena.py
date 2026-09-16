import struct
from unittest.mock import patch

import pytest

import experimental.pikmin2_dwarf_bear_arena as arena


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


def test_family_actor_plus_control_unique_ids(tmp_path):
    data, actors = staged(tmp_path)
    assert struct.unpack_from('>I', data, 20)[0] == 3
    assert [a['species'] for a in actors] == ['KumaKochappy', 'P1 Chappy']
    assert [a['generator'] for a in actors] == [211101, 211102]
    assert len({a['generator'] for a in actors}) == 2
    for a in actors:
        assert a['offset'] == [0, 0, 0]
        assert a['source_yaw'] is None and a['source_yaw_applied'] is False
        assert len(a['expected_xyz']) == 3
    assert 'KumaChappy' in actors[0]['parent_following']


def test_expected_xyz_translation_only(tmp_path):
    _, actors = staged(tmp_path)
    assert actors[0]['expected_xyz'] == [-150., 30., 1850.]
    assert actors[1]['expected_xyz'] == [150., 30., 1550.]


def test_generator_id_collision_rejected(tmp_path):
    with pytest.raises(ValueError, match='collision'):
        staged(tmp_path, existing=[entry(identity=211102)])


def test_invalid_expected_xyz_rejected(tmp_path, monkeypatch):
    monkeypatch.setattr(arena, 'POSITIONS', ((-150., 30., float('inf')), (150., 30., 1550.)))
    with pytest.raises(ValueError):
        staged(tmp_path)
