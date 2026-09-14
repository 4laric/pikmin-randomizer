"""BombSarai install/arena tests covering INSTALLED artifacts (#244).

Modeled on ``tests/test_pikmin2_aquatic_install.py``. Uses a synthetic schema-1
``P2_BOMBSARAI_IMPORT_1`` import with real pose bytes and recorded SHA-256
hashes; the lane defines the schema because no upstream extraction manifest
exists.
"""
import struct
import json
from pathlib import Path
from unittest.mock import patch

import pytest

import experimental.pikmin2_bombsarai_arena as arena
from experimental.pikmin2_bombsarai_arena import (GATES, GATE_STATES, P1_CHAPPY_TYPE,
                                                  P1_MAR_TYPE, POSITIONS, PROXY, roster)
from experimental.pikmin2_bombsarai_install import (ACTORS_HEADER, ACTORS_TXT, ANCHORS,
                                                    install, plan, sha, verify_install)

SOURCE_REVISION = '632af93787b9c95b63f0c13be32b161375ce3a96'


def fake_imported(root, omit_poses=False, tamper=False):
    """Synthetic schema-1 BombSarai import: real bytes, recorded hashes."""
    root.mkdir(parents=True)
    species_dir = root / 'BombSarai'
    species_dir.mkdir()
    clips = []
    for clip in ANCHORS:
        pose = f'bombsarai_BombSarai_{clip}_00.mod'
        data = f'BombSarai:{clip}:pose'.encode()
        if not omit_poses:
            (species_dir / pose).write_bytes(data)
        clips.append(dict(name=clip, status='converted', events=[[10, 2]], source_frames=30,
                          poses=[dict(file=pose, frame=0, bytes=len(data), sha256=sha(data))]))
    manifest = dict(schema=1, policy='P2_BOMBSARAI_IMPORT_1', disc_id='GPVE01', disc_revision=0,
                    source_revision=SOURCE_REVISION, native_ready=False,
                    gameplay_events_executed=False,
                    payload=dict(enemy='Bomb', enemy_id=36, child_num=2),
                    species={'BombSarai': dict(
                        enemy_id=58, role='concrete spawnable',
                        parameter_blocks=[{}, {'fp00': 1500.0, 'fp06': 60.0},
                                          {'fp01': 70.0, 'fp03': 50.0}],
                        clips=clips)})
    (root / 'bombsarai.json').write_text(json.dumps(manifest))
    if tamper:
        (species_dir / 'bombsarai_BombSarai_wait1_00.mod').write_bytes(b'TAMPERED')
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


def staged(tmp_path, existing=None, template=None):
    source = tmp_path / 'dataDir/stages/practice/default.gen'
    source.parent.mkdir(parents=True)
    source.write_bytes(b'1.0v' + struct.pack('>4fI', 47, 30, 1919, 180, 1))
    with patch.object(arena, 'records', return_value=existing or [entry(b'goal')]), \
            patch.object(arena, 'generator', return_value=b'x' * 24 + (template or entry())):
        return arena.roster(tmp_path)


def test_actor_count_rejected_before_io():
    for actors in ([], [(i, 'BombSarai') for i in range(101)]):
        with pytest.raises(ValueError):
            plan(Path('missing'), actors)


def test_duplicate_and_invalid_ids_rejected(tmp_path):
    imported = fake_imported(tmp_path / 'imported')
    with pytest.raises(ValueError):
        plan(imported, [(5, 'BombSarai'), (5, 'BombSarai')])
    for bad in [(-1, 'BombSarai'), ('5', 'BombSarai'), (True, 'BombSarai'), (1, 'Mar')]:
        with pytest.raises(ValueError):
            plan(imported, [bad])


