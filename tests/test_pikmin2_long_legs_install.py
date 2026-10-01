"""Long Legs batch-2 install + arena tests (#312, parent #173).

Uses a synthetic ``long-legs-family.json`` mesh profile with real bytes and
recorded SHA-256 hashes so installed artifacts, not just output, are covered.
"""
import json
import struct
from pathlib import Path
from unittest.mock import patch

import pytest

import experimental.pikmin2_batch2_core as core
import experimental.pikmin2_long_legs_arena as arena
from experimental.pikmin2_long_legs_install import (ACTORS_HEADER, ACTORS_TXT,
                                                    ANCHORS, BASE_SPECIES,
                                                    DAMAGUMO_MANIFEST, FOLDERS,
                                                    INSTALL_JSON, MANIFEST,
                                                    SPECIES, install, plan, sha,
                                                    verify_install)

ANCHOR_ROWS = {'Houdai': {'wait': [0, 38], 'attack': [0, 33, 38], 'landing': [0, 54, 149]},
               'BigFoot': {'wait': [0, 75, 299], 'flick': [0, 35, 47], 'dead': [0, 95, 149]},
               'Damagumo': {'landing': [0, 74, 149], 'wait': [0, 51, 104],
                            'flick': [0, 33, 67]}}


def fake_imported(root, omit_mesh=False, tamper=False, damagumo=False,
                  damagumo_tamper=False):
    root.mkdir(parents=True)
    profiles = {}
    for species in sorted(BASE_SPECIES):
        identity = SPECIES[species]
        (root / FOLDERS[species]).mkdir()
        data = (species + ':enemy.bmd').encode()
        if not omit_mesh:
            (root / FOLDERS[species] / 'enemy.bmd').write_bytes(data)
        profiles[str(identity)] = dict(
            enemy_id=identity, name=species, retail=species + ' Retail',
            folder=FOLDERS[species], joints=['kosi'], joint_count=1,
            embedded_texture_count=1, model_sha256=sha(data),
            special_joints=[dict(name='rkamujnt', role='mouth', present=False)],
            animation_rows=ANCHOR_ROWS[species])
    manifest = dict(schema=1, family='Long Legs', lane='codex/p2-longlegs-family',
                    profiles=profiles)
    (root / MANIFEST).write_text(json.dumps(manifest))
    if tamper:
        (root / FOLDERS['Houdai'] / 'enemy.bmd').write_bytes(b'TAMPERED')
    if damagumo:
        (root / FOLDERS['Damagumo']).mkdir()
        data = b'Damagumo:enemy.bmd'
        (root / FOLDERS['Damagumo'] / 'enemy.bmd').write_bytes(
            b'TAMPERED' if damagumo_tamper else data)
        demon = dict(schema=1, family='Long Legs', lane='demon',
                     profiles={'56': dict(
                         enemy_id=56, name='Damagumo', retail='Beady Long Legs',
                         folder=FOLDERS['Damagumo'], joints=['kosi'], joint_count=1,
                         embedded_texture_count=1, model_sha256=sha(data),
                         special_joints=[dict(name='rkamujnt', role='mouth',
                                              present=False)],
                         animation_rows=ANCHOR_ROWS['Damagumo'])})
        (root / DAMAGUMO_MANIFEST).write_text(json.dumps(demon))
    return root


def fake_run(tmp_path):
    run = tmp_path / 'run'
    (run / 'assets/dataDir/courses/pikmin2room').mkdir(parents=True)
    return run


def entry(kind=b'iket', identity=1):
    record = bytearray(100)
    record[:8] = b'    0.0v'
    struct.pack_into('<I', record, 8, identity)
    record[72:76] = kind
    return bytes(record)


def staged(tmp_path, existing=None):
    source = tmp_path / 'dataDir/stages/practice/default.gen'
    source.parent.mkdir(parents=True)
    source.write_bytes(b'1.0v' + struct.pack('>4fI', 47, 30, 1919, 180, 1))
    with patch.object(core, 'records', return_value=existing or [entry(b'goal')]), \
            patch.object(core, 'generator', return_value=b'x' * 24 + entry()):
        return arena.roster(tmp_path)


def test_actor_count_rejected_before_io():
    for actors in ([], [(i, 'Houdai') for i in range(101)]):
        with pytest.raises(ValueError):
            plan(Path('missing'), actors)


def test_duplicate_and_invalid_ids_rejected(tmp_path):
    imported = fake_imported(tmp_path / 'imported')
    with pytest.raises(ValueError):
        plan(imported, [(5, 'Houdai'), (5, 'Houdai')])
    for bad in [(-1, 'Houdai'), ('5', 'Houdai'), (True, 'Houdai'), (1, 'Demon')]:
        with pytest.raises(ValueError):
            plan(imported, [bad])


