"""Long Legs bind-pose visual conversion tests (#312, parent #173).

The converter's full J3D decode is exercised against the real disc in the lane
evidence; these tests cover the lane-owned contract (deterministic bytes, hash
binding, overwrite refusal, absent-baseline preservation) with a patched
conversion so no disc or generated asset is required.
"""
import json
from pathlib import Path

import pytest

import experimental.pikmin2_long_legs_visual as visual
from experimental.pikmin2_long_legs_visual import (FAMILY, MESH, MOD, RECEIPT,
                                                   SCHEMA, convert, plan, sha,
                                                   verify)


def make_room(root):
    room = root / 'assets' / 'dataDir' / 'courses' / 'pikmin2room'
    room.mkdir(parents=True)
    for species in visual.SPECIES:
        (room / MESH.format(species=species)).write_bytes(species.encode() + b':enemy.bmd')
    return room


def fake_conversion(monkeypatch, payload=b'MOD\x00'):
    def _fake(model):
        return payload + sha(model).encode(), dict(vertices=1, triangles=2, shapes=1,
                                                   textures=1, envelopes=0,
                                                   bind_draw_matrices=0,
                                                   discarded_attributes=[])
    monkeypatch.setattr(visual, '_conversion', _fake)


def test_convert_writes_bind_mods_and_receipt(tmp_path, monkeypatch):
    fake_conversion(monkeypatch)
    room = make_room(tmp_path)
    receipt = convert(room)
    assert receipt['schema'] == SCHEMA and receipt['family'] == FAMILY
    assert receipt['pose_bank'] is False and receipt['skeletal_playback'] is False
    assert sorted(receipt['files']) == ['BigFoot', 'Houdai']
    for species in visual.SPECIES:
        target = room / MOD.format(species=species)
        assert target.is_file()
        row = receipt['files'][species]
        assert row['output'] == target.name
        assert row['bytes'] == target.stat().st_size
        assert row['sha256'] == sha(target.read_bytes())
        assert row['source_sha256'] == sha((room / MESH.format(species=species)).read_bytes())
    saved = json.loads((room / RECEIPT).read_text())
    assert saved == receipt


def test_conversion_is_deterministic(tmp_path, monkeypatch):
    fake_conversion(monkeypatch)
    first = convert(make_room(tmp_path / 'a'))
    second = convert(make_room(tmp_path / 'b'))
    assert first == second
    assert first['files']['Houdai']['sha256'] == second['files']['Houdai']['sha256']


def test_convert_refuses_existing_mod(tmp_path, monkeypatch):
    fake_conversion(monkeypatch)
    room = make_room(tmp_path)
    (room / MOD.format(species='Houdai')).write_bytes(b'old')
    with pytest.raises(ValueError, match='existing/conflicting'):
        convert(room)


def test_convert_refuses_existing_receipt(tmp_path, monkeypatch):
    fake_conversion(monkeypatch)
    room = make_room(tmp_path)
    (room / RECEIPT).write_text('{}')
    with pytest.raises(ValueError, match='receipt'):
        convert(room)


def test_absent_mesh_bank_preserves_baseline(tmp_path, monkeypatch):
    fake_conversion(monkeypatch)
    room = tmp_path / 'assets' / 'dataDir' / 'courses' / 'pikmin2room'
    room.mkdir(parents=True)
    receipt = convert(room)
    assert receipt['visuals'] == 'absent_baseline_preserved'
    assert verify(room) == dict(verified=[], visuals='absent_baseline_preserved')


def test_verify_round_trip_and_tamper(tmp_path, monkeypatch):
    fake_conversion(monkeypatch)
    room = make_room(tmp_path)
    convert(room)
    assert verify(room)['verified'] == ['BigFoot', 'Houdai']
    (room / MOD.format(species='BigFoot')).write_bytes(b'tampered')
    with pytest.raises(ValueError, match='mismatch'):
        verify(room)


def test_verify_detects_changed_source(tmp_path, monkeypatch):
    fake_conversion(monkeypatch)
    room = make_room(tmp_path)
    convert(room)
    (room / MESH.format(species='Houdai')).write_bytes(b'changed:enemy.bmd')
    with pytest.raises(ValueError, match='changed'):
        verify(room)


def test_plan_rejects_stray_mesh(tmp_path):
    room = make_room(tmp_path)
    (room / 'Olimar_enemy.bmd').write_bytes(b'x')
    with pytest.raises(ValueError, match='Unexpected'):
        plan(room)


def test_plan_rejects_unsafe_room(tmp_path):
    with pytest.raises(ValueError, match='private'):
        plan(tmp_path / 'missing')


def test_conversion_rejects_non_bmd(tmp_path):
    room = make_room(tmp_path)
    (room / MESH.format(species='Houdai')).write_bytes(b'not a model')
    with pytest.raises(ValueError, match='J3D2bmd3'):
        convert(room)


def test_rigid_skin_sidecar_is_written_bound_and_verified(tmp_path, monkeypatch):
    """#173 walk: a rigid (envelope-free) mesh also gets the IK skin sidecar."""
    def _fake(model):
        report = dict(vertices=1, triangles=2, shapes=1, textures=1, envelopes=0,
                      bind_draw_matrices=0, discarded_attributes=[])
        if model.startswith(b'Houdai'):
            report['skin_text'] = b'P2_LONG_LEGS_SKIN_1\n' + sha(model).encode() + b'\nend\n'
        return b'MOD\x00' + sha(model).encode(), report
    monkeypatch.setattr(visual, '_conversion', _fake)
    room = make_room(tmp_path)
    receipt = convert(room)
    assert receipt['ik_leg_skin'] == ['Houdai']
    row = receipt['files']['Houdai']
    skin = room / visual.SKIN.format(species='Houdai')
    assert row['skin'] == skin.name and row['skin_bytes'] == skin.stat().st_size
    assert row['skin_sha256'] == sha(skin.read_bytes())
    assert 'skin' not in receipt['files']['BigFoot']
    assert not (room / visual.SKIN.format(species='BigFoot')).exists()
    assert verify(room)['verified'] == ['BigFoot', 'Houdai']
    skin.write_bytes(b'tampered')
    with pytest.raises(ValueError, match='skin sidecar mismatch'):
        verify(room)


def test_skin_text_rows_follow_joint_and_vertex_order(monkeypatch):
    import experimental.pikmin2_rigid as rigid
    monkeypatch.setattr(visual, 'joint_names', lambda blocks: ['kosi', 'lfoot1jnt'])
    identity = [[1, 0, 0, 0], [0, 1, 0, 138], [0, 0, 1, 0]]
    monkeypatch.setattr(rigid, 'joint_matrices', lambda blocks: [identity, identity])
    text = visual.skin_text({}, {9: [(1, (1.0, 2.0, 3.0)), (0, (0.5, 0, 0))], 10: [(1, (0, 1, 0))]})
    lines = text.decode('ascii').splitlines()
    assert lines[0] == visual.SKIN_HEADER and lines[1] == 'joints 2'
    assert lines[2].startswith('j 0 kosi ') and lines[3].startswith('j 1 lfoot1jnt ')
    assert lines[4:7] == ['positions 2', '1 1 2 3', '0 0.5 0 0']
    assert lines[7:] == ['normals 1', '1 0 1 0', 'end']
    with pytest.raises(ValueError, match='out of range'):
        visual.skin_text({}, {9: [(2, (0, 0, 0))], 10: []})
