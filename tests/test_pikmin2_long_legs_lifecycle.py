"""Tests for the Long Legs encounter/lifecycle validator (#173/#312).

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

from experimental import pikmin2_long_legs_lifecycle as behavior
from experimental.pikmin2_long_legs_lifecycle import (
    BIGFOOT_ID, BIGFOOT_POSITION, BIGFOOT_SOURCE_ID, HOudai_ID,
    HOudai_POSITION, HOudai_SOURCE_ID, instrument, validate)

GOOD_LOG = '\n'.join([
    'P2_LONG_LEGS_BIND generator=312001 species=Houdai pose=bind visual_only=0 native_fsm=implemented',
    'P2_LONG_LEGS_BIND generator=312002 species=BigFoot pose=bind visual_only=0 native_fsm=implemented',
    'Experimental preview window set to 960x540 windowed and centered',
    'P2_LONG_LEGS_STATE species=Houdai generator=312001 state=Land',
    'P2_LONG_LEGS_STATE species=Houdai generator=312001 state=Wait',
    'P2_LONG_LEGS_STATE species=BigFoot generator=312002 state=Wait',
    'P2_LL_READY squad=20 houdai_gen=312001 bigfoot_gen=312002 attack=20',
    'P2_LONG_LEGS_DAMAGE species=BigFoot generator=312002 health=80.0 prior=85.0',
    'P2_LONG_LEGS_CRUSH species=BigFoot generator=312002 pikmin=5',
    'P2_LL_NATURAL_DEATH bigfoot=1 health=0.0',
    'P2_LL_INJECT species=Houdai injected_health=0 source=fixture not_natural_combat=1',
    'P2_LONG_LEGS_DEAD species=BigFoot generator=312002 health=0 prior_health=123.0',
    'P2_LONG_LEGS_BIRTH species=BigFoot generator=312002 count=30',
    'P2_LONG_LEGS_DEAD species=Houdai generator=312001 health=0 prior_health=2800.0',
    'P2_LL_CORPSE species=BigFoot pellet=1 generator=312002',
    'P2_LL_CORPSE species=Houdai pellet=1 generator=312001',
    'P2_LL_FORGET species=BigFoot count=0 registered=0',
    'P2_LL_FORGET species=Houdai count=0 registered=0',
    'P2_LL_REENTRY species=BigFoot old=0x1 new=0x2 stale=0 fresh=1 count=2',
    'P2_LL_REENTRY species=Houdai old=0x3 new=0x4 stale=0 fresh=1 count=2',
    'P2_LL_NOREWARD pod=0 pokos=-1 fresh_corpses=0',
    'PASS P2_LONG_LEGS_LIFECYCLE death=Houdai,BigFoot corpse=2 registry_empty=2 '
    'reentry=2 stale=0 duplicate_reward=0',
])

REQUIRED_MARKERS = {
    'identity': 'P2_LONG_LEGS_BIND generator=312002 species=BigFoot pose=bind '
                'visual_only=0 native_fsm=implemented',
    'window': 'Experimental preview window set to 960x540 windowed and centered',
    'ready': 'P2_LL_READY squad=20 houdai_gen=312001 bigfoot_gen=312002 attack=20',
    'injected': 'P2_LL_INJECT species=Houdai injected_health=0 source=fixture '
                'not_natural_combat=1',
    'dead': 'P2_LONG_LEGS_DEAD species=BigFoot generator=312002 health=0 prior_health=123.0',
    'birth': 'P2_LONG_LEGS_BIRTH species=BigFoot generator=312002 count=30',
    'corpse': 'P2_LL_CORPSE species=BigFoot pellet=1 generator=312002',
    'forget': 'P2_LL_FORGET species=BigFoot count=0 registered=0',
    'reentry': 'P2_LL_REENTRY species=BigFoot old=0x1 new=0x2 stale=0 fresh=1 count=2',
    'noreward': 'P2_LL_NOREWARD pod=0 pokos=-1 fresh_corpses=0',
    'completion': 'PASS P2_LONG_LEGS_LIFECYCLE death=Houdai,BigFoot corpse=2 '
                  'registry_empty=2 reentry=2 stale=0 duplicate_reward=0',
}


def test_identities_and_behavior_positions():
    assert (HOudai_ID, BIGFOOT_ID) == (312001, 312002)
    assert (HOudai_SOURCE_ID, BIGFOOT_SOURCE_ID) == (66, 69)
    # BigFoot is staged at the squad overlay centre so the source foot crush
    # (port radius 60) and wake radius (75) both cover the starting squad.
    squad_centre = (-104.0, 1816.0)
    dx, dz = BIGFOOT_POSITION[0] - squad_centre[0], BIGFOOT_POSITION[2] - squad_centre[1]
    assert (dx * dx + dz * dz) ** 0.5 < 1.0
    # Houdai is clear of the crush radius so BigFoot's landing is un-ambiguous.
    ddx, ddz = HOudai_POSITION[0] - BIGFOOT_POSITION[0], HOudai_POSITION[2] - BIGFOOT_POSITION[2]
    assert (ddx * ddx + ddz * ddz) ** 0.5 > 60.0


def test_validate_passes_on_complete_lifecycle_log():
    result = validate(GOOD_LOG, code=0)
    assert result['passed'], result['checks']
    assert result['squad'] == 20
    assert result['gates']['combat_damage'] == 'pass'
    assert result['gates']['foot_crush'] == 'pass'
    assert result['gates']['death_output'] == 'pass'
    assert result['gates']['corpse_handoff'] == 'pass'
    assert result['gates']['delivery_reward'] == 'untested'
    assert result['gates']['cleanup'] == 'pass'
    assert result['gates']['reentry'] == 'pass'
    assert result['natural_vs_injected']['natural_bigfoot_death'] is True


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


def test_injected_lethal_is_labelled_distinct_from_natural_death():
    result = validate(GOOD_LOG, code=0)
    assert result['checks']['injected_lethal']
    # Removing the natural-death marker still passes the injected lifecycle path.
    no_natural = validate(GOOD_LOG.replace(
        'P2_LL_NATURAL_DEATH bigfoot=1 health=0.0\nP2_LL_INJECT species=Houdai '
        'injected_health=0 source=fixture not_natural_combat=1',
        'P2_LL_INJECT species=BigFoot,Houdai injected_health=0 source=fixture not_natural_combat=1'),
        code=0)
    assert no_natural['passed']
    assert not no_natural['natural_vs_injected']['natural_bigfoot_death']


def test_natural_combat_markers_report_separately():
    no_damage = validate(GOOD_LOG.replace(
        'P2_LONG_LEGS_DAMAGE species=BigFoot generator=312002 health=80.0 prior=85.0',
        ''), code=0)
    assert no_damage['gates']['combat_damage'] == 'unmeasured'
    no_crush = validate(GOOD_LOG.replace(
        'P2_LONG_LEGS_CRUSH species=BigFoot generator=312002 pikmin=5', ''), code=0)
    assert no_crush['gates']['foot_crush'] == 'unmeasured'


def test_delivery_reward_is_honestly_untested():
    result = validate(GOOD_LOG, code=0)
    assert result['gates']['delivery_reward'] == 'untested'
    assert 'lane 14' in result['delivery_reward_reason']
    assert 'lane 06' in result['delivery_reward_reason']


def _native_roots():
    env = os.environ.get('PIKMIN_NATIVE_ROOT')
    if env:
        yield Path(env)
    here = Path(__file__).resolve()
    for base in (here.parents[2], here.parents[1]):
        for sibling in ('native',):
            candidate = base / sibling
            if candidate.is_dir():
                yield candidate


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
    assert 'class RoomApp : public PlugPikiApp {' in result
    assert result.count('class RoomApp : public PlugPikiApp {') == 1
    assert 'int main(' in result
    if 'PIKMIN_P2_ROOM_WINDOW' in source:
        assert 'PIKMIN_P2_ROOM_WINDOW' in result and 'pc_window_center()' in result
    assert '#include "pc_p2_long_legs.h"' in result
    assert 'P2_LL_REENTRY' in result and 'P2_LL_FORGET' in result
    assert 'mHealth=0.0f' in result
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
    link = next(command for command in calls
                if any(a.endswith('libpikmin_legacy.a') for a in command))
    assert any(a.endswith('tutorial.obj') for a in link)
    assert any(a.endswith('room.obj') for a in link)
    assert not any(a.endswith('fixture.obj') for a in link)
