"""BombSarai install/arena tests covering INSTALLED artifacts, not just output/ (#244).

Modeled on ``tests/test_pikmin2_aquatic_install.py`` (#374). Uses a synthetic
schema-1 BombSarai import with real bytes and recorded SHA-256 hashes; no disc
data, converted asset or native actor is required.
"""
import struct
import json
from pathlib import Path
from unittest.mock import patch

import pytest

import experimental.pikmin2_bombsarai_arena as arena
from experimental.pikmin2_bombsarai_arena import (GATES, GATE_STATES, IDS, P1_CHAPPY_TYPE,
                                                  P1_PUFFY_TYPE, POSITIONS, PROXY, SPECIES,
                                                  roster)
from experimental.pikmin2_bombsarai_install import (ACTORS_HEADER, ACTORS_TXT,
                                                    install, plan, sha, verify_install)

ANCHORS = {'BombSarai': ('wait1', 'release1', 'dead1'),
           'Bomb': ('hit_start', 'hit_loop')}
ENEMY_IDS = {'BombSarai': 58, 'Bomb': 36}
BLOCKS = {'BombSarai': [{'s000': 0.5}, {'fp00': 1500.0}, {'fp01': 70.0}],
          'Bomb': [{'s000': 0.5}, {'fp00': 4.5}, {'fp01': 500.0, 'fp02': 50.0}]}


def fake_imported(root, omit_poses=False, tamper=False):
    """Synthetic schema-1 BombSarai import: real bytes, recorded hashes."""
    root.mkdir(parents=True)
    species = {}
    for name, identity in ENEMY_IDS.items():
        (root / name).mkdir()
        clips = []
        for clip in ANCHORS[name]:
            pose = f'bombsarai_{name}_{clip}_00.mod'
            data = f'{name}:{clip}:pose'.encode()
            if not omit_poses:
                (root / name / pose).write_bytes(data)
            clips.append(dict(name=clip, status='converted', events=[], source_frames=10,
                              poses=[dict(file=pose, frame=0, bytes=len(data), sha256=sha(data))]))
        species[name] = dict(enemy_id=identity, role='concrete spawnable',
                             parameter_blocks=BLOCKS[name], clips=clips)
    manifest = dict(schema=1, policy='P2_BOMBSARAI_IMPORT_1', disc_id='GPVE01', disc_revision=0,
                    native_ready=False, gameplay_events_executed=False, btk_playback=False,
                    species=species)
    (root / 'bombsarai.json').write_text(json.dumps(manifest))
    if tamper:
        (root / 'BombSarai' / 'bombsarai_BombSarai_wait1_00.mod').write_bytes(b'TAMPERED')
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
    for bad in [(-1, 'BombSarai'), ('5', 'BombSarai'), (True, 'BombSarai'), (1, 'Fuefuki')]:
        with pytest.raises(ValueError):
            plan(imported, [bad])


def test_schema_and_identity_rejected(tmp_path):
    imported = fake_imported(tmp_path / 'imported')
    meta = json.loads((imported / 'bombsarai.json').read_text())
    for key, value in (('schema', 2), ('policy', 'P2_AQUATIC_IMPORT_1'),
                       ('disc_id', 'GPVJ01'), ('disc_revision', 1)):
        broken = dict(meta, **{key: value})
        (imported / 'bombsarai.json').write_text(json.dumps(broken))
        with pytest.raises(ValueError):
            plan(imported, [(1, 'BombSarai')])
        (imported / 'bombsarai.json').write_text(json.dumps(meta))
    broken = json.loads(json.dumps(meta))
    broken['species']['BombSarai']['enemy_id'] = 99
    (imported / 'bombsarai.json').write_text(json.dumps(broken))
    with pytest.raises(ValueError, match='species/ID'):
        plan(imported, [(1, 'BombSarai')])
    broken = json.loads(json.dumps(meta))
    broken['species'].pop('Bomb')
    (imported / 'bombsarai.json').write_text(json.dumps(broken))
    with pytest.raises(ValueError):
        plan(imported, [(1, 'BombSarai')])


