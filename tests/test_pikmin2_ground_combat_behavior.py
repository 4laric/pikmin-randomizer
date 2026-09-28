"""Tests for the Sokkuri/Armor natural ground-combat validator (#165).

Three layers, none touches GL, disc assets, a player save or a real run:

* synthetic native-log unit tests for ``validate()`` (the acceptance contract);
* a GL-free fixture-builder smoke test that exercises ``instrument()`` on the
  real ``tools/preview_p2_room.cpp`` when a native worktree is present;
* a ``build()`` command-rewriting test with mocked compiler/Ninja steps.
"""
from pathlib import Path
from unittest.mock import patch

import pytest

from experimental import pikmin2_ground_combat_behavior as behavior
from experimental.pikmin2_ground_combat_behavior import (
    ARMOR_ID, ARMOR_POSITION, SOKKURI_ID, SOKKURI_POSITION, instrument, validate,
)

GOOD_LOG = '\n'.join([
    'P2_SOKKURI_BIND generator=346005 source_id=79 visual_only=0',
    'P2_ARMOR_BIND generator=346001 source_id=15 visual_only=0',
    'P2_ENEMY_READY species=Sokkuri native_family=Chappy generator=346005 x=-100.0 '
    'y=30.0 z=1850.0 health=120.0 max_health=120.0 behavior=native source_FSM=implemented',
    'P2_ENEMY_READY species=Armor native_family=Chappy generator=346001 x=-60.0 '
    'y=30.0 z=1850.0 health=300.0 max_health=300.0 behavior=native source_FSM=implemented',
    'Experimental preview window set to 960x540 windowed and centered',
    'P2_COMBAT_READY squad=20 sokkuri_health=120.0 armor_health=300.0',
    'P2_COMBAT_STIMULUS tick=1 captain_free_deploy=1',
    'P2_COMBAT_DEPLOY squad=20',
    'P2_COMBAT_DAMAGE species=Sokkuri health=60.0 max=120.0',
    'P2_COMBAT_DAMAGE species=Armor health=150.0 max=300.0',
    'P2_SOKKURI_DEAD generator=346005 source_id=79 health=0',
    'P2_ARMOR_DEAD generator=346001 source_id=15 health=0',
    'P2_COMBAT_DEATH species=Sokkuri generator=346005 source_id=79',
    'P2_COMBAT_DEATH species=Armor generator=346001 source_id=15',
    'P2_COMBAT_CORPSE species=Sokkuri generator=346005',
    'P2_COMBAT_CORPSE species=Armor generator=346001',
    'P2_BATCH2_DRAW corpse=1 key=ground|Sokkuri clip=dead1',
    'P2_COMBAT_FORGET species=Sokkuri count=0 registered=0',
    'P2_COMBAT_FORGET species=Armor count=0 registered=0',
    'P2_COMBAT_REENTRY species=Sokkuri old=0x1 new=0x2 stale=0 fresh=1 count=1',
    'P2_COMBAT_REENTRY species=Armor old=0x3 new=0x4 stale=0 fresh=1 count=1',
    'PASS P2_GROUND_COMBAT natural_death=2 corpse=2 cleanup=2 reentry=2 injected=0',
])

REQUIRED_MARKERS = {
    'identity': 'P2_ARMOR_BIND generator=346001 source_id=15 visual_only=0',
    'ready': 'P2_ENEMY_READY species=Armor native_family=Chappy generator=346001',
    'window': 'Experimental preview window set to 960x540 windowed and centered',
    'live_squad': 'P2_COMBAT_READY squad=20 sokkuri_health=120.0 armor_health=300.0',
    'deployed': 'P2_COMBAT_DEPLOY squad=20',
    'module_death': 'P2_ARMOR_DEAD generator=346001 source_id=15 health=0',
    'death': 'P2_COMBAT_DEATH species=Armor generator=346001 source_id=15',
    'corpse': 'P2_COMBAT_CORPSE species=Armor generator=346001',
    'forget': 'P2_COMBAT_FORGET species=Armor count=0 registered=0',
    'reentry': 'P2_COMBAT_REENTRY species=Armor old=0x3 new=0x4 stale=0 fresh=1 count=1',
    'completion': 'PASS P2_GROUND_COMBAT natural_death=2 corpse=2 cleanup=2 reentry=2 injected=0',
}


def test_identities_and_behavior_positions():
    assert (SOKKURI_ID, ARMOR_ID) == (346005, 346001)
    assert SOKKURI_POSITION == (-100.0, 30.0, 1850.0)
    assert ARMOR_POSITION == (-60.0, 30.0, 1850.0)


def test_validate_passes_on_complete_natural_log():
    result = validate(GOOD_LOG, code=0)
    assert result['passed'], result['checks']
    assert result['squad'] == 20
    assert result['gates'] == {'combat': 'pass', 'death': 'pass', 'corpse': 'pass',
                               'delivery_reward': 'untested', 'cleanup': 'pass',
                               'reentry': 'pass'}
    assert result['checks']['no_injection']


