"""Arena contract tests for the BigTreasure placement lane (#246).

Modeled on ``tests/test_pikmin2_aquatic_install.py``. Covers the arena's
placement contract (Chappy placement vehicle, unique generator IDs,
translation-only poses) and the honest gate/status ledger, plus install
branches not already covered by ``tests/test_pikmin2_bigtreasure_install.py``
(changed-receipt refusal, complete external-dependency receipt).
"""
import json
import struct
from pathlib import Path
from unittest.mock import patch

import pytest

import experimental.pikmin2_bigtreasure_arena as arena
from experimental.pikmin2_bigtreasure_arena import (GATES, IDS, P1_CHAPPY_TYPE,
                                                    POSITIONS, PROXY, STATUS, roster)
from experimental.pikmin2_bigtreasure_install import install


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


def test_proxy_is_chappy_placement_vehicle():
    # engine/include/teki.h: 3 Chappy (Dwarf Bulborb).
    assert P1_CHAPPY_TYPE == 3
    assert PROXY['BigTreasure'] == P1_CHAPPY_TYPE
    assert PROXY['P1 Chappy'] == P1_CHAPPY_TYPE
    assert set(PROXY) == set(arena.SPECIES)


def test_gates_and_status_coverage():
    for gate in ('native_identity', 'weapon_ownership_teardown', 'per_element_attacks',
                 'motion_staging', 'natural_AI', 'fsm_host', 'combat', 'damage_receivers',
                 'loozy_model', 'skeletal_playback', 'spawn', 'reload'):
        assert gate in GATES
        assert gate in STATUS
    assert set(GATES) == set(STATUS)
    assert STATUS['weapon_ownership_teardown'].startswith('probe-verified')
    assert STATUS['per_element_attacks'].startswith('probe-verified')
    assert STATUS['motion_staging'].startswith('partial')
    assert '2/29' in STATUS['motion_staging']
    for gate in ('native_identity', 'natural_AI', 'fsm_host', 'combat',
                 'damage_receivers', 'loozy_model', 'skeletal_playback'):
        assert 'blocked' in STATUS[gate].lower()
    for gate in ('spawn', 'reload'):
        assert STATUS[gate].startswith('untested')


def test_unique_generator_ids():
    assert len(set(IDS)) == len(IDS)
    assert set(IDS) == {246001, 246002}


def test_roster_requires_real_stage_records():
    with pytest.raises(Exception):
        roster(Path('missing'))


def test_roster_two_actors_translation_only(tmp_path):
    data, actors = staged(tmp_path)
    assert struct.unpack_from('>I', data, 20)[0] == 3
    assert [a['species'] for a in actors] == list(arena.SPECIES)
    assert [a['generator'] for a in actors] == list(arena.IDS)
    assert [a['native_teki_type'] for a in actors] == [P1_CHAPPY_TYPE, P1_CHAPPY_TYPE]
    assert [tuple(a['expected_xyz']) for a in actors] == [tuple(p) for p in POSITIONS]
    for actor in actors:
        assert actor['offset'] == [0, 0, 0]
        assert actor['source_yaw'] is None and actor['source_yaw_applied'] is False
        assert len(actor['expected_xyz']) == 3
    assert actors[0]['proxy'].startswith('P1 Chappy placement vehicle')
    assert actors[1]['proxy'] == 'ordinary P1 control'


def test_generator_id_collision_rejected(tmp_path):
    with pytest.raises(ValueError, match='collision'):
        staged(tmp_path, existing=[entry(identity=246001)])


def test_arena_uses_existing_install():
    from experimental import pikmin2_bigtreasure_install as install_mod
    assert arena.install is install_mod.install
    assert callable(arena.prepare)


def test_install_refuses_changed_receipt(tmp_path):
    run = tmp_path / 'run'
    run.mkdir()
    install(run)
    receipt = run / 'bigtreasure-install.json'
    payload = json.loads(receipt.read_text(encoding='utf-8'))
    payload['profile_sha256'] = '0' * 64
    receipt.write_text(json.dumps(payload), encoding='utf-8')
    profile = run / 'p2-bigtreasure-profile.txt'
    before = profile.read_bytes()
    with pytest.raises(SystemExit):
        install(run)
    assert profile.read_bytes() == before


def test_install_receipt_external_dependencies_complete(tmp_path):
    run = tmp_path / 'run'
    run.mkdir()
    payload = install(run)
    assert set(payload['external_dependencies']) == {
        'models_motions:#128', 'pellet_configs:disc_data', 'mpellet_drop_code:disc_data'}