def test_missing_anchor_rejected(tmp_path):
    imported = fake_imported(tmp_path / 'imported')
    meta = json.loads((imported / 'bombsarai.json').read_text())
    meta['species']['BombSarai']['clips'] = [
        clip for clip in meta['species']['BombSarai']['clips'] if clip['name'] != 'release1']
    (imported / 'bombsarai.json').write_text(json.dumps(meta))
    with pytest.raises(ValueError, match='anchor'):
        plan(imported, [(1, 'BombSarai')])


def test_pose_hash_mismatch_rejected(tmp_path):
    imported = fake_imported(tmp_path / 'imported', tamper=True)
    with pytest.raises(ValueError, match='hash mismatch'):
        plan(imported, [(1, 'BombSarai')])


def test_install_and_verify_roundtrip(tmp_path):
    imported = fake_imported(tmp_path / 'imported')
    run = fake_run(tmp_path)
    actors = [(244001, 'BombSarai'), (244002, 'Bomb')]
    receipt = install(imported, run, actors)
    assert receipt['visuals'] == 'installed'
    assert receipt['policy'] == 'P2_BOMBSARAI_IMPORT_1'
    assert receipt['native_ready'] is False
    expected = {'bombsarai_BombSarai_wait1_00.mod', 'bombsarai_BombSarai_release1_00.mod',
                'bombsarai_BombSarai_dead1_00.mod', 'bombsarai_Bomb_hit_start_00.mod',
                'bombsarai_Bomb_hit_loop_00.mod'}
    assert set(receipt['file_sha256']) == expected
    for name, value in receipt['file_sha256'].items():
        installed = (run / 'assets/dataDir/courses/pikmin2room' / name).read_bytes()
        assert sha(installed) == value
    verified = verify_install(imported, run, actors)
    assert verified['verified'] == sorted(expected)
    config = (run / ACTORS_TXT).read_text().split()
    assert config[:4] == [ACTORS_HEADER, '2', '244001', 'BombSarai']


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
    (run / ACTORS_TXT).write_text('P2_BOMBSARAI_ACTORS_1\n1\n999 BombSarai\n')
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
    # engine/include/teki.h: 16 Mar (Puffy Blowhog), 3 Chappy (Dwarf Bulborb).
    assert P1_PUFFY_TYPE == 16
    assert P1_CHAPPY_TYPE == 3
    assert PROXY['BombSarai'] == P1_PUFFY_TYPE
    assert PROXY['P1 Chappy'] == P1_CHAPPY_TYPE
    assert 'Puffy Blowhog' in arena.FAMILY[P1_PUFFY_TYPE]


def test_gates_cover_lane_open_items():
    for gate in ('native_identity', 'bomb_lob_flight', 'projectile_lifecycle',
                 'hover_flight', 'blast_routing', 'carrier_fsm', 'death_drop',
                 'bitter_purple_interrupt', 'pool_exhaustion',
                 'kamu_joint_capture', 'multi_projectile_induction',
                 'persistence_reload', 'visual_fidelity'):
        assert gate in GATES
    assert set(GATES) == set(GATE_STATES)
    assert 'blocked' in GATE_STATES['native_identity'].lower()
    assert GATE_STATES['bomb_lob_flight'].startswith('pass')
    assert GATE_STATES['visual_fidelity'].startswith('blocked')
    for state in GATE_STATES.values():
        assert state.split(':', 1)[0] in ('pass', 'partial', 'blocked', 'untested'), state


def test_roster_requires_real_stage_records():
    with pytest.raises(Exception):
        roster(Path('missing'))


def test_roster_actors_translation_only(tmp_path):
    data, actors = staged(tmp_path)
    assert struct.unpack_from('>I', data, 20)[0] == 3
    assert [a['species'] for a in actors] == list(SPECIES)
    assert [a['generator'] for a in actors] == list(IDS)
    assert [a['native_teki_type'] for a in actors] == [P1_PUFFY_TYPE, P1_CHAPPY_TYPE]
    assert [tuple(a['expected_xyz']) for a in actors] == [tuple(p) for p in POSITIONS]
    for actor in actors:
        assert actor['offset'] == [0, 0, 0]
        assert actor['source_yaw'] is None and actor['source_yaw_applied'] is False
        assert len(actor['expected_xyz']) == 3


def test_generator_id_collision_rejected(tmp_path):
    with pytest.raises(ValueError, match='collision'):
        staged(tmp_path, existing=[entry(identity=244001)])
