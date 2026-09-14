"""Fuefuki (Antenna Beetle) arena contract + install-contract tests (#245).

Modeled on ``tests/test_pikmin2_aquatic_install.py`` and
``tests/test_pikmin2_dwarf_bear_arena.py``. Arena checks cover the proxy
constants, honest real-GL gate statuses, the two-actor translation-only roster
and generator-ID uniqueness. Install checks exercise the existing
``experimental/pikmin2_fuefuki_install.py`` module without editing it.
"""
import json
import struct
from pathlib import Path
from unittest.mock import patch

import pytest

import experimental.pikmin2_fuefuki_arena as arena
from experimental.pikmin2_fuefuki_arena import (BLOCKED, GATES, IDS, P1_CHAPPY_TYPE,
                                                P1_NAPKID_TYPE, PASSED, POSITIONS,
                                                PROXY, SPECIES, STATUS, roster)
from experimental.pikmin2_fuefuki_install import (ENEMY_ID, INSTALL_JSON, PROFILE_TXT,
                                                  SEAM_BINDINGS, SEAM_VERSION, install,
                                                  profile_text, sha)


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


def test_proxy_types_match_native_registry():
    # engine/include/teki.h: 11 Napkid (Swooping Snitchbug), 3 Chappy.
    assert P1_NAPKID_TYPE == 11
    assert P1_CHAPPY_TYPE == 3
    assert PROXY['Fuefuki'] == P1_NAPKID_TYPE
    assert PROXY['P1 Chappy'] == P1_CHAPPY_TYPE
    assert 'Napkid' in arena.FAMILY[P1_NAPKID_TYPE]


def test_gate_status_matches_real_gl_evidence():
    for gate in ('whistle_theft', 'interference', 'reclaim', 'carry', 'brain_fallback'):
        assert gate in GATES
        assert STATUS[gate] == PASSED[gate]
        assert STATUS[gate].startswith('pass')
    for gate in ('follow_locomotion', 'panic_staging', 'claim_persistence',
                 'native_identity', 'press_combat'):
        assert gate in GATES
        assert STATUS[gate] == BLOCKED[gate]
        assert STATUS[gate].startswith('blocked')
    assert STATUS['spawn'] == 'untested'
    assert set(STATUS) == set(GATES)


def test_roster_requires_real_stage_records():
    with pytest.raises(Exception):
        roster(Path('missing'))


def test_roster_two_actors_translation_only(tmp_path):
    data, actors = staged(tmp_path)
    assert struct.unpack_from('>I', data, 20)[0] == 3
    assert [a['species'] for a in actors] == list(SPECIES)
    assert [a['generator'] for a in actors] == list(IDS)
    assert [a['native_teki_type'] for a in actors] == [P1_NAPKID_TYPE, P1_CHAPPY_TYPE]
    assert [tuple(a['expected_xyz']) for a in actors] == [tuple(p) for p in POSITIONS]
    assert actors[0]['expected_xyz'] == [-150., 30., 1850.]
    assert actors[1]['expected_xyz'] == [150., 30., 1550.]
    for actor in actors:
        assert actor['offset'] == [0, 0, 0]
        assert actor['source_yaw'] is None and actor['source_yaw_applied'] is False
        assert len(actor['expected_xyz']) == 3
    assert 'placement vehicle only' in actors[0]['proxy']
    assert actors[1]['proxy'] == 'ordinary P1 control'


def test_generator_ids_unique_and_collision_rejected(tmp_path):
    assert len(set(IDS)) == len(IDS)
    with pytest.raises(ValueError, match='collision'):
        staged(tmp_path, existing=[entry(identity=IDS[0])])


def test_invalid_expected_xyz_rejected(tmp_path, monkeypatch):
    monkeypatch.setattr(arena, 'POSITIONS', ((-150., 30., float('inf')), (150., 30., 1550.)))
    with pytest.raises(ValueError):
        staged(tmp_path)


def test_profile_text_is_canonical_seam_contract():
    text = profile_text()
    assert text.endswith('\n')
    rows = text.splitlines()
    assert rows[0] == SEAM_VERSION
    assert f'enemy fuefuki {ENEMY_ID} states 9 anims 10' in rows
    for name in SEAM_BINDINGS:
        assert f'binding {name} lane_owned' in rows
    assert 'external motion_bank:#128' in rows


def test_install_and_idempotent_reinstall(tmp_path):
    run = tmp_path / 'run'
    run.mkdir()
    receipt = install(run)
    assert receipt['status'] == 'installed'
    assert receipt['seam'] == SEAM_VERSION
    assert receipt['enemy_id'] == ENEMY_ID
    assert receipt['bindings'] == list(SEAM_BINDINGS)
    assert sha((run / PROFILE_TXT).read_bytes()) == receipt['profile_sha256']
    again = install(run)
    assert again['status'] == 'already-installed'
    assert again['profile_sha256'] == receipt['profile_sha256']


def test_install_refuses_tampered_profile_before_mutation(tmp_path):
    run = tmp_path / 'run'
    run.mkdir()
    install(run)
    (run / PROFILE_TXT).write_text('TAMPERED\n')
    with pytest.raises(SystemExit, match='refusing to overwrite changed profile'):
        install(run)


def test_install_refuses_changed_receipt(tmp_path):
    run = tmp_path / 'run'
    run.mkdir()
    install(run)
    receipt = json.loads((run / INSTALL_JSON).read_text())
    receipt['profile_sha256'] = '0' * 64
    (run / INSTALL_JSON).write_text(json.dumps(receipt))
    with pytest.raises(SystemExit, match='refusing to overwrite changed install receipt'):
        install(run)


def test_install_requires_existing_run_directory(tmp_path):
    with pytest.raises(SystemExit, match='private run directory missing'):
        install(tmp_path / 'missing')