def test_schema_and_identity_rejected(tmp_path):
    imported = fake_imported(tmp_path / 'imported')
    manifest = imported / 'bombsarai.json'
    meta = json.loads(manifest.read_text())
    for key, value in (('schema', 2), ('policy', 'P2_FLYING_1'),
                       ('disc_id', 'GPVJ01'), ('disc_revision', 1),
                       ('source_revision', 'deadbeef')):
        broken = dict(meta, **{key: value})
        manifest.write_text(json.dumps(broken))
        with pytest.raises(ValueError):
            plan(imported, [(1, 'BombSarai')])
        manifest.write_text(json.dumps(meta))
    broken = json.loads(json.dumps(meta))
    broken['species']['BombSarai']['enemy_id'] = 99
    manifest.write_text(json.dumps(broken))
    with pytest.raises(ValueError, match='species/ID'):
        plan(imported, [(1, 'BombSarai')])
    broken = json.loads(json.dumps(meta))
    broken['payload']['child_num'] = 5
    manifest.write_text(json.dumps(broken))
    with pytest.raises(ValueError, match='payload'):
        plan(imported, [(1, 'BombSarai')])
    broken = json.loads(json.dumps(meta))
    broken['species'].pop('BombSarai')
    manifest.write_text(json.dumps(broken))
    with pytest.raises(ValueError):
        plan(imported, [(1, 'BombSarai')])


def test_missing_anchor_rejected(tmp_path):
    imported = fake_imported(tmp_path / 'imported')
    manifest = imported / 'bombsarai.json'
    meta = json.loads(manifest.read_text())
    meta['species']['BombSarai']['clips'] = [
        clip for clip in meta['species']['BombSarai']['clips'] if clip['name'] != 'release1']
    manifest.write_text(json.dumps(meta))
    with pytest.raises(ValueError, match='anchor'):
        plan(imported, [(1, 'BombSarai')])


def test_unknown_clip_rejected(tmp_path):
    imported = fake_imported(tmp_path / 'imported')
    manifest = imported / 'bombsarai.json'
    meta = json.loads(manifest.read_text())
    meta['species']['BombSarai']['clips'].append(
        dict(name='invented1', status='converted', events=[], source_frames=1,
             poses=[dict(file='invented1.mod', frame=0, sha256='0' * 64)]))
    manifest.write_text(json.dumps(meta))
    with pytest.raises(ValueError, match='clip bank'):
        plan(imported, [(1, 'BombSarai')])


def test_pose_hash_mismatch_rejected(tmp_path):
    imported = fake_imported(tmp_path / 'imported', tamper=True)
    with pytest.raises(ValueError, match='hash mismatch'):
        plan(imported, [(1, 'BombSarai')])


def test_install_and_verify_roundtrip(tmp_path):
    imported = fake_imported(tmp_path / 'imported')
    run = fake_run(tmp_path)
    actors = [(244001, 'BombSarai'), (244002, 'BombSarai')]
    expected = {f'bombsarai_BombSarai_{clip}_00.mod' for clip in ANCHORS}
    receipt = install(imported, run, actors)
    assert receipt['visuals'] == 'installed'
    assert set(receipt['file_sha256']) == expected
    for name, value in receipt['file_sha256'].items():
        installed = (run / 'assets/dataDir/courses/pikmin2room' / name).read_bytes()
        assert sha(installed) == value
    verified = verify_install(imported, run, actors)
    assert verified['verified'] == sorted(expected)
    config = (run / ACTORS_TXT).read_text().split()
    assert config[:4] == [ACTORS_HEADER, '2', '244001', 'BombSarai']


def test_receipt_records_provenance(tmp_path):
    imported = fake_imported(tmp_path / 'imported')
    run = fake_run(tmp_path)
    receipt = install(imported, run, [(244001, 'BombSarai')])
    assert receipt['policy'] == 'P2_BOMBSARAI_IMPORT_1'
    assert receipt['enemy_id'] == 58
    assert receipt['native_ready'] is False
    assert receipt['audit']['source_revision'] == SOURCE_REVISION
    assert receipt['audit']['payload'] == dict(enemy='Bomb', enemy_id=36, child_num=2)


def test_install_refuses_overwrite(tmp_path):
    imported = fake_imported(tmp_path / 'imported')
    run = fake_run(tmp_path)
    install(imported, run, [(1, 'BombSarai')])
    with pytest.raises(ValueError, match='Refusing existing'):
        install(imported, run, [(2, 'BombSarai')])


def test_verify_detects_tampered_installed_pose(tmp_path):
    imported = fake_imported(tmp_path / 'imported')
    run = fake_run(tmp_path)
    install(imported, run, [(1, 'BombSarai')])
    target = run / 'assets/dataDir/courses/pikmin2room/bombsarai_BombSarai_dead1_00.mod'
    target.write_bytes(b'X')
    with pytest.raises(ValueError, match='visual mismatch'):
        verify_install(imported, run, [(1, 'BombSarai')])


