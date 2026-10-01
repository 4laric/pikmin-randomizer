"""Tests for the Sokkuri/Armor ground-lifecycle validator (#165/#407).

Two layers, neither touches GL, disc assets, a player save or a real run:

* synthetic native-log unit tests for ``validate()`` (the acceptance contract);
* a GL-free fixture-builder smoke test that exercises ``instrument()`` on the
  real ``tools/preview_p2_room.cpp`` and the ``build()`` command rewriting with
  mocked compiler/Ninja steps.
"""
import os
from pathlib import Path
from unittest.mock import patch

import pytest

from experimental import pikmin2_ground_lifecycle_behavior as behavior
from experimental.pikmin2_ground_lifecycle_behavior import (
    ARMOR_ID, ARMOR_POSITION, SOKKURI_ID, SOKKURI_POSITION, SQUAD_X, SQUAD_Z,
    instrument, validate)

GOOD_LOG = '\n'.join([
    'P2_SOKKURI_BIND generator=346005 source_id=79 visual_only=0',
    'P2_ARMOR_BIND generator=346001 source_id=15 visual_only=0',
    'P2_ENEMY_READY species=Sokkuri native_family=Chappy generator=346005 x=-100.0 '
    'y=30.0 z=1850.0 health=120.0 max_health=120.0 behavior=native source_FSM=implemented',
    'P2_ENEMY_READY species=Armor native_family=Chappy generator=346001 x=-60.0 '
    'y=30.0 z=1850.0 health=300.0 max_health=300.0 behavior=native source_FSM=implemented',
    'Experimental preview window set to 960x540 windowed and centered',
    'P2_LIFECYCLE_READY squad=20 sokkuri_gen=346005 armor_gen=346001 sokkuri_reg=1 armor_reg=1',
    'P2_LIFECYCLE_INJECT species=Sokkuri,Armor injected_health=0 source=fixture '
    'not_natural_combat=1',
    'P2_SOKKURI_DEAD generator=346005 source_id=79 health=0 prior_health=0.0',
    'P2_ARMOR_DEAD generator=346001 source_id=15 health=0',
    'P2_LIFECYCLE_DEADCLIP species=Sokkuri source_id=79 clip=dead1',
    'P2_LIFECYCLE_DEADCLIP species=Armor source_id=15 clip=dead',
    'P2_LIFECYCLE_CORPSE species=Sokkuri pellet=1 generator=346005',
    'P2_LIFECYCLE_CORPSE species=Armor pellet=1 generator=346001',
    'P2_BATCH2_DRAW corpse=1 key=ground|Sokkuri clip=dead1',
    'P2_LIFECYCLE_FORGET species=Sokkuri count=0 registered=0',
    'P2_LIFECYCLE_FORGET species=Armor count=0 registered=0',
    'P2_LIFECYCLE_REENTRY species=Sokkuri old=0x1 new=0x2 stale=0 fresh=1 count=1',
    'P2_LIFECYCLE_REENTRY species=Armor old=0x3 new=0x4 stale=0 fresh=1 count=1',
    'P2_LIFECYCLE_NOREWARD pod=0 pokos=-1 fresh_corpses=0',
    'PASS P2_GROUND_LIFECYCLE death=Sokkuri,Armor corpse=2 registry_empty=2 reentry=2 '
    'stale=0 duplicate_reward=0 injected=1',
])

REQUIRED_MARKERS = {
    'identity': 'P2_ARMOR_BIND generator=346001 source_id=15 visual_only=0',
    'window': 'Experimental preview window set to 960x540 windowed and centered',
    'ready': 'P2_LIFECYCLE_READY squad=20 sokkuri_gen=346005 armor_gen=346001 '
             'sokkuri_reg=1 armor_reg=1',
    'inject': 'P2_LIFECYCLE_INJECT species=Sokkuri,Armor injected_health=0 source=fixture '
              'not_natural_combat=1',
    'death': 'P2_ARMOR_DEAD generator=346001 source_id=15 health=0',
    'deadclip': 'P2_LIFECYCLE_DEADCLIP species=Armor source_id=15 clip=dead',
    'corpse': 'P2_LIFECYCLE_CORPSE species=Armor pellet=1 generator=346001',
    'corpse_draw': 'P2_BATCH2_DRAW corpse=1 key=ground|Sokkuri clip=dead1',
    'forget': 'P2_LIFECYCLE_FORGET species=Armor count=0 registered=0',
    'reentry': 'P2_LIFECYCLE_REENTRY species=Armor old=0x3 new=0x4 stale=0 fresh=1 count=1',
    'noreward': 'P2_LIFECYCLE_NOREWARD pod=0 pokos=-1 fresh_corpses=0',
    'completion': 'PASS P2_GROUND_LIFECYCLE death=Sokkuri,Armor corpse=2 registry_empty=2 '
                  'reentry=2 stale=0 duplicate_reward=0 injected=1',
}


def test_identities_and_behavior_positions():
    assert (SOKKURI_ID, ARMOR_ID) == (346005, 346001)
    for species, position, sight in (('Sokkuri', SOKKURI_POSITION, 150.0),
                                     ('Armor', ARMOR_POSITION, 200.0)):
        distance = min((position[0] - x) ** 2 + (position[2] - z) ** 2
                       for x in SQUAD_X for z in SQUAD_Z) ** 0.5
        assert distance < sight, species + ' must start inside the source sight radius'


