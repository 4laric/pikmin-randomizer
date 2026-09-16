"""Aquatic install/arena tests covering INSTALLED artifacts, not just output/ (#374).

Modeled on ``tests/test_pikmin2_mamuta_install.py`` and
``tests/test_pikmin2_kogane_install.py``. Uses a synthetic schema-1 aquatic
import with real bytes and recorded SHA-256 hashes.
"""
import struct
import json
from pathlib import Path
from unittest.mock import patch

import pytest

import experimental.pikmin2_aquatic_arena as arena
from experimental.pikmin2_aquatic_arena import (BLOCKED, GATES, P1_CHAPPY_TYPE,
                                               P1_NAMAZU_TYPE, P1_OTAMA_TYPE,
                                               POSITIONS, PROXY, roster)
from experimental.pikmin2_aquatic_install import (ACTORS_HEADER, ACTORS_TXT,
                                                  install, plan, sha,
                                                  verify_install)

ANCHORS = {'Catfish': ('wait1', 'attack', 'dead'),
           'Tadpole': ('wait1', 'move1', 'dead'),
           'Jigumo': ('wait1', 'attack1', 'dead1'),
           'UmiMushi': ('run1', 'attack1', 'dead1')}
IDS = {'Catfish': 26, 'Tadpole': 27, 'Jigumo': 63, 'UmiMushi': 71}


def fake_imported(root, omit_poses=False, tamper=False):
    """Synthetic schema-1 aquatic import: real bytes, recorded hashes."""
    root.mkdir(parents=True)
    species = {}
    for name, identity in IDS.items():
        (root / name).mkdir()
        clips = []
        for clip in ANCHORS[name]:
            pose = f'aquatic_{name}_{clip}_00.mod'
            data = f'{name}:{clip}:pose'.encode()
            if not omit_poses:
                (root / name / pose).write_bytes(data)
            clips.append(dict(name=clip, status='converted', events=[], source_frames=10,
                              poses=[dict(file=pose, frame=0, bytes=len(data), sha256=sha(data))]))
        species[name] = dict(enemy_id=identity, role='concrete spawnable',
                             parameter_blocks=[{}, {'fp00': 200.0}, {'fp01': 2.0}], clips=clips)
    manifest = dict(schema=1, policy='P2_AQUATIC_IMPORT_1', disc_id='GPVE01', disc_revision=0,
                    native_ready=False, gameplay_events_executed=False, btk_playback=False,
                    species=species)
    (root / 'aquatic.json').write_text(json.dumps(manifest))
    if tamper:
        (root / 'Catfish' / 'aquatic_Catfish_wait1_00.mod').write_bytes(b'TAMPERED')
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
    for actors in ([], [(i, 'Catfish') for i in range(101)]):
        with pytest.raises(ValueError):
            plan(Path('missing'), actors)


def test_duplicate_and_invalid_ids_rejected(tmp_path):
    imported = fake_imported(tmp_path / 'imported')
    with pytest.raises(ValueError):
        plan(imported, [(5, 'Catfish'), (5, 'Catfish')])
    for bad in [(-1, 'Catfish'), ('5', 'Catfish'), (True, 'Catfish'), (1, 'Namazu')]:
        with pytest.raises(ValueError):
            plan(imported, [bad])


def test_schema_and_identity_rejected(tmp_path):
    imported = fake_imported(tmp_path / 'imported')
    meta = json.loads((imported / 'aquatic.json').read_text())
    for key, value in (('schema', 2), ('policy', 'P2_FROG_IMPORT_1'),
                       ('disc_id', 'GPVJ01'), ('disc_revision', 1)):
        broken = dict(meta, **{key: value})
        (imported / 'aquatic.json').write_text(json.dumps(broken))
        with pytest.raises(ValueError):
            plan(imported, [(1, 'Catfish')])
        (imported / 'aquatic.json').write_text(json.dumps(meta))
    broken = json.loads(json.dumps(meta))
    broken['species']['Catfish']['enemy_id'] = 99
    (imported / 'aquatic.json').write_text(json.dumps(broken))
    with pytest.raises(ValueError, match='species/ID'):
        plan(imported, [(1, 'Catfish')])
    broken = json.loads(json.dumps(meta))
    broken['species'].pop('UmiMushi')
    (imported / 'aquatic.json').write_text(json.dumps(broken))
    with pytest.raises(ValueError):
        plan(imported, [(1, 'Catfish')])


def test_missing_anchor_rejected(tmp_path):
    imported = fake_imported(tmp_path / 'imported')
    meta = json.loads((imported / 'aquatic.json').read_text())
    meta['species']['Catfish']['clips'] = [
        clip for clip in meta['species']['Catfish']['clips'] if clip['name'] != 'attack']
    (imported / 'aquatic.json').write_text(json.dumps(meta))
    with pytest.raises(ValueError, match='anchor'):
        plan(imported, [(1, 'Catfish')])


def test_pose_hash_mismatch_rejected(tmp_path):
    imported = fake_imported(tmp_path / 'imported', tamper=True)
    with pytest.raises(ValueError, match='hash mismatch'):
        plan(imported, [(1, 'Catfish')])