@pytest.mark.parametrize('name', sorted(REQUIRED_MARKERS))
def test_each_missing_marker_fails(name):
    result = validate(GOOD_LOG.replace(REQUIRED_MARKERS[name], 'absent'), code=0)
    assert not result['passed'], name


def test_death_without_partial_damage_still_counts_as_natural_damage():
    death_only = '\n'.join(line for line in GOOD_LOG.splitlines()
                           if not line.startswith('P2_COMBAT_DAMAGE '))
    result = validate(death_only, code=0)
    assert result['checks']['natural_damage']
    assert result['passed']


def test_injected_or_forced_health_fails_natural_claim():
    injected = GOOD_LOG.replace(
        'P2_COMBAT_DEPLOY squad=20',
        'P2_COMBAT_DEPLOY squad=20\n'
        'P2_LIFECYCLE_INJECT species=Sokkuri,Armor injected_health=0 source=fixture '
        'not_natural_combat=1')
    result = validate(injected, code=0)
    assert not result['checks']['no_injection']
    assert not result['checks']['natural_damage']
    assert not result['passed']


def test_non_text_and_nonzero_exit_fail():
    with pytest.raises(ValueError):
        validate(b'not text')
    assert not validate(GOOD_LOG, code=1)['passed']


def test_extinction_fails():
    result = validate(GOOD_LOG + '\nGAMEEND_PikminExtinction', code=0)
    assert not result['checks']['no_extinction']
    assert not result['passed']


def test_delivery_reward_is_honestly_untested():
    result = validate(GOOD_LOG, code=0)
    assert result['gates']['delivery_reward'] == 'untested'
    assert 'no Pod' in result['delivery_reward_reason']


NATIVE_ROOT_CANDIDATES = (
    Path('output/native-species-groundlife'),
    Path('native'),
)


def _native_root():
    for root in NATIVE_ROOT_CANDIDATES:
        if (root / 'tools' / 'preview_p2_room.cpp').is_file() \
                and (root / 'src' / 'plugPikiColin' / 'newPikiGame.cpp').is_file():
            return root
    return None


def test_instrument_is_gl_free_builder_smoke():
    native = _native_root()
    if native is None:
        pytest.skip('native worktree not present')
    source = (native / 'tools' / 'preview_p2_room.cpp').read_text()
    result = instrument(source)
    assert 'class RoomApp : public PlugPikiApp {' in result
    assert result.count('class RoomApp : public PlugPikiApp {') == 1
    assert 'int main(' in result
    assert '#include "pc_p2_sokkuri.h"' in result
    assert '#include "pc_p2_armor.h"' in result
    assert 'P2_COMBAT_REENTRY' in result and 'P2_COMBAT_DEPLOY' in result
    # The fixture must not write health: natural combat is the whole point.
    assert 'mHealth=0' not in result and 'injected_health' not in result
    with pytest.raises(ValueError):
        instrument(result)


def test_build_orchestration_rewrites_fixture_objects_gl_free(tmp_path):
    native = _native_root()
    if native is None:
        pytest.skip('native worktree not present')
    build = tmp_path / 'build'
    output = tmp_path / 'fixture-output'
    build.mkdir()
    compiler = 'g++.exe'
    fixture_object = str(tmp_path / 'fixture.obj')
    record = dict(status='built', observed_source={'head': 'a' * 40, 'status': '',
                                                   'tracked_diff_sha256': 'x'},
                  inputs={}, fixture_inputs={}, configuration_inputs={},
                  toolchain={'ninja': {'path': 'ninja.exe'}}, commands=[
                      [compiler, '-c', '-MD', '-MF', 'room.d', '-o', 'room.obj', 'room.cpp'],
                      [compiler, fixture_object, 'libpikmin_legacy.a', '-o', 'old.exe',
                       '-Wl,--out-implib,old.dll.a']])
    calls = []

    def fake_run(command, cwd, env=None):
        calls.append(command)
        return 0, ''

    with patch('scripts.build_pikmin2_fixture.build_fixture', return_value=record), \
            patch('scripts.build_pikmin2_fixture.run', side_effect=fake_run), \
            patch('scripts.build_pikmin2_fixture.require_fresh'), \
            patch('scripts.build_pikmin2_fixture.check_snapshot'), \
            patch('scripts.build_pikmin2_fixture.snapshot', return_value={}), \
            patch('scripts.build_pikmin2_fixture.git_state', return_value=record['observed_source']):
        behavior.build(native.resolve(), build, output, 'a' * 40)
    assert (output / 'room.cpp').exists()
    assert (output / 'instrumentation.json').exists()
    link = next(command for command in calls
                if any(a.endswith('libpikmin_legacy.a') for a in command))
    assert any(a.endswith('tutorial.obj') for a in link)
    assert any(a.endswith('room.obj') for a in link)
    assert not any(a.endswith('fixture.obj') for a in link)
