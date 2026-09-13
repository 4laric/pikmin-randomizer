"""Fuefuki (#245) arena contract and install-glue tests.

Arena checks cover the P1 proxy choice, the consolidated gate record and the
private-stage roster. Install checks cover the lane's opt-in profile glue
(``experimental/pikmin2_fuefuki_install.py``), which has no separate test file;
they live here so install coverage is not duplicated. There is no
``tests/test_pikmin2_fuefuki_install.py``.
"""
import json
import struct
from pathlib import Path
from unittest.mock import patch

import pytest

import experimental.pikmin2_fuefuki_arena as arena
from experimental.pikmin2_fuefuki_arena import (
    GATE_STATES, GATES, IDS, P1_CHAPPY_TYPE, P1_NAPKID_TYPE, POSITIONS, PROXY,
    roster, verify_profile)
from experimental.pikmin2_fuefuki_install import (
    ANIM_COUNT, ENEMY_ID, EXTERNAL_DEPS, INSTALL_JSON, PROFILE_TXT,
    SEAM_BINDINGS, SEAM_VERSION, STATE_COUNT, install, profile_text, sha)


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
    assert 'Snitchbug' in arena.FAMILY[P1_NAPKID_TYPE]


def test_gates_consolidate_runtime_evidence():
    assert set(GATES) == set(GATE_STATES)
    for gate in ('whistle_theft', 'interference_nonroute', 'follow_bookkeeping',
                 'panic_release', 'reclaim', 'carry_carcass', 'control_undisturbed'):
        assert GATE_STATES[gate].startswith('pass'), gate
    assert GATE_STATES['native_identity'].startswith('blocked')
    assert GATE_STATES['spawn_exact_xyz'].startswith('untested')


def test_gates_mark_unresolved_items_blocked():
    for gate in ('follow_locomotion', 'panic_staging', 'brain_fallback',
                 'claim_persistence', 'motion_bank_staging'):
        assert gate in GATES
        assert GATE_STATES[gate].startswith('blocked'), gate
    assert 'no P1 follow-teki action' in GATE_STATES['follow_locomotion']
    assert 'PIKISTATE_Normal' in GATE_STATES['panic_staging']
    assert '#128' in GATE_STATES['motion_bank_staging']


def test_roster_requires_real_stage_records():
    with pytest.raises(Exception):
        roster(Path('missing'))


def test_roster_beetle_plus_control_translation_only(tmp_path):
    data, actors = staged(tmp_path)
    assert struct.unpack_from('>I', data, 20)[0] == 3
    assert [a['species'] for a in actors] == list(arena.SPECIES)
    assert [a['generator'] for a in actors] == list(IDS)
    assert [a['native_teki_type'] for a in actors] == [P1_NAPKID_TYPE, P1_CHAPPY_TYPE]
    assert [tuple(a['expected_xyz']) for a in actors] == [tuple(p) for p in POSITIONS]
    for actor in actors:
        assert actor['offset'] == [0, 0, 0]
        assert actor['source_yaw'] is None and actor['source_yaw_applied'] is False
        assert len(actor['expected_xyz']) == 3
    assert 'placement vehicle only' in actors[0]['proxy']
    assert actors[1]['proxy'] == 'ordinary P1 control'


def test_generator_id_collision_rejected(tmp_path):
    with pytest.raises(ValueError, match='collision'):
        staged(tmp_path, existing=[entry(identity=245001)])


def test_profile_contract_tokens():
    text = profile_text()
    lines = text.splitlines()
    assert lines[0] == SEAM_VERSION
    assert f'enemy fuefuki {ENEMY_ID} states {STATE_COUNT} anims {ANIM_COUNT}' in lines
    for name in SEAM_BINDINGS:
        assert f'binding {name} lane_owned' in lines
    for dep in EXTERNAL_DEPS:
        assert f'external {dep}' in lines
    assert text.endswith('\n')


def test_install_and_idempotent_roundtrip(tmp_path):
    run = tmp_path / 'run'
    run.mkdir()
    receipt = install(run)
    assert receipt['status'] == 'installed'
    assert receipt['seam'] == SEAM_VERSION and receipt['enemy_id'] == ENEMY_ID
    data = profile_text().encode('utf-8')
    assert (run / PROFILE_TXT).read_bytes() == data
    assert receipt['profile_sha256'] == sha(data)
    verified = verify_profile(run)
    assert verified['profile_sha256'] == sha(data)
    again = install(run)
    assert again['status'] == 'already-installed'
    assert again['profile_sha256'] == sha(data)


def test_install_requires_private_run(tmp_path):
    with pytest.raises(SystemExit):
        install(tmp_path / 'missing')


def test_install_refuses_changed_profile(tmp_path):
    run = tmp_path / 'run'
    run.mkdir()
    install(run)
    (run / PROFILE_TXT).write_text('tampered\n')
    with pytest.raises(SystemExit, match='refusing to overwrite'):
        install(run)


def test_verify_profile_detects_profile_tamper(tmp_path):
    run = tmp_path / 'run'
    run.mkdir()
    install(run)
    (run / PROFILE_TXT).write_text('tampered\n')
    with pytest.raises(ValueError, match='profile mismatch'):
        verify_profile(run)


def test_verify_profile_detects_receipt_tamper(tmp_path):
    run = tmp_path / 'run'
    run.mkdir()
    install(run)
    receipt = json.loads((run / INSTALL_JSON).read_text())
    receipt['profile_sha256'] = '0' * 64
    (run / INSTALL_JSON).write_text(json.dumps(receipt))
    with pytest.raises(ValueError, match='receipt mismatch'):
        verify_profile(run)