def test_install_and_verify_roundtrip(tmp_path):
    imported = fake_imported(tmp_path / 'imported')
    run = fake_run(tmp_path)
    actors = [(374001, 'Catfish'), (374002, 'Tadpole')]
    receipt = install(imported, run, actors)
    assert receipt['visuals'] == 'installed'
    expected = {'aquatic_Catfish_wait1_00.mod', 'aquatic_Catfish_attack_00.mod',
                'aquatic_Catfish_dead_00.mod', 'aquatic_Tadpole_wait1_00.mod',
                'aquatic_Tadpole_move1_00.mod', 'aquatic_Tadpole_dead_00.mod'}
    assert set(receipt['file_sha256']) == expected
    for name, value in receipt['file_sha256'].items():
        installed = (run / 'assets/dataDir/courses/pikmin2room' / name).read_bytes()
        assert sha(installed) == value
    verified = verify_install(imported, run, actors)
    assert verified['verified'] == sorted(expected)
    config = (run / ACTORS_TXT).read_text().split()
    assert config[:4] == [ACTORS_HEADER, '2', '374001', 'Catfish']


def test_install_refuses_overwrite(tmp_path):
    imported = fake_imported(tmp_path / 'imported')
    run = fake_run(tmp_path)
    install(imported, run, [(1, 'Catfish')])
    with pytest.raises(ValueError, match='Refusing existing'):
        install(imported, run, [(2, 'Catfish')])


def test_verify_detects_tampered_installed_pose(tmp_path):
    imported = fake_imported(tmp_path / 'imported')
    run = fake_run(tmp_path)
    install(imported, run, [(1, 'Catfish')])
    target = run / 'assets/dataDir/courses/pikmin2room/aquatic_Catfish_dead_00.mod'
    target.write_bytes(b'X')
    with pytest.raises(ValueError, match='visual mismatch'):
        verify_install(imported, run, [(1, 'Catfish')])


def test_verify_detects_config_tamper(tmp_path):
    imported = fake_imported(tmp_path / 'imported')
    run = fake_run(tmp_path)
    install(imported, run, [(1, 'Catfish')])
    (run / ACTORS_TXT).write_text('P2_AQUATIC_ACTORS_1\n1\n999 Catfish\n')
    with pytest.raises(ValueError, match='actor config mismatch'):
        verify_install(imported, run, [(1, 'Catfish')])


def test_absent_visual_bank_preserves_baseline(tmp_path):
    imported = fake_imported(tmp_path / 'imported', omit_poses=True)
    run = fake_run(tmp_path)
    receipt = install(imported, run, [(1, 'Catfish')])
    assert receipt['visuals'] == 'absent_baseline_preserved'
    assert receipt['file_sha256'] == {}
    assert not list((run / 'assets/dataDir/courses/pikmin2room').iterdir())


def test_partial_visual_bank_refused(tmp_path):
    imported = fake_imported(tmp_path / 'imported')
    (imported / 'Catfish' / 'aquatic_Catfish_attack_00.mod').unlink()
    with pytest.raises(ValueError, match='Incomplete'):
        plan(imported, [(1, 'Catfish')])


def test_sibling_generator_overlap_refused(tmp_path):
    imported = fake_imported(tmp_path / 'imported')
    run = fake_run(tmp_path)
    (run / 'p2-dwarf-bear-actors.txt').write_text('P2_DWARF_BEAR_ACTORS_1 1\n374001\n')
    with pytest.raises(ValueError, match='overlap'):
        install(imported, run, [(374001, 'Catfish')])


def test_non_junction_room_required(tmp_path):
    imported = fake_imported(tmp_path / 'imported')
    run = tmp_path / 'run'
    run.mkdir()
    with pytest.raises(ValueError, match='non-junction'):
        install(imported, run, [(1, 'Catfish')])


def test_proxy_types_match_native_registry():
    # engine/include/teki.h: 30 Namazu (Water Dumple), 25 Otama (Wogpole), 3 Chappy.
    assert P1_NAMAZU_TYPE == 30
    assert P1_OTAMA_TYPE == 25
    assert P1_CHAPPY_TYPE == 3
    assert PROXY['Catfish'] == P1_NAMAZU_TYPE
    assert PROXY['Tadpole'] == P1_OTAMA_TYPE
    assert PROXY['Jigumo'] == P1_CHAPPY_TYPE
    assert PROXY['UmiMushi'] == P1_CHAPPY_TYPE


def test_gates_cover_batch1_open_items():
    for gate in ('native_identity', 'catfish_kochappy_fsm', 'tadpole_waterbox_leap',
                 'jigumo_panhouse_nest', 'umimushi_shared_mgr_blind',
                 'jigumo_proxy', 'umimushi_proxy'):
        assert gate in GATES
    assert 'blocked' in BLOCKED['jigumo_proxy'].lower()
    assert 'no P1 counterpart' in BLOCKED['umimushi_proxy']


def test_roster_requires_real_stage_records():
    with pytest.raises(Exception):
        roster(Path('missing'))


def test_roster_five_actors_translation_only(tmp_path):
    data, actors = staged(tmp_path)
    assert struct.unpack_from('>I', data, 20)[0] == 6
    assert [a['species'] for a in actors] == list(arena.SPECIES)
    assert [a['generator'] for a in actors] == list(arena.IDS)
    assert [a['native_teki_type'] for a in actors] == [
        P1_NAMAZU_TYPE, P1_OTAMA_TYPE, P1_CHAPPY_TYPE, P1_CHAPPY_TYPE, P1_CHAPPY_TYPE]
    assert [tuple(a['expected_xyz']) for a in actors] == [tuple(p) for p in POSITIONS]
    for actor in actors:
        assert actor['offset'] == [0, 0, 0]
        assert actor['source_yaw'] is None and actor['source_yaw_applied'] is False
        assert len(actor['expected_xyz']) == 3


def test_generator_id_collision_rejected(tmp_path):
    with pytest.raises(ValueError, match='collision'):
        staged(tmp_path, existing=[entry(identity=374003)])