def test_schema_and_identity_rejected(tmp_path):
    imported = fake_imported(tmp_path / 'imported')
    meta = json.loads((imported / MANIFEST).read_text())
    for key, value in (('schema', 2), ('family', 'Ground Invertebrates')):
        broken = dict(meta, **{key: value})
        (imported / MANIFEST).write_text(json.dumps(broken))
        with pytest.raises(ValueError):
            plan(imported, [(1, 'Houdai')])
        (imported / MANIFEST).write_text(json.dumps(meta))
    broken = json.loads(json.dumps(meta))
    broken['profiles']['66']['enemy_id'] = 99
    (imported / MANIFEST).write_text(json.dumps(broken))
    with pytest.raises(ValueError, match='species/ID'):
        plan(imported, [(1, 'Houdai')])
    broken = json.loads(json.dumps(meta))
    broken['profiles'].pop('69')
    (imported / MANIFEST).write_text(json.dumps(broken))
    with pytest.raises(ValueError):
        plan(imported, [(1, 'Houdai')])


def test_missing_anchor_rejected(tmp_path):
    imported = fake_imported(tmp_path / 'imported')
    meta = json.loads((imported / MANIFEST).read_text())
    meta['profiles']['66']['animation_rows'].pop(ANCHORS['Houdai'][0])
    (imported / MANIFEST).write_text(json.dumps(meta))
    with pytest.raises(ValueError, match='anchor'):
        plan(imported, [(1, 'Houdai')])


def test_mesh_hash_mismatch_rejected(tmp_path):
    imported = fake_imported(tmp_path / 'imported', tamper=True)
    with pytest.raises(ValueError, match='hash mismatch'):
        plan(imported, [(1, 'Houdai')])


def test_install_and_verify_roundtrip(tmp_path):
    imported = fake_imported(tmp_path / 'imported')
    run = fake_run(tmp_path)
    actors = [(312001, 'Houdai'), (312002, 'BigFoot')]
    receipt = install(imported, run, actors)
    assert receipt['visuals'] == 'installed'
    assert set(receipt['file_sha256']) == {'Houdai', 'BigFoot'}
    verified = verify_install(imported, run, actors)
    assert verified['verified'] == ['BigFoot', 'Houdai']
    config = (run / ACTORS_TXT).read_text().split()
    assert config[:4] == [ACTORS_HEADER, '2', '312001', 'Houdai']


def test_install_refuses_overwrite(tmp_path):
    imported = fake_imported(tmp_path / 'imported')
    run = fake_run(tmp_path)
    install(imported, run, [(1, 'Houdai')])
    with pytest.raises(ValueError, match='Refusing existing'):
        install(imported, run, [(2, 'Houdai')])


def test_verify_detects_tampered_mesh(tmp_path):
    imported = fake_imported(tmp_path / 'imported')
    run = fake_run(tmp_path)
    install(imported, run, [(1, 'Houdai')])
    (run / 'assets/dataDir/courses/pikmin2room/Houdai_enemy.bmd').write_bytes(b'X')
    with pytest.raises(ValueError, match='mesh mismatch'):
        verify_install(imported, run, [(1, 'Houdai')])


def test_verify_detects_config_tamper(tmp_path):
    imported = fake_imported(tmp_path / 'imported')
    run = fake_run(tmp_path)
    install(imported, run, [(1, 'Houdai')])
    (run / ACTORS_TXT).write_text(f'{ACTORS_HEADER}\n1\n999 Nope\n')
    with pytest.raises(ValueError, match='actor config mismatch'):
        verify_install(imported, run, [(1, 'Houdai')])


def test_absent_mesh_preserves_baseline(tmp_path):
    imported = fake_imported(tmp_path / 'imported', omit_mesh=True)
    run = fake_run(tmp_path)
    receipt = install(imported, run, [(1, 'Houdai')])
    assert receipt['visuals'] == 'absent_baseline_preserved'
    assert receipt['file_sha256'] == {}
    assert not list((run / 'assets/dataDir/courses/pikmin2room').iterdir())


def test_partial_mesh_refused(tmp_path):
    imported = fake_imported(tmp_path / 'imported')
    (imported / FOLDERS['Houdai'] / 'enemy.bmd').unlink()
    with pytest.raises(ValueError, match='Incomplete'):
        plan(imported, [(1, 'Houdai'), (2, 'BigFoot')])


def test_sibling_generator_overlap_refused(tmp_path):
    imported = fake_imported(tmp_path / 'imported')
    run = fake_run(tmp_path)
    (run / 'p2-dweevil-actors.txt').write_text('P2_DWEEVIL_ACTORS_1 1\n312001\n')
    with pytest.raises(ValueError, match='overlap'):
        install(imported, run, [(312001, 'Houdai')])


def test_non_junction_room_required(tmp_path):
    imported = fake_imported(tmp_path / 'imported')
    run = tmp_path / 'run'
    run.mkdir()
    with pytest.raises(ValueError, match='non-junction'):
        install(imported, run, [(1, 'Houdai')])


def test_roster_translation_only(tmp_path):
    data, actors = staged(tmp_path)
    assert struct.unpack_from('>I', data, 20)[0] == 1 + len(arena.SPECIES)
    assert [a['species'] for a in actors] == list(arena.SPECIES)
    assert [a['generator'] for a in actors] == list(arena.IDS)
    assert [a['native_teki_type'] for a in actors] == [
        arena.PROXY[s] for s in arena.SPECIES]
    assert [tuple(a['expected_xyz']) for a in actors] == [
        tuple(p) for p in arena.POSITIONS]
    for actor in actors:
        assert actor['offset'] == [0, 0, 0]
        assert actor['source_yaw'] is None and actor['source_yaw_applied'] is False


