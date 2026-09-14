"""Lane 16 Frog/MaroFrog arena placement option tests (#167/#201)."""
import struct
from unittest.mock import patch

import pytest

from experimental.pikmin2_frog_arena import onion_position, roster


def record(label=b'iket', identity=1, position=(0., 0., 0.)):
    r = bytearray(110)
    r[:8] = b'    0.0v'
    struct.pack_into('<I', r, 8, identity)
    r[16:48] = label.ljust(32, b'\0')
    r[72:76] = b'iket'
    struct.pack_into('>3f', r, 48, *position)
    struct.pack_into('>3f', r, 60, 0, 0, 0)
    return bytes(r)


def stage_source(tmp_path):
    path = tmp_path / 'dataDir/stages/practice/default.gen'
    path.parent.mkdir(parents=True)
    path.write_bytes(b'1.0v' + struct.pack('>4fI', 47, 30, 1919, 180, 1))


def arena_patches(practice):
    return (patch('experimental.pikmin2_frog_arena.records', return_value=practice),
            patch('experimental.pikmin2_frog_arena.generator', return_value=bytes(24) + record()))


def test_onion_position_reads_red_goal():
    practice = [record(b'blue goal'), record(b'red goal', identity=2, position=(-498.186, 0., 1454.469))]
    x, y, z = onion_position(practice)
    assert abs(x - (-498.186)) < .01 and y == 0. and abs(z - 1454.469) < .01


def test_onion_position_missing_fails_closed():
    with pytest.raises(ValueError):
        onion_position([record(b'blue goal')])


def test_default_placement_unchanged(tmp_path):
    stage_source(tmp_path)
    records, generator = arena_patches([record(b'red goal')])
    with records, generator:
        _, actors = roster(tmp_path)
    assert [a['position'] for a in actors[:2]] == [[-150., 30., 1850.], [150., 30., 1850.]]


def test_near_onion_stages_registered_actors(tmp_path):
    stage_source(tmp_path)
    practice = [record(b'blue goal'), record(b'red goal', identity=2, position=(-498.186, 0., 1454.469))]
    records, generator = arena_patches(practice)
    with records, generator:
        _, actors = roster(tmp_path, near_onion=True)
    assert [a['species'] for a in actors] == ['Frog', 'MaroFrog', 'P1 Frog', 'P1 Frow']
    for x, _, z in (a['position'] for a in actors[:2]):
        assert abs(x - (-498.186)) <= 40.001
        assert abs(z - 1454.469) <= 115.001
    assert all(a['offset'] == [0, 0, 0] and not a['source_yaw_applied'] for a in actors)


def test_near_onion_requires_red_goal(tmp_path):
    stage_source(tmp_path)
    records, generator = arena_patches([record(b'blue goal')])
    with records, generator, pytest.raises(ValueError):
        roster(tmp_path, near_onion=True)
