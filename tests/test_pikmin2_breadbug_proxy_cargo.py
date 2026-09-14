"""Lane 18 runnable small-Breadbug proxy cargo arena tests (#168/#220)."""
from unittest.mock import patch

import pytest

from experimental import pikmin2_breadbug_proxy_cargo as proxy

WINDOW = 'Experimental preview window set to 960x540 windowed and centered'
DRAW = 'P2_BREADBUG_ACTOR_DRAW generator=186081 visual_proxy no_P2_FSM'
BIRTH = ('P2_BREADBUG_CARGO_BIRTH xyz=-150.000,35.000,1850.000 '
         'nest=-100.000,30.000,1700.000 distance=150.000 min=1')
TICK = ('P2_BREADBUG_CARGO_TICK tick=30 held=1 state=6 alive=1 '
        'distance=120.000 displacement=30.000 held_frames=30')
RESULT = ('P2_BREADBUG_CARGO_RESULT grabbed=1 held_frames=60 moved=50.000 '
          'progress=30.000 released=1 alive=0')
FULL = '\n'.join((WINDOW, DRAW, BIRTH, TICK, RESULT))


def test_grab_drag_and_release_delegate_to_contest_observation():
    report = proxy.validate(FULL)
    assert report['grab_observed'] is True
    assert report['drag_observed'] is True
    assert report['release_observed'] is True
    assert report['observed'] is True
    assert report['complete'] is True
    assert report['live_visual'] is True
    assert report['standard_window'] is True
    assert report['native_offset_power'] == 2.0
    assert report['source_strength'] == 1.5
    assert report['p2_contest_semantics'] is False


def test_unobserved_grab_is_incomplete_not_accepted():
    report = proxy.validate(FULL.replace('grabbed=1', 'grabbed=0'))
    assert report['grab_observed'] is False
    assert report['drag_observed'] is False
    assert report['observed'] is False
    assert report['complete'] is False
    assert report['p2_contest_semantics'] is False


def test_release_is_a_separate_gate_from_the_grab():
    report = proxy.validate(FULL.replace('released=1', 'released=0'))
    assert report['grab_observed'] is True
    assert report['release_observed'] is False
    assert report['observed'] is False
    assert report['complete'] is False


def test_missing_live_visual_or_window_is_rejected():
    with pytest.raises(ValueError, match='live Breadbug visual'):
        proxy.validate(FULL.replace(DRAW, ''))
    with pytest.raises(ValueError, match='960x540 centred window'):
        proxy.validate(FULL.replace(WINDOW, ''))


def test_structural_errors_delegate_to_contest_observation():
    with pytest.raises(ValueError, match='Missing native cargo birth marker'):
        proxy.validate(FULL.replace(BIRTH, ''))
    with pytest.raises(ValueError, match='Expected one completed P1 cargo observation'):
        proxy.validate(FULL.replace(RESULT, ''))


def test_build_copies_fixture_and_prefix_then_links(tmp_path):
    native = tmp_path / 'native'
    native.mkdir()
    build_dir = tmp_path / 'build'
    build_dir.mkdir()
    prefix = tmp_path / 'room-prefix.inc'
    prefix.write_text('// prefix\n')
    output = tmp_path / 'out'
    record = {'commands': [['g++', '-c', 'x.cpp', '-o', 'x.o'],
                           ['g++', '-o', 'baseline.exe', 'x.o']]}
    with patch.object(proxy.builder, 'build_fixture', return_value=record) as build_fixture, \
         patch.object(proxy.builder, 'run', return_value=(0, 'linked')) as link, \
         patch.object(proxy.builder, 'snapshot', return_value={'exe': {'sha256': 'abc'}}):
        exe, identity = proxy.build(native, build_dir, output, 'a' * 40, prefix)
    build_fixture.assert_called_once()
    assert build_fixture.call_args.args[2] == output / 'fixture.cpp'
    assert (output / 'fixture.cpp').read_text() == proxy.fixture_source()
    assert (output / 'room-prefix.inc').read_text() == '// prefix\n'
    assert exe == output / 'fixture.exe'
    link.assert_called_once()
    assert link.call_args.args[0][-2:] == [str(output / 'fixture.exe'), 'x.o']
    assert identity == {'exe': {'sha256': 'abc'}}
    assert (output / 'fixture-link.log').read_text() == 'linked'


def test_build_propagates_link_failure(tmp_path):
    native = tmp_path / 'native'
    native.mkdir()
    build_dir = tmp_path / 'build'
    build_dir.mkdir()
    prefix = tmp_path / 'room-prefix.inc'
    prefix.write_text('// prefix\n')
    record = {'commands': [['g++', '-o', 'baseline.exe', 'x.o']]}
    with patch.object(proxy.builder, 'build_fixture', return_value=record), \
         patch.object(proxy.builder, 'run', return_value=(1, 'boom')):
        with pytest.raises(RuntimeError, match='fixture link failed'):
            proxy.build(native, build_dir, tmp_path / 'out', 'a' * 40, prefix)