def test_verify_detects_config_tamper(tmp_path):
    imported = fake_imported(tmp_path / 'imported')
    run = fake_run(tmp_path)
    install(imported, run, [(1, 'BombSarai')])
    (run / ACTORS_TXT).write_text(f'{ACTORS_HEADER}\n1\n999 BombSarai\n')
    with pytest.raises(ValueError, match='actor config mismatch'):
        verify_install(imported, run, [(1, 'BombSarai')])


def test_absent_visual_bank_preserves_baseline(tmp_path):
    imported = fake_imported(tmp_path / 'imported', omit_poses=True)
    run = fake_run(tmp_path)
    receipt = install(imported, run, [(1, 'BombSarai')])
    assert receipt['visuals'] == 'absent_baseline_preserved'
    assert receipt['file_sha256'] == {}
    assert not list((run / 'assets/dataDir/courses/pikmin2room').iterdir())


def test_partial_visual_bank_refused(tmp_path):
    imported = fake_imported(tmp_path / 'imported')
    (imported / 'BombSarai' / 'bombsarai_BombSarai_release1_00.mod').unlink()
    with pytest.raises(ValueError, match='Incomplete'):
        plan(imported, [(1, 'BombSarai')])


def test_sibling_generator_overlap_refused(tmp_path):
    imported = fake_imported(tmp_path / 'imported')
    run = fake_run(tmp_path)
    (run / 'p2-dwarf-bear-actors.txt').write_text('P2_DWARF_BEAR_ACTORS_1 1\n244001\n')
    with pytest.raises(ValueError, match='overlap'):
        install(imported, run, [(244001, 'BombSarai')])


def test_non_junction_room_required(tmp_path):
    imported = fake_imported(tmp_path / 'imported')
    run = tmp_path / 'run'
    run.mkdir()
    with pytest.raises(ValueError, match='non-junction'):
        install(imported, run, [(1, 'BombSarai')])


def test_proxy_types_match_native_registry():
    # engine/include/teki.h:97: TEKI_Mar = 16 (Puffy Blowhog); 3 Chappy control.
    assert P1_MAR_TYPE == 16
    assert P1_CHAPPY_TYPE == 3
    assert PROXY['BombSarai'] == P1_MAR_TYPE
    assert PROXY['P1 Chappy'] == P1_CHAPPY_TYPE


def test_gates_cover_runtime_evidence():
    for gate in ('native_identity', 'carrier_fsm', 'blast_routing', 'visual_assets',
                 'save_resume', 'induction_ip02', 'animated_capture_joint'):
        assert gate in GATES
    assert 'blocked' in GATE_STATES['native_identity'].lower()
    pass_partial = sum(1 for value in GATE_STATES.values()
                       if value.startswith(('pass', 'partial')))
    assert pass_partial > len(GATES) // 2


def test_scenario_profiles_use_body_relative_joint():
    for name, payload in arena.scenario_payloads().items():
        lines = payload.decode('ascii').split('\r\n')
        assert 'joint 0 -40 0' in lines and 'joint 0 55 0' not in lines
    assert GATE_STATES['animated_capture_joint'].startswith('pass')


def test_roster_requires_real_stage_records():
    with pytest.raises(Exception):
        roster(Path('missing'))


def test_roster_actors_translation_only(tmp_path):
    data, actors = staged(tmp_path)
    assert struct.unpack_from('>I', data, 20)[0] == 3
    assert [a['species'] for a in actors] == list(arena.SPECIES)
    assert [a['generator'] for a in actors] == list(arena.IDS)
    assert [a['native_teki_type'] for a in actors] == [P1_MAR_TYPE, P1_CHAPPY_TYPE]
    assert [tuple(a['expected_xyz']) for a in actors] == [tuple(p) for p in POSITIONS]
    for actor in actors:
        assert actor['offset'] == [0, 0, 0]
        assert actor['source_yaw'] is None and actor['source_yaw_applied'] is False
        assert len(actor['expected_xyz']) == 3


def test_generator_id_collision_rejected(tmp_path):
    with pytest.raises(ValueError, match='collision'):
        staged(tmp_path, existing=[entry(identity=244002)])