def test_generator_id_collision_rejected(tmp_path):
    with pytest.raises(ValueError, match='collision'):
        staged(tmp_path, existing=[entry(identity=312002)])


def test_gates_cover_open_items():
    for gate in ('native_identity', 'ik_leg_stability', 'foot_crush',
                 'houdai_gun_callback', 'skeletal_playback'):
        assert gate in arena.GATES
    assert 'Chappy' in arena.BLOCKED['natural_AI']
def test_damagumo_requires_demon_profile(tmp_path):
    imported = fake_imported(tmp_path / 'imported')
    with pytest.raises(ValueError, match='demon-lane source profile'):
        plan(imported, [(312004, 'Damagumo')])


def test_damagumo_requires_demon_mesh(tmp_path):
    imported = fake_imported(tmp_path / 'imported', damagumo=True)
    (imported / FOLDERS['Damagumo'] / 'enemy.bmd').unlink()
    with pytest.raises(ValueError, match='Missing Damagumo source mesh'):
        plan(imported, [(312004, 'Damagumo')])


def test_damagumo_mesh_hash_mismatch_rejected(tmp_path):
    imported = fake_imported(tmp_path / 'imported', damagumo=True,
                             damagumo_tamper=True)
    with pytest.raises(ValueError, match='hash mismatch'):
        plan(imported, [(312004, 'Damagumo')])


def test_unused_damagumo_mesh_refused(tmp_path):
    imported = fake_imported(tmp_path / 'imported', damagumo=True)
    with pytest.raises(ValueError, match='Unused Damagumo'):
        plan(imported, [(1, 'Houdai')])


def test_damagumo_install_and_verify_roundtrip(tmp_path):
    imported = fake_imported(tmp_path / 'imported', damagumo=True)
    run = fake_run(tmp_path)
    actors = [(312001, 'Houdai'), (312004, 'Damagumo')]
    receipt = install(imported, run, actors)
    assert receipt['visuals'] == 'installed'
    assert set(receipt['file_sha256']) == {'Houdai', 'Damagumo'}
    assert receipt['damagumo_manifest_sha256'] is not None
    verified = verify_install(imported, run, actors)
    assert verified['verified'] == ['Damagumo', 'Houdai']
    config = (run / ACTORS_TXT).read_text().split()
    assert config[:6] == [ACTORS_HEADER, '2', '312001', 'Houdai', '312004', 'Damagumo']
    profile = (run / 'p2-long-legs-profile.txt').read_text()
    assert 'species Damagumo 56 Beady Long Legs' in profile
    assert 'folder Damagumo Demon' in profile
    bank = (run / 'p2-long-legs-bank.txt').read_text()
    assert 'species Damagumo 56' in bank
    assert 'clip Damagumo landing' in bank


def test_damagumo_missing_anchor_rejected(tmp_path):
    imported = fake_imported(tmp_path / 'imported', damagumo=True)
    meta = json.loads((imported / DAMAGUMO_MANIFEST).read_text())
    meta['profiles']['56']['animation_rows'].pop(ANCHORS['Damagumo'][0])
    (imported / DAMAGUMO_MANIFEST).write_text(json.dumps(meta))
    with pytest.raises(ValueError, match='anchor'):
        plan(imported, [(312004, 'Damagumo')])


def test_damagumo_never_aliases_houdai(tmp_path):
    imported = fake_imported(tmp_path / 'imported', damagumo=True)
    run = fake_run(tmp_path)
    receipt = install(imported, run, [(312004, 'Damagumo')])
    assert receipt['actors'] == [[312004, 'Damagumo']]
    assert 'Damagumo' not in {a for _, a in [(312004, 'Houdai')]}
    config = (run / ACTORS_TXT).read_text().split()
    assert 'Houdai' not in config
    assert (run / 'assets/dataDir/courses/pikmin2room/Damagumo_enemy.bmd').is_file()


def test_base_only_install_unchanged(tmp_path):
    imported = fake_imported(tmp_path / 'imported')
    run = fake_run(tmp_path)
    receipt = install(imported, run, [(312001, 'Houdai'), (312002, 'BigFoot')])
    assert receipt['damagumo_manifest_sha256'] is None
    assert set(receipt['file_sha256']) == {'Houdai', 'BigFoot'}
    assert not (run / 'assets/dataDir/courses/pikmin2room/Damagumo_enemy.bmd').exists()


def test_arena_stages_damagumo_slot():
    assert 'Damagumo' in arena.SPECIES
    assert 312004 in arena.IDS
    assert arena.SPECIES[arena.IDS.index(312004)] == 'Damagumo'
    assert arena.PROXY['Damagumo'] is not None
    assert arena.POSITIONS[arena.IDS.index(312004)] == (-240.0, 30.0, 1850.0)
    assert 'Houdai' in arena.SPECIES and 'BigFoot' in arena.SPECIES
