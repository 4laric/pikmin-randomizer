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