def test_validate_passes_on_complete_lifecycle_log():
    result = validate(GOOD_LOG, code=0)
    assert result['passed'], result['checks']
    assert result['squad'] == 20
    assert result['gates'] == {'death': 'pass', 'corpse': 'pass',
                               'delivery_reward': 'untested',
                               'cleanup': 'pass', 'reentry': 'pass',
                               'combat_damage': 'unmeasured'}


@pytest.mark.parametrize('name', sorted(REQUIRED_MARKERS))
def test_each_missing_marker_fails(name):
    result = validate(GOOD_LOG.replace(REQUIRED_MARKERS[name], 'absent'), code=0)
    assert not result['passed'], name


def test_non_text_and_nonzero_exit_fail():
    with pytest.raises(ValueError):
        validate(b'not text')
    assert not validate(GOOD_LOG, code=1)['passed']


def test_extinction_fails():
    result = validate(GOOD_LOG + '\nGAMEEND_PikminExtinction', code=0)
    assert not result['checks']['no_extinction']
    assert not result['passed']


def test_delivery_reward_is_honestly_untested_not_n_a():
    result = validate(GOOD_LOG, code=0)
    assert result['gates']['delivery_reward'] == 'untested'
    assert 'no Pod' in result['delivery_reward_reason']
    assert 'not a source-backed N/A' in result['delivery_reward_reason']


NATURAL_DAMAGE = GOOD_LOG.replace(
    'P2_SOKKURI_DEAD generator=346005 source_id=79 health=0 prior_health=0.0',
    'P2_SOKKURI_DAMAGE generator=346005 source_id=79 health=80.0\n'
    'P2_SOKKURI_DEAD generator=346005 source_id=79 health=0 prior_health=105.0')


def test_combat_damage_is_observable_separately_from_death():
    plain = validate(GOOD_LOG, code=0)
    assert plain['checks']['death']
    assert not plain['checks']['natural_damage_seen']
    assert plain['gates']['combat_damage'] == 'unmeasured'
    with_damage = validate(NATURAL_DAMAGE, code=0)
    assert with_damage['checks']['natural_damage_seen']
    assert with_damage['gates']['combat_damage'] == 'pass'
    # Death still passes; the injected lethal step is recorded separately.
    assert with_damage['gates']['death'] == 'pass'


def test_death_prior_health_is_reported():
    result = validate(NATURAL_DAMAGE, code=0)
    assert result['checks']['death']
    assert result['checks']['natural_damage_seen']
    # The prior_health suffix must not break the death marker match.
    legacy = validate(GOOD_LOG.replace(' prior_health=0.0', ''), code=0)
    assert legacy['checks']['death']


def _native_roots():
    """Candidate native repo roots for the private fixture builder.

    ``PIKMIN_NATIVE_ROOT`` points at a private lane worktree; the historical
    ``native/`` subdir layout is also honored.
    """
    roots = []
    env = os.environ.get('PIKMIN_NATIVE_ROOT')
    if env:
        roots.append(Path(env))
    here = Path(__file__).resolve()
    roots += [here.parents[1] / 'native', Path('native')]
    return roots


def _native_fixture_source():
    for root in _native_roots():
        fixture = root / 'tools/preview_p2_room.cpp'
        if fixture.is_file():
            return root, fixture
    return None, None


def _fixture_source():
    root, fixture = _native_fixture_source()
    if root is None:
        pytest.skip('private native fixture worktree not present')
    return fixture.read_text(), fixture


def test_lane_fixture_honors_960x540_window():
    root, fixture = _native_fixture_source()
    if root is None:
        pytest.skip('lane fixture worktree not present')
    text = fixture.read_text()
    assert 'PIKMIN_P2_ROOM_WINDOW' in text and 'pc_window_center()' in text


def test_instrument_is_gl_free_builder_smoke():
    source, _ = _fixture_source()
    result = instrument(source)
    # The replacement keeps the production main() and its window policy.
    assert 'class RoomApp : public PlugPikiApp {' in result
    assert result.count('class RoomApp : public PlugPikiApp {') == 1
    assert 'int main(' in result
    if 'PIKMIN_P2_ROOM_WINDOW' in source:
        assert 'PIKMIN_P2_ROOM_WINDOW' in result and 'pc_window_center()' in result
    # The private app includes the family headers and the lifecycle markers.
    assert '#include "pc_p2_sokkuri.h"' in result
    assert '#include "pc_p2_armor.h"' in result
    assert 'P2_LIFECYCLE_REENTRY' in result and 'P2_LIFECYCLE_FORGET' in result
    assert 'mHealth=0.0f' in result
    # Re-instrumenting a transformed source must be refused, not silently doubled.
    with pytest.raises(ValueError):
        instrument(result)


def test_build_orchestration_rewrites_fixture_objects_gl_free(tmp_path):
    native_root, _ = _native_fixture_source()
    if native_root is None:
        pytest.skip('private native fixture worktree not present')
    native = native_root.resolve()
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
        behavior.build(native, build, output, 'a' * 40)
    assert (output / 'room.cpp').exists()
    assert (output / 'instrumentation.json').exists()
    # The tutorial translation unit is linked first so the archive member is not
    # extracted, and the fixture objects are the private ones.
    link = next(command for command in calls
                if any(a.endswith('libpikmin_legacy.a') for a in command))
    assert any(a.endswith('tutorial.obj') for a in link)
    assert any(a.endswith('room.obj') for a in link)
    assert not any(a.endswith('fixture.obj') for a in link)
