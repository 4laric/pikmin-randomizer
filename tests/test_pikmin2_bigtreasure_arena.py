"""BigTreasure (Titan Dweevil) arena contract tests plus install coverage (#246).

Modeled on ``tests/test_pikmin2_kogane_arena.py`` and the arena section of
``tests/test_pikmin2_aquatic_install.py``. Only arena-contract checks and
install coverage not already exercised by
``tests/test_pikmin2_bigtreasure_install.py`` live here.
"""
import struct
from pathlib import Path
from unittest.mock import patch

import pytest

import experimental.pikmin2_bigtreasure_arena as arena
from experimental.pikmin2_bigtreasure_install import (EXTERNAL_DEPS, PROFILE_TXT,
                                                      SEAM_BINDINGS, install,
                                                      profile_text)


def entry(kind=b'iket', identity=1):
    record = bytearray(100)
    record[:8] = b'    0.0v'
    struct.pack_into('<I', record, 8, identity)
    record[72:76] = kind
    return bytes(record)


def staged(tmp_path, existing=None, template=None):
    source = tmp_path / 'dataDir/stages/practice/default.gen'
    source.parent.mkdir(parents=True, exist_ok=True)
    source.write_bytes(b'1.0v' + struct.pack('>4fI', 47, 30, 1919, 180, 1))
    with patch.object(arena, 'records', return_value=existing or [entry(b'goal')]), \
            patch.object(arena, 'generator', return_value=b'x' * 24 + (template or entry())):
        return arena.roster(tmp_path)


def test_proxy_type_is_p1_chappy_from_teki_h():
    # engine/include/teki.h:84 - TEKI_Chappy = 3, "3, Dwarf Bulborb".
    assert arena.P1_CHAPPY_TYPE == 3
    assert arena.PROXY[arena.BIGTREASURE] == arena.P1_CHAPPY_TYPE
    assert arena.PROXY[arena.CONTROL] == arena.P1_CHAPPY_TYPE
    assert 'Dwarf Bulborb' in arena.FAMILY[arena.P1_CHAPPY_TYPE]


def test_gates_cover_arena_contract_and_status_is_complete():
    for gate in ('native_identity', 'spawn_exact_xyz', 'control_undisturbed',
                 'natural_AI', 'combat', 'death_corpse', 'carrier_recovery',
                 'reload', 'per_element_attacks', 'damage_receivers'):
        assert gate in arena.GATES
    for gate in ('weapon_ownership_teardown', 'motion_staging', 'fsm_host',
                 'loozy_model', 'skeletal_playback', 'arena_mixed_level_staging'):
        assert gate in arena.GATES
    assert tuple(arena.STATUS) == arena.GATES
    assert set(arena.BLOCKED) == {key for key, value in arena.STATUS.items()
                                  if value.startswith('blocked')}


def test_unresolved_items_recorded_honestly():
    assert 'unconverted' in arena.STATUS['loozy_model']
    assert 'no live skinning' in arena.STATUS['skeletal_playback']
    assert 'not registered' in arena.STATUS['damage_receivers']
    assert '12-state' in arena.STATUS['fsm_host']
    assert 'staged-phases' in arena.STATUS['arena_mixed_level_staging']
    assert 'staged_phases_gate' in profile_text()
    assert arena.STATUS['motion_staging'].startswith('partial')
    assert '2 of 29' in arena.STATUS['motion_staging']
    assert '27' in arena.STATUS['motion_staging']


def test_probe_evidence_not_overclaimed():
    assert arena.STATUS['weapon_ownership_teardown'].startswith('probe-verified')
    assert 'P2_BIGTREASURE_HOST_SEAM_PASS' in arena.STATUS['weapon_ownership_teardown']
    assert arena.STATUS['per_element_attacks'].startswith('probe-verified')
    assert 'remain unmeasured' in arena.STATUS['per_element_attacks']


def test_roster_requires_real_stage_records():
    with pytest.raises(Exception):
        arena.roster(Path('missing'))


def test_roster_actor_plus_control_translation_only(tmp_path):
    data, actors = staged(tmp_path)
    assert struct.unpack_from('>I', data, 20)[0] == 3  # goal + BigTreasure + control
    assert [a['species'] for a in actors] == list(arena.SPECIES)
    assert [a['generator'] for a in actors] == list(arena.IDS)
    assert [a['native_teki_type'] for a in actors] == [
        arena.P1_CHAPPY_TYPE, arena.P1_CHAPPY_TYPE]
    assert [tuple(a['expected_xyz']) for a in actors] == [tuple(p) for p in arena.POSITIONS]
    for actor in actors:
        assert actor['offset'] == [0, 0, 0]
        assert actor['source_yaw'] is None and actor['source_yaw_applied'] is False
        assert len(actor['expected_xyz']) == 3
    assert actors[1]['proxy'] == 'ordinary P1 control'
    assert 'identity NOT claimed' in actors[0]['proxy']


def test_generator_id_collision_rejected(tmp_path):
    with pytest.raises(ValueError, match='collision'):
        staged(tmp_path, existing=[entry(identity=246002)])


def test_install_declares_full_seam_binding_and_external_set(tmp_path):
    payload = install(tmp_path)
    assert payload['status'] == 'installed'
    assert set(payload['bindings']) == set(SEAM_BINDINGS)
    assert {'ground_query', 'host_profile', 'tick_entry', 'probe'} <= set(SEAM_BINDINGS)
    assert set(payload['external_dependencies']) == set(EXTERNAL_DEPS)
    assert {'pellet_configs:disc_data', 'mpellet_drop_code:disc_data'} <= set(EXTERNAL_DEPS)
    assert (Path(tmp_path) / PROFILE_TXT).read_bytes() == profile_text().encode('utf-8')
